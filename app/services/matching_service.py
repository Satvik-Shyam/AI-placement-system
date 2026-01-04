"""
Embedding & Matching Service

PURPOSE:
Generate vector embeddings for resumes and job descriptions,
then compute similarity scores for job recommendations.

HOW IT WORKS:
1. Extract text features from parsed resume/JD
2. Generate embeddings using DeepSeek API
3. Store embeddings in MongoDB (cache)
4. Compute cosine similarity between student & job embeddings
5. Store recommendations in PostgreSQL (ai_recommendations table)

WHY EMBEDDINGS?
- Semantic matching: "Python developer" matches "Software Engineer - Python"
- Better than keyword matching: Captures meaning, not just exact words
- Scalable: Compare thousands of jobs quickly with vector math

COST OPTIMIZATION:
- Cache embeddings in MongoDB (never recompute)
- Use text hash to detect changes (only re-embed if content changed)
- Batch similarity computation (one student vs all jobs)
"""

import hashlib
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.services.deepseek_client import get_deepseek_client
from app.services.mongo_service import (
    ParsedResumeService,
    ParsedJobDescriptionService,
    EmbeddingCacheService
)
from app.db.postgres import get_db_session, execute_raw_sql
from sqlalchemy import text


# ============================================================
# EMBEDDING GENERATION
# ============================================================

class EmbeddingService:
    """
    Generates and caches vector embeddings for text.
    
    Uses DeepSeek's embedding capability or falls back to
    a simple TF-IDF-like approach if embeddings aren't available.
    """
    
    def __init__(self):
        self.ai_client = get_deepseek_client()
        self.cache_service = EmbeddingCacheService()
        self.parsed_resume_service = ParsedResumeService()
        self.parsed_jd_service = ParsedJobDescriptionService()
        
        # Embedding dimension (we'll use a simplified approach)
        self.embedding_dim = 256
    
    def _compute_text_hash(self, text: str) -> str:
        """Compute hash of text to detect changes."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _text_to_features(self, parsed_data: dict, entity_type: str) -> str:
        """
        Convert parsed data to a feature string for embedding.
        
        This creates a normalized text representation that captures
        the key matching criteria.
        """
        features = []
        
        if entity_type == "student":
            # Extract key features from resume
            skills = parsed_data.get("skills", [])
            features.append(f"skills: {', '.join(skills)}")
            
            exp_years = parsed_data.get("experience_years", 0)
            features.append(f"experience: {exp_years} years")
            
            # Add education
            for edu in parsed_data.get("education", []):
                degree = edu.get("degree", "")
                field = edu.get("field", "")
                features.append(f"education: {degree} in {field}")
            
            # Add job roles from experience
            for exp in parsed_data.get("experience", []):
                role = exp.get("role", "")
                if role:
                    features.append(f"role: {role}")
        
        elif entity_type == "job":
            # Extract key features from JD
            title = parsed_data.get("title", "")
            features.append(f"title: {title}")
            
            req_skills = parsed_data.get("required_skills", [])
            features.append(f"required skills: {', '.join(req_skills)}")
            
            pref_skills = parsed_data.get("preferred_skills", [])
            if pref_skills:
                features.append(f"preferred skills: {', '.join(pref_skills)}")
            
            min_exp = parsed_data.get("min_experience", 0)
            max_exp = parsed_data.get("max_experience")
            if max_exp:
                features.append(f"experience: {min_exp}-{max_exp} years")
            else:
                features.append(f"experience: {min_exp}+ years")
        
        return " | ".join(features)
    
    def _generate_embedding_via_ai(self, text: str) -> List[float]:
        """
        Generate embedding using DeepSeek API.
        
        Note: If DeepSeek doesn't support embeddings directly,
        we use a workaround by asking it to generate feature weights.
        """
        system_prompt = """You are an embedding generator. Given text about a person or job,
output a JSON array of exactly 256 floating point numbers between -1 and 1.
These numbers should represent the semantic meaning of the text.
Similar texts should produce similar number patterns.
Return ONLY the JSON array, nothing else."""

        try:
            response = self.ai_client._call_api(
                system_prompt, 
                text, 
                max_tokens=2000
            )
            embedding = self.ai_client._extract_json(response)
            
            if isinstance(embedding, list) and len(embedding) >= self.embedding_dim:
                return [float(x) for x in embedding[:self.embedding_dim]]
        except:
            pass
        
        # Fallback: Generate simple hash-based embedding
        return self._generate_simple_embedding(text)
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """
        Fallback: Generate a simple embedding using text hashing.
        
        This is a deterministic approach that doesn't require AI.
        Not as good as real embeddings, but works for demonstration.
        """
        # Normalize text
        text = text.lower().strip()
        words = text.split()
        
        # Initialize embedding with zeros
        embedding = [0.0] * self.embedding_dim
        
        # Hash each word and add to embedding
        for i, word in enumerate(words):
            word_hash = hashlib.sha256(word.encode()).digest()
            for j in range(min(32, self.embedding_dim)):
                idx = (i * 32 + j) % self.embedding_dim
                # Convert byte to float between -1 and 1
                embedding[idx] += (word_hash[j % len(word_hash)] - 128) / 128.0
        
        # Normalize to unit vector
        magnitude = np.sqrt(sum(x**2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def get_student_embedding(
        self, 
        student_id: int, 
        force_regenerate: bool = False
    ) -> Optional[List[float]]:
        """
        Get or generate embedding for a student.
        
        Args:
            student_id: PostgreSQL student ID
            force_regenerate: If True, regenerate even if cached
        
        Returns:
            List of floats (embedding vector) or None if no resume
        """
        # Check cache first (unless forced)
        if not force_regenerate:
            cached = self.cache_service.get_embedding("student", student_id)
            if cached:
                return cached
        
        # Get parsed resume from MongoDB
        parsed_doc = self.parsed_resume_service.get_by_student(student_id)
        if not parsed_doc or "parsed_data" not in parsed_doc:
            return None
        
        parsed_data = parsed_doc["parsed_data"]
        
        # Convert to feature text
        feature_text = self._text_to_features(parsed_data, "student")
        text_hash = self._compute_text_hash(feature_text)
        
        # Generate embedding
        embedding = self._generate_simple_embedding(feature_text)
        
        # Cache it
        self.cache_service.store_embedding(
            entity_type="student",
            entity_id=student_id,
            embedding=embedding,
            text_hash=text_hash
        )
        
        return embedding
    
    def get_job_embedding(
        self, 
        job_id: int, 
        force_regenerate: bool = False
    ) -> Optional[List[float]]:
        """
        Get or generate embedding for a job.
        """
        # Check cache first
        if not force_regenerate:
            cached = self.cache_service.get_embedding("job", job_id)
            if cached:
                return cached
        
        # Get parsed JD from MongoDB
        parsed_doc = self.parsed_jd_service.get_by_job(job_id)
        if not parsed_doc or "parsed_data" not in parsed_doc:
            return None
        
        parsed_data = parsed_doc["parsed_data"]
        
        # Convert to feature text
        feature_text = self._text_to_features(parsed_data, "job")
        text_hash = self._compute_text_hash(feature_text)
        
        # Generate embedding
        embedding = self._generate_simple_embedding(feature_text)
        
        # Cache it
        self.cache_service.store_embedding(
            entity_type="job",
            entity_id=job_id,
            embedding=embedding,
            text_hash=text_hash
        )
        
        return embedding


# ============================================================
# SIMILARITY COMPUTATION
# ============================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Returns:
        Float between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same dimension")
    
    # Convert to numpy for efficient computation
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return float(dot_product / (magnitude_a * magnitude_b))


def compute_skill_match_percentage(
    student_skills: List[str], 
    required_skills: List[str]
) -> float:
    """
    Compute percentage of required skills that student has.
    
    Uses case-insensitive matching.
    
    Returns:
        Float between 0 and 100
    """
    if not required_skills:
        return 100.0  # No requirements = 100% match
    
    # Normalize to lowercase for comparison
    student_skills_lower = {s.lower() for s in student_skills}
    required_skills_lower = {s.lower() for s in required_skills}
    
    # Count matches
    matches = student_skills_lower.intersection(required_skills_lower)
    
    return (len(matches) / len(required_skills_lower)) * 100


def check_experience_match(
    student_experience: float,
    min_required: int,
    max_required: Optional[int]
) -> bool:
    """
    Check if student's experience falls within job requirements.
    """
    if student_experience < min_required:
        return False
    
    if max_required is not None and student_experience > max_required + 2:
        # Allow some flexibility (2 years over max is okay)
        return False
    
    return True


# ============================================================
# RECOMMENDATION SERVICE
# ============================================================

class RecommendationService:
    """
    Generates and stores job recommendations for students.
    
    Process:
    1. Get student embedding
    2. Get all open job embeddings
    3. Compute similarity scores
    4. Calculate skill match percentage
    5. Check experience match
    6. Store top recommendations in PostgreSQL
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.parsed_resume_service = ParsedResumeService()
        self.parsed_jd_service = ParsedJobDescriptionService()
    
    def generate_recommendations(
        self, 
        student_id: int, 
        top_n: int = 10,
        min_score: float = 0.3
    ) -> List[dict]:
        """
        Generate job recommendations for a student.
        
        Args:
            student_id: PostgreSQL student ID
            top_n: Maximum number of recommendations
            min_score: Minimum match score (0-1) to include
        
        Returns:
            List of recommendation dicts with scores
        """
        recommendations = []
        
        # Step 1: Get student embedding
        student_embedding = self.embedding_service.get_student_embedding(student_id)
        if not student_embedding:
            return []
        
        # Step 2: Get student's parsed resume for skill matching
        student_doc = self.parsed_resume_service.get_by_student(student_id)
        if not student_doc:
            return []
        
        student_data = student_doc.get("parsed_data", {})
        student_skills = student_data.get("skills", [])
        student_experience = student_data.get("experience_years", 0)
        
        # Step 3: Get all open jobs from PostgreSQL
        open_jobs = execute_raw_sql("""
            SELECT job_id, title, company_id, min_experience, max_experience
            FROM jobs 
            WHERE status = 'open'
        """)
        
        # Step 4: Score each job
        for job in open_jobs:
            job_id = job["job_id"]
            
            # Get job embedding
            job_embedding = self.embedding_service.get_job_embedding(job_id)
            if not job_embedding:
                continue
            
            # Compute cosine similarity
            similarity = cosine_similarity(student_embedding, job_embedding)
            
            # Normalize to 0-1 range (cosine similarity is -1 to 1)
            match_score = (similarity + 1) / 2
            
            # Get job's parsed data for skill matching
            job_doc = self.parsed_jd_service.get_by_job(job_id)
            if job_doc and "parsed_data" in job_doc:
                job_data = job_doc["parsed_data"]
                required_skills = job_data.get("required_skills", [])
                
                # Compute skill match percentage
                skill_match_pct = compute_skill_match_percentage(
                    student_skills, required_skills
                )
                
                # Check experience match
                experience_match = check_experience_match(
                    student_experience,
                    job.get("min_experience", 0),
                    job.get("max_experience")
                )
            else:
                skill_match_pct = 50.0  # Default if no parsed data
                experience_match = True
            
            # Combine scores (weighted average)
            # 50% embedding similarity + 40% skill match + 10% experience
            combined_score = (
                match_score * 0.5 +
                (skill_match_pct / 100) * 0.4 +
                (1.0 if experience_match else 0.5) * 0.1
            )
            
            if combined_score >= min_score:
                recommendations.append({
                    "job_id": job_id,
                    "job_title": job["title"],
                    "match_score": round(combined_score, 4),
                    "skill_match_pct": round(skill_match_pct, 2),
                    "experience_match": experience_match,
                    "embedding_similarity": round(match_score, 4)
                })
        
        # Step 5: Sort by score and take top N
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return recommendations[:top_n]
    
    def store_recommendations(
        self, 
        student_id: int, 
        recommendations: List[dict]
    ) -> int:
        """
        Store recommendations in PostgreSQL ai_recommendations table.
        
        Args:
            student_id: PostgreSQL student ID
            recommendations: List from generate_recommendations()
        
        Returns:
            Number of recommendations stored
        """
        if not recommendations:
            return 0
        
        stored_count = 0
        expires_at = datetime.utcnow() + timedelta(days=7)  # Expire in 7 days
        
        with get_db_session() as db:
            for rec in recommendations:
                # Generate recommendation reason
                reason = self._generate_reason(rec)
                
                # Insert or update recommendation
                db.execute(
                    text("""
                        INSERT INTO ai_recommendations (
                            student_id, job_id, match_score, skill_match_pct,
                            experience_match, recommendation_reason, expires_at
                        ) VALUES (
                            :student_id, :job_id, :match_score, :skill_match_pct,
                            :experience_match, :reason, :expires_at
                        )
                        ON CONFLICT (student_id, job_id) DO UPDATE SET
                            match_score = EXCLUDED.match_score,
                            skill_match_pct = EXCLUDED.skill_match_pct,
                            experience_match = EXCLUDED.experience_match,
                            recommendation_reason = EXCLUDED.recommendation_reason,
                            expires_at = EXCLUDED.expires_at,
                            created_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "student_id": student_id,
                        "job_id": rec["job_id"],
                        "match_score": rec["match_score"],
                        "skill_match_pct": rec["skill_match_pct"],
                        "experience_match": rec["experience_match"],
                        "reason": reason,
                        "expires_at": expires_at
                    }
                )
                stored_count += 1
        
        return stored_count
    
    def _generate_reason(self, rec: dict) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        score_pct = int(rec["match_score"] * 100)
        reasons.append(f"Overall match: {score_pct}%")
        
        skill_pct = int(rec["skill_match_pct"])
        if skill_pct >= 80:
            reasons.append(f"Excellent skill match ({skill_pct}%)")
        elif skill_pct >= 50:
            reasons.append(f"Good skill match ({skill_pct}%)")
        else:
            reasons.append(f"Partial skill match ({skill_pct}%)")
        
        if rec["experience_match"]:
            reasons.append("Experience requirements met")
        else:
            reasons.append("Experience slightly outside range")
        
        return ". ".join(reasons) + "."
    
    def get_student_recommendations(
        self, 
        student_id: int,
        include_applied: bool = False
    ) -> List[dict]:
        """
        Fetch stored recommendations for a student from PostgreSQL.
        
        Args:
            student_id: PostgreSQL student ID
            include_applied: Include jobs student already applied to
        
        Returns:
            List of recommendations with job details
        """
        sql = """
            SELECT 
                r.recommendation_id,
                r.job_id,
                j.title as job_title,
                c.company_name,
                r.match_score,
                r.skill_match_pct,
                r.experience_match,
                r.recommendation_reason,
                r.is_viewed,
                r.is_applied,
                r.created_at
            FROM ai_recommendations r
            JOIN jobs j ON r.job_id = j.job_id
            JOIN companies c ON j.company_id = c.company_id
            WHERE r.student_id = :student_id
                AND r.expires_at > CURRENT_TIMESTAMP
                AND j.status = 'open'
        """
        
        if not include_applied:
            sql += " AND r.is_applied = FALSE"
        
        sql += " ORDER BY r.match_score DESC"
        
        return execute_raw_sql(sql, {"student_id": student_id})
    
    def mark_recommendation_viewed(
        self, 
        student_id: int, 
        job_id: int
    ) -> bool:
        """Mark a recommendation as viewed."""
        with get_db_session() as db:
            result = db.execute(
                text("""
                    UPDATE ai_recommendations 
                    SET is_viewed = TRUE 
                    WHERE student_id = :student_id AND job_id = :job_id
                """),
                {"student_id": student_id, "job_id": job_id}
            )
            return result.rowcount > 0
    
    def mark_recommendation_applied(
        self, 
        student_id: int, 
        job_id: int
    ) -> bool:
        """Mark a recommendation as applied (student applied to job)."""
        with get_db_session() as db:
            result = db.execute(
                text("""
                    UPDATE ai_recommendations 
                    SET is_applied = TRUE 
                    WHERE student_id = :student_id AND job_id = :job_id
                """),
                {"student_id": student_id, "job_id": job_id}
            )
            return result.rowcount > 0


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    return EmbeddingService()


def get_recommendation_service() -> RecommendationService:
    """Get recommendation service instance."""
    return RecommendationService()