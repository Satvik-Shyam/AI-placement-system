"""
AI Parsing Service - Resume and Job Description parsing using DeepSeek.

PURPOSE:
AI is used ONLY for:
1. Resume parsing (text → structured JSON)
2. Job description parsing (text → structured JSON)
3. Skill extraction and normalization

AI OUTPUT → STRUCTURED → STORED IN DATABASE → QUERIED BY SQL
The DBMS is the core system. AI is just a data transformer.

COST OPTIMIZATION:
- Short, structured prompts (minimize input tokens)
- Strict JSON output (minimize output tokens)
- Low temperature (0.1) for consistent results
- Cache results in MongoDB (never re-parse same document)
"""

import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.deepseek_client import get_deepseek_client, DeepSeekClient
from app.services.mongo_service import (
    RawResumeService,
    ParsedResumeService,
    RawJobDescriptionService,
    ParsedJobDescriptionService
)
from app.db.postgres import get_db_session
from sqlalchemy import text


# ============================================================
# JSON VALIDATION HELPERS
# ============================================================

def validate_parsed_resume(data: dict) -> dict:
    """
    Validate and sanitize parsed resume data.
    Ensures all required fields exist with correct types.
    """
    validated = {
        "name": str(data.get("name", "")).strip() or "Unknown",
        "email": data.get("email") if data.get("email") else None,
        "phone": data.get("phone") if data.get("phone") else None,
        "skills": [],
        "experience_years": 0,
        "education": [],
        "experience": []
    }
    
    # Validate skills (must be list of strings)
    skills = data.get("skills", [])
    if isinstance(skills, list):
        validated["skills"] = [str(s).strip() for s in skills if s]
    
    # Validate experience_years (must be number >= 0)
    exp_years = data.get("experience_years", 0)
    try:
        validated["experience_years"] = max(0, float(exp_years))
    except (ValueError, TypeError):
        validated["experience_years"] = 0
    
    # Validate education (list of dicts)
    education = data.get("education", [])
    if isinstance(education, list):
        for edu in education:
            if isinstance(edu, dict):
                validated["education"].append({
                    "degree": str(edu.get("degree", "")).strip(),
                    "field": str(edu.get("field", "")).strip(),
                    "institution": str(edu.get("institution", "")).strip(),
                    "year": edu.get("year"),
                    "cgpa": edu.get("cgpa")
                })
    
    # Validate experience (list of dicts)
    experience = data.get("experience", [])
    if isinstance(experience, list):
        for exp in experience:
            if isinstance(exp, dict):
                validated["experience"].append({
                    "company": str(exp.get("company", "")).strip(),
                    "role": str(exp.get("role", "")).strip(),
                    "duration": str(exp.get("duration", "")).strip(),
                    "highlights": exp.get("highlights", [])
                })
    
    return validated


def validate_parsed_jd(data: dict) -> dict:
    """
    Validate and sanitize parsed job description data.
    """
    validated = {
        "title": str(data.get("title", "")).strip() or "Unknown Position",
        "required_skills": [],
        "preferred_skills": [],
        "min_experience": 0,
        "max_experience": None,
        "education_required": data.get("education_required")
    }
    
    # Validate required_skills
    req_skills = data.get("required_skills", [])
    if isinstance(req_skills, list):
        validated["required_skills"] = [str(s).strip() for s in req_skills if s]
    
    # Validate preferred_skills
    pref_skills = data.get("preferred_skills", [])
    if isinstance(pref_skills, list):
        validated["preferred_skills"] = [str(s).strip() for s in pref_skills if s]
    
    # Validate experience range
    try:
        validated["min_experience"] = max(0, int(data.get("min_experience", 0)))
    except (ValueError, TypeError):
        validated["min_experience"] = 0
    
    try:
        max_exp = data.get("max_experience")
        if max_exp is not None:
            validated["max_experience"] = max(validated["min_experience"], int(max_exp))
    except (ValueError, TypeError):
        validated["max_experience"] = None
    
    return validated


def compute_text_hash(text: str) -> str:
    """Compute MD5 hash of text for change detection."""
    return hashlib.md5(text.encode()).hexdigest()


# ============================================================
# RESUME PARSING SERVICE
# ============================================================

class ResumeParsingService:
    """
    Complete resume parsing workflow:
    1. Store raw resume in MongoDB
    2. Parse with DeepSeek AI
    3. Validate JSON output
    4. Store parsed data in MongoDB
    5. Sync skills to PostgreSQL
    """
    
    def __init__(self):
        self.ai_client: DeepSeekClient = get_deepseek_client()
        self.raw_resume_service = RawResumeService()
        self.parsed_resume_service = ParsedResumeService()
    
    def parse_and_store(
        self, 
        student_id: int, 
        resume_text: str, 
        filename: str = None
    ) -> dict:
        """
        Full parsing pipeline for a resume.
        
        Args:
            student_id: PostgreSQL student ID
            resume_text: Extracted text from resume file
            filename: Original filename (optional)
        
        Returns:
            {
                "success": True/False,
                "raw_mongo_id": "...",
                "parsed_mongo_id": "...",
                "parsed_data": {...},
                "skills_synced": 5
            }
        """
        result = {
            "success": False,
            "raw_mongo_id": None,
            "parsed_mongo_id": None,
            "parsed_data": None,
            "skills_synced": 0,
            "error": None
        }
        
        try:
            # Step 1: Store raw resume in MongoDB
            raw_mongo_id = self.raw_resume_service.insert(
                student_id=student_id,
                resume_text=resume_text,
                filename=filename
            )
            result["raw_mongo_id"] = raw_mongo_id
            
            # Step 2: Parse with AI
            parsed_data = self.ai_client.parse_resume(resume_text)
            
            # Step 3: Validate JSON output
            validated_data = validate_parsed_resume(parsed_data)
            result["parsed_data"] = validated_data
            
            # Step 4: Store parsed data in MongoDB
            parsed_mongo_id = self.parsed_resume_service.insert(
                student_id=student_id,
                raw_resume_id=raw_mongo_id,
                parsed_data=validated_data
            )
            result["parsed_mongo_id"] = parsed_mongo_id
            
            # Step 5: Mark raw resume as parsed
            self.raw_resume_service.mark_as_parsed(raw_mongo_id)
            
            # Step 6: Sync skills to PostgreSQL
            skills_synced = self._sync_skills_to_postgres(
                student_id=student_id,
                skills=validated_data["skills"]
            )
            result["skills_synced"] = skills_synced
            
            # Step 7: Update student's resume_mongo_id in PostgreSQL
            self._update_student_resume_id(student_id, parsed_mongo_id)
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _sync_skills_to_postgres(self, student_id: int, skills: List[str]) -> int:
        """
        Sync extracted skills to PostgreSQL.
        
        Process:
        1. Normalize skill names using AI
        2. Find or create skills in skills table
        3. Link to student via student_skills junction table
        
        Returns:
            Number of skills synced
        """
        if not skills:
            return 0
        
        # Normalize skills using AI
        try:
            normalized_skills = self.ai_client.normalize_skills(skills)
        except:
            normalized_skills = skills  # Fallback to original if AI fails
        
        synced_count = 0
        
        with get_db_session() as db:
            for skill_name in normalized_skills:
                if not skill_name:
                    continue
                
                # Find or create skill
                skill_result = db.execute(
                    text("""
                        INSERT INTO skills (skill_name, category)
                        VALUES (:name, 'uncategorized')
                        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
                        RETURNING skill_id
                    """),
                    {"name": skill_name}
                )
                skill_row = skill_result.fetchone()
                skill_id = skill_row[0]
                
                # Link to student (ignore if already linked)
                db.execute(
                    text("""
                        INSERT INTO student_skills (student_id, skill_id, proficiency_level)
                        VALUES (:student_id, :skill_id, 'intermediate')
                        ON CONFLICT (student_id, skill_id) DO NOTHING
                    """),
                    {"student_id": student_id, "skill_id": skill_id}
                )
                synced_count += 1
        
        return synced_count
    
    def _update_student_resume_id(self, student_id: int, mongo_id: str):
        """Update student's resume_mongo_id in PostgreSQL."""
        with get_db_session() as db:
            db.execute(
                text("""
                    UPDATE students 
                    SET resume_mongo_id = :mongo_id, updated_at = CURRENT_TIMESTAMP
                    WHERE student_id = :student_id
                """),
                {"mongo_id": mongo_id, "student_id": student_id}
            )


# ============================================================
# JOB DESCRIPTION PARSING SERVICE
# ============================================================

class JobDescriptionParsingService:
    """
    Complete JD parsing workflow:
    1. Store raw JD in MongoDB
    2. Parse with DeepSeek AI
    3. Validate JSON output
    4. Store parsed data in MongoDB
    5. Sync required skills to PostgreSQL
    """
    
    def __init__(self):
        self.ai_client: DeepSeekClient = get_deepseek_client()
        self.raw_jd_service = RawJobDescriptionService()
        self.parsed_jd_service = ParsedJobDescriptionService()
    
    def parse_and_store(self, job_id: int, jd_text: str) -> dict:
        """
        Full parsing pipeline for a job description.
        
        Args:
            job_id: PostgreSQL job ID
            jd_text: Full job description text
        
        Returns:
            {
                "success": True/False,
                "raw_mongo_id": "...",
                "parsed_mongo_id": "...",
                "parsed_data": {...},
                "skills_synced": 5
            }
        """
        result = {
            "success": False,
            "raw_mongo_id": None,
            "parsed_mongo_id": None,
            "parsed_data": None,
            "skills_synced": 0,
            "error": None
        }
        
        try:
            # Step 1: Store raw JD in MongoDB
            raw_mongo_id = self.raw_jd_service.insert(
                job_id=job_id,
                jd_text=jd_text
            )
            result["raw_mongo_id"] = raw_mongo_id
            
            # Step 2: Parse with AI
            parsed_data = self.ai_client.parse_job_description(jd_text)
            
            # Step 3: Validate JSON output
            validated_data = validate_parsed_jd(parsed_data)
            result["parsed_data"] = validated_data
            
            # Step 4: Store parsed data in MongoDB
            parsed_mongo_id = self.parsed_jd_service.insert(
                job_id=job_id,
                raw_jd_id=raw_mongo_id,
                parsed_data=validated_data
            )
            result["parsed_mongo_id"] = parsed_mongo_id
            
            # Step 5: Mark raw JD as parsed
            self.raw_jd_service.mark_as_parsed(job_id)
            
            # Step 6: Sync skills to PostgreSQL
            all_skills = validated_data["required_skills"] + validated_data["preferred_skills"]
            skills_synced = self._sync_job_skills_to_postgres(
                job_id=job_id,
                required_skills=validated_data["required_skills"],
                preferred_skills=validated_data["preferred_skills"]
            )
            result["skills_synced"] = skills_synced
            
            # Step 7: Update job's jd_mongo_id in PostgreSQL
            self._update_job_mongo_id(job_id, parsed_mongo_id)
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _sync_job_skills_to_postgres(
        self, 
        job_id: int, 
        required_skills: List[str],
        preferred_skills: List[str]
    ) -> int:
        """
        Sync job skills to PostgreSQL.
        
        Required skills: is_mandatory = TRUE
        Preferred skills: is_mandatory = FALSE
        """
        synced_count = 0
        
        with get_db_session() as db:
            # Process required skills
            for skill_name in required_skills:
                if not skill_name:
                    continue
                
                # Find or create skill
                skill_result = db.execute(
                    text("""
                        INSERT INTO skills (skill_name, category)
                        VALUES (:name, 'uncategorized')
                        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
                        RETURNING skill_id
                    """),
                    {"name": skill_name}
                )
                skill_id = skill_result.fetchone()[0]
                
                # Link to job as mandatory
                db.execute(
                    text("""
                        INSERT INTO job_required_skills (job_id, skill_id, is_mandatory)
                        VALUES (:job_id, :skill_id, TRUE)
                        ON CONFLICT (job_id, skill_id) DO UPDATE SET is_mandatory = TRUE
                    """),
                    {"job_id": job_id, "skill_id": skill_id}
                )
                synced_count += 1
            
            # Process preferred skills
            for skill_name in preferred_skills:
                if not skill_name:
                    continue
                
                # Find or create skill
                skill_result = db.execute(
                    text("""
                        INSERT INTO skills (skill_name, category)
                        VALUES (:name, 'uncategorized')
                        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
                        RETURNING skill_id
                    """),
                    {"name": skill_name}
                )
                skill_id = skill_result.fetchone()[0]
                
                # Link to job as preferred (not mandatory)
                db.execute(
                    text("""
                        INSERT INTO job_required_skills (job_id, skill_id, is_mandatory)
                        VALUES (:job_id, :skill_id, FALSE)
                        ON CONFLICT (job_id, skill_id) DO NOTHING
                    """),
                    {"job_id": job_id, "skill_id": skill_id}
                )
                synced_count += 1
        
        return synced_count
    
    def _update_job_mongo_id(self, job_id: int, mongo_id: str):
        """Update job's jd_mongo_id in PostgreSQL."""
        with get_db_session() as db:
            db.execute(
                text("""
                    UPDATE jobs 
                    SET jd_mongo_id = :mongo_id, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = :job_id
                """),
                {"mongo_id": mongo_id, "job_id": job_id}
            )


# ============================================================
# SKILL EXTRACTION SERVICE (Standalone)
# ============================================================

class SkillExtractionService:
    """
    Standalone skill extraction and normalization.
    Used when you just need to extract skills from any text.
    """
    
    def __init__(self):
        self.ai_client: DeepSeekClient = get_deepseek_client()
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract skills from any text using AI.
        
        This uses a specialized prompt that's different from
        the full resume parser.
        """
        system_prompt = """Extract technical and professional skills from the text.
Return ONLY a JSON array of skill names.
Include: programming languages, frameworks, tools, databases, soft skills.
Format: ["Skill1", "Skill2", "Skill3"]
Return ONLY the JSON array, nothing else."""

        try:
            response = self.ai_client._call_api(system_prompt, text, max_tokens=300)
            skills = self.ai_client._extract_json(response)
            
            if isinstance(skills, list):
                return [str(s).strip() for s in skills if s]
            return []
        except:
            return []
    
    def normalize_skills(self, skills: List[str]) -> List[str]:
        """
        Normalize skill names to standard forms.
        E.g., "JS" → "JavaScript", "ML" → "Machine Learning"
        """
        return self.ai_client.normalize_skills(skills)
    
    def match_skills_to_db(self, skills: List[str]) -> List[dict]:
        """
        Match extracted skills against PostgreSQL skills table.
        
        Returns:
            List of {"skill_name": "...", "skill_id": ..., "matched": True/False}
        """
        results = []
        
        with get_db_session() as db:
            for skill_name in skills:
                # Try exact match first
                match_result = db.execute(
                    text("""
                        SELECT skill_id, skill_name 
                        FROM skills 
                        WHERE LOWER(skill_name) = LOWER(:name)
                    """),
                    {"name": skill_name}
                )
                row = match_result.fetchone()
                
                if row:
                    results.append({
                        "input_skill": skill_name,
                        "matched_skill": row[1],
                        "skill_id": row[0],
                        "matched": True
                    })
                else:
                    results.append({
                        "input_skill": skill_name,
                        "matched_skill": None,
                        "skill_id": None,
                        "matched": False
                    })
        
        return results


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_resume_parser() -> ResumeParsingService:
    """Get resume parsing service instance."""
    return ResumeParsingService()


def get_jd_parser() -> JobDescriptionParsingService:
    """Get JD parsing service instance."""
    return JobDescriptionParsingService()


def get_skill_extractor() -> SkillExtractionService:
    """Get skill extraction service instance."""
    return SkillExtractionService()