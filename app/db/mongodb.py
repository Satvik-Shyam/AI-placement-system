"""
MongoDB Connection Utility

MongoDB stores:
- Raw resume documents (PDFs as text)
- AI-parsed outputs (structured JSON)
- Raw job descriptions
- AI extraction results

WHY MongoDB for these?
- Schema-flexible: AI outputs vary in structure
- Document-oriented: Natural fit for resumes/JDs
- No joins needed: Each document is self-contained
"""
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from app.core.config import get_settings

settings = get_settings()

# Global client (connection pooling handled internally by pymongo)
_client: MongoClient = None
_db: Database = None


def get_mongo_client() -> MongoClient:
    """Get or create MongoDB client (singleton pattern)"""
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_mongo_db() -> Database:
    """Get the placement_docs database"""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[settings.mongodb_db]
    return _db


def get_collection(name: str) -> Collection:
    """
    Get a specific collection.
    Collections we'll use:
    - raw_resumes: Original resume text
    - parsed_resumes: AI-extracted resume data
    - raw_job_descriptions: Original JD text
    - parsed_job_descriptions: AI-extracted JD data
    - embedding_cache: Cached embeddings for similarity
    """
    db = get_mongo_db()
    return db[name]


def test_mongo_connection() -> bool:
    """
    Test if MongoDB is reachable.
    Returns True if connection successful, False otherwise.
    """
    try:
        client = get_mongo_client()
        # ping command checks connection
        client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False


# Collection name constants (avoid typos)
COLLECTIONS = {
    "raw_resumes": "raw_resumes",
    "parsed_resumes": "parsed_resumes",
    "raw_jds": "raw_job_descriptions",
    "parsed_jds": "parsed_job_descriptions",
    "embedding_cache": "embedding_cache"
}


def init_mongo_indexes():
    """
    Create indexes for better query performance.
    Call this once during app startup.
    """
    db = get_mongo_db()
    
    # Index on student_id for quick resume lookups
    db[COLLECTIONS["raw_resumes"]].create_index("student_id")
    db[COLLECTIONS["parsed_resumes"]].create_index("student_id")
    
    # Index on job_id for JD lookups
    db[COLLECTIONS["raw_jds"]].create_index("job_id")
    db[COLLECTIONS["parsed_jds"]].create_index("job_id")
    
    # Compound index for embedding cache
    db[COLLECTIONS["embedding_cache"]].create_index([
        ("entity_type", 1),
        ("entity_id", 1)
    ], unique=True)
    
    print("MongoDB indexes created successfully")