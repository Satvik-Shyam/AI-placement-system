"""
MongoDB Service - CRUD operations for document collections.

Collections in this database:
1. raw_resumes       - Original resume text (before AI parsing)
2. parsed_resumes    - AI-extracted structured data from resumes
3. raw_job_descriptions - Original JD text (before AI parsing)
4. parsed_job_descriptions - AI-extracted structured data from JDs
5. embedding_cache   - Cached vector embeddings for similarity matching

WHY MongoDB for these?
- Resume/JD text varies wildly in structure
- AI outputs have nested, flexible schemas
- No complex joins needed - documents are self-contained
- Easy to store and retrieve JSON directly
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from pymongo.collection import Collection

from app.db.mongodb import get_collection, COLLECTIONS


# ============================================================
# HELPER: Convert ObjectId to string for JSON serialization
# ============================================================

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def serialize_docs(docs: list) -> list:
    """Convert list of MongoDB documents to JSON-serializable list."""
    return [serialize_doc(doc) for doc in docs]


# ============================================================
# RAW RESUMES COLLECTION
# Stores original resume text before AI parsing
# ============================================================

class RawResumeService:
    """
    Handles raw resume document storage.
    These are the original uploaded resume texts.
    """
    
    def __init__(self):
        self.collection: Collection = get_collection(COLLECTIONS["raw_resumes"])
    
    def insert(self, student_id: int, resume_text: str, filename: str = None) -> str:
        """
        Insert a raw resume document.
        
        Args:
            student_id: PostgreSQL student ID (foreign reference)
            resume_text: Extracted text from resume PDF/DOCX
            filename: Original filename
        
        Returns:
            MongoDB ObjectId as string (store this in PostgreSQL)
        """
        doc = {
            "student_id": student_id,
            "resume_text": resume_text,
            "filename": filename,
            "uploaded_at": datetime.utcnow(),
            "is_parsed": False  # Will be True after AI parsing
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_by_id(self, mongo_id: str) -> Optional[dict]:
        """Fetch raw resume by MongoDB ObjectId."""
        doc = self.collection.find_one({"_id": ObjectId(mongo_id)})
        return serialize_doc(doc)
    
    def get_by_student(self, student_id: int) -> Optional[dict]:
        """Fetch latest raw resume for a student."""
        doc = self.collection.find_one(
            {"student_id": student_id},
            sort=[("uploaded_at", -1)]  # Most recent first
        )
        return serialize_doc(doc)
    
    def mark_as_parsed(self, mongo_id: str) -> bool:
        """Mark resume as parsed after AI processing."""
        result = self.collection.update_one(
            {"_id": ObjectId(mongo_id)},
            {"$set": {"is_parsed": True, "parsed_at": datetime.utcnow()}}
        )
        return result.modified_count > 0


# ============================================================
# PARSED RESUMES COLLECTION
# Stores AI-extracted structured data from resumes
# ============================================================

class ParsedResumeService:
    """
    Handles parsed resume storage.
    These contain structured data extracted by AI.
    """
    
    def __init__(self):
        self.collection: Collection = get_collection(COLLECTIONS["parsed_resumes"])
    
    def insert(self, student_id: int, raw_resume_id: str, parsed_data: dict) -> str:
        """
        Insert parsed resume data.
        
        Args:
            student_id: PostgreSQL student ID
            raw_resume_id: Reference to raw_resumes document
            parsed_data: AI-extracted structured data
        
        Returns:
            MongoDB ObjectId as string
        
        Example parsed_data:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "skills": ["Python", "SQL", "Machine Learning"],
            "experience_years": 2,
            "education": [{"degree": "B.Tech", "field": "CS", "institution": "IIT"}],
            "experience": [{"company": "Google", "role": "Intern", "duration": "3 months"}]
        }
        """
        doc = {
            "student_id": student_id,
            "raw_resume_id": raw_resume_id,
            "parsed_data": parsed_data,
            "parsed_at": datetime.utcnow(),
            "version": 1  # Track parsing versions
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_by_student(self, student_id: int) -> Optional[dict]:
        """Fetch latest parsed resume for a student."""
        doc = self.collection.find_one(
            {"student_id": student_id},
            sort=[("parsed_at", -1)]
        )
        return serialize_doc(doc)
    
    def get_skills(self, student_id: int) -> List[str]:
        """Extract just the skills list from parsed resume."""
        doc = self.get_by_student(student_id)
        if doc and "parsed_data" in doc:
            return doc["parsed_data"].get("skills", [])
        return []
    
    def update_parsed_data(self, student_id: int, parsed_data: dict) -> bool:
        """Update parsed data (e.g., after re-parsing with new AI model)."""
        result = self.collection.update_one(
            {"student_id": student_id},
            {
                "$set": {"parsed_data": parsed_data, "parsed_at": datetime.utcnow()},
                "$inc": {"version": 1}
            },
            upsert=False
        )
        return result.modified_count > 0


# ============================================================
# RAW JOB DESCRIPTIONS COLLECTION
# ============================================================

class RawJobDescriptionService:
    """
    Handles raw job description storage.
    """
    
    def __init__(self):
        self.collection: Collection = get_collection(COLLECTIONS["raw_jds"])
    
    def insert(self, job_id: int, jd_text: str) -> str:
        """
        Insert a raw job description.
        
        Args:
            job_id: PostgreSQL job ID (foreign reference)
            jd_text: Full job description text
        
        Returns:
            MongoDB ObjectId as string
        """
        doc = {
            "job_id": job_id,
            "jd_text": jd_text,
            "created_at": datetime.utcnow(),
            "is_parsed": False
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_by_job(self, job_id: int) -> Optional[dict]:
        """Fetch raw JD for a job."""
        doc = self.collection.find_one({"job_id": job_id})
        return serialize_doc(doc)
    
    def mark_as_parsed(self, job_id: int) -> bool:
        """Mark JD as parsed after AI processing."""
        result = self.collection.update_one(
            {"job_id": job_id},
            {"$set": {"is_parsed": True, "parsed_at": datetime.utcnow()}}
        )
        return result.modified_count > 0


# ============================================================
# PARSED JOB DESCRIPTIONS COLLECTION
# ============================================================

class ParsedJobDescriptionService:
    """
    Handles parsed job description storage.
    """
    
    def __init__(self):
        self.collection: Collection = get_collection(COLLECTIONS["parsed_jds"])
    
    def insert(self, job_id: int, raw_jd_id: str, parsed_data: dict) -> str:
        """
        Insert parsed job description data.
        
        Example parsed_data:
        {
            "title": "Software Engineer",
            "required_skills": ["Python", "SQL"],
            "preferred_skills": ["Docker", "AWS"],
            "min_experience": 2,
            "max_experience": 5,
            "education_required": "B.Tech"
        }
        """
        doc = {
            "job_id": job_id,
            "raw_jd_id": raw_jd_id,
            "parsed_data": parsed_data,
            "parsed_at": datetime.utcnow()
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_by_job(self, job_id: int) -> Optional[dict]:
        """Fetch parsed JD for a job."""
        doc = self.collection.find_one({"job_id": job_id})
        return serialize_doc(doc)
    
    def get_required_skills(self, job_id: int) -> List[str]:
        """Extract required skills from parsed JD."""
        doc = self.get_by_job(job_id)
        if doc and "parsed_data" in doc:
            return doc["parsed_data"].get("required_skills", [])
        return []


# ============================================================
# EMBEDDING CACHE COLLECTION
# Stores vector embeddings for similarity matching
# ============================================================

class EmbeddingCacheService:
    """
    Caches embeddings to avoid recomputing them.
    Embeddings are expensive to generate, so we store them.
    """
    
    def __init__(self):
        self.collection: Collection = get_collection(COLLECTIONS["embedding_cache"])
    
    def store_embedding(
        self, 
        entity_type: str,  # 'student' or 'job'
        entity_id: int, 
        embedding: List[float],
        text_hash: str = None  # Hash of source text to detect changes
    ) -> str:
        """
        Store or update an embedding.
        
        Args:
            entity_type: 'student' or 'job'
            entity_id: PostgreSQL ID
            embedding: Vector as list of floats
            text_hash: MD5 hash of source text (to detect if re-embedding needed)
        """
        doc = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "embedding": embedding,
            "text_hash": text_hash,
            "created_at": datetime.utcnow()
        }
        
        # Upsert: update if exists, insert if not
        result = self.collection.update_one(
            {"entity_type": entity_type, "entity_id": entity_id},
            {"$set": doc},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else "updated"
    
    def get_embedding(self, entity_type: str, entity_id: int) -> Optional[List[float]]:
        """Fetch cached embedding."""
        doc = self.collection.find_one({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        if doc:
            return doc.get("embedding")
        return None
    
    def get_all_job_embeddings(self) -> List[dict]:
        """Fetch all job embeddings for batch similarity computation."""
        cursor = self.collection.find({"entity_type": "job"})
        return [{"job_id": doc["entity_id"], "embedding": doc["embedding"]} for doc in cursor]
    
    def delete_embedding(self, entity_type: str, entity_id: int) -> bool:
        """Delete cached embedding (e.g., when resume is updated)."""
        result = self.collection.delete_one({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        return result.deleted_count > 0


# ============================================================
# CONVENIENCE FUNCTION: Get all services
# ============================================================

def get_mongo_services() -> dict:
    """
    Get all MongoDB service instances.
    
    Usage:
        services = get_mongo_services()
        services['raw_resumes'].insert(...)
    """
    return {
        "raw_resumes": RawResumeService(),
        "parsed_resumes": ParsedResumeService(),
        "raw_jds": RawJobDescriptionService(),
        "parsed_jds": ParsedJobDescriptionService(),
        "embeddings": EmbeddingCacheService()
    }