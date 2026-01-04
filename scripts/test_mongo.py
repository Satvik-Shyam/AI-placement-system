#!/usr/bin/env python3
"""
MongoDB Test Script

Tests all MongoDB collections with sample data.
Run: python scripts/test_mongodb.py
"""
import sys
sys.path.insert(0, '.')

from app.db.mongodb import test_mongo_connection, init_mongo_indexes, get_mongo_db
from app.services.mongo_service import (
    RawResumeService,
    ParsedResumeService,
    RawJobDescriptionService,
    ParsedJobDescriptionService,
    EmbeddingCacheService
)


def test_raw_resumes():
    """Test raw resume operations."""
    print("\n[1] Testing raw_resumes collection...")
    
    service = RawResumeService()
    
    # Sample resume text
    sample_resume = """
    John Doe
    Email: john.doe@email.com | Phone: +91-9876543210
    
    EDUCATION
    B.Tech in Computer Science, IIT Delhi (2020-2024)
    CGPA: 8.5/10
    
    SKILLS
    Programming: Python, Java, JavaScript
    Databases: PostgreSQL, MongoDB
    Frameworks: Django, React, FastAPI
    
    EXPERIENCE
    Software Engineering Intern, Google (May 2023 - July 2023)
    - Built REST APIs using Python and Flask
    - Improved query performance by 40%
    
    PROJECTS
    - E-commerce Platform using Django
    - Real-time Chat Application using WebSockets
    """
    
    # Insert
    mongo_id = service.insert(
        student_id=1,  # Fake ID for testing
        resume_text=sample_resume,
        filename="john_doe_resume.pdf"
    )
    print(f"    ✅ Inserted raw resume: {mongo_id}")
    
    # Fetch
    doc = service.get_by_id(mongo_id)
    print(f"    ✅ Fetched resume for student: {doc['student_id']}")
    
    # Mark as parsed
    service.mark_as_parsed(mongo_id)
    doc = service.get_by_id(mongo_id)
    print(f"    ✅ Marked as parsed: {doc['is_parsed']}")
    
    return mongo_id


def test_parsed_resumes():
    """Test parsed resume operations."""
    print("\n[2] Testing parsed_resumes collection...")
    
    service = ParsedResumeService()
    
    # Sample parsed data (what AI would extract)
    parsed_data = {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "+91-9876543210",
        "skills": ["Python", "Java", "JavaScript", "PostgreSQL", "MongoDB", "Django", "React", "FastAPI"],
        "experience_years": 0.25,  # 3 months internship
        "education": [
            {
                "degree": "B.Tech",
                "field": "Computer Science",
                "institution": "IIT Delhi",
                "year": 2024,
                "cgpa": 8.5
            }
        ],
        "experience": [
            {
                "company": "Google",
                "role": "Software Engineering Intern",
                "duration": "3 months",
                "highlights": ["Built REST APIs", "Improved query performance by 40%"]
            }
        ]
    }
    
    # Insert
    mongo_id = service.insert(
        student_id=1,
        raw_resume_id="test_raw_id",
        parsed_data=parsed_data
    )
    print(f"    ✅ Inserted parsed resume: {mongo_id}")
    
    # Fetch skills
    skills = service.get_skills(student_id=1)
    print(f"    ✅ Extracted skills: {skills[:5]}...")  # First 5
    
    return mongo_id


def test_raw_job_descriptions():
    """Test raw JD operations."""
    print("\n[3] Testing raw_job_descriptions collection...")
    
    service = RawJobDescriptionService()
    
    sample_jd = """
    Software Engineer - Backend
    
    Company: TechCorp India
    Location: Bangalore (Hybrid)
    Experience: 2-5 years
    
    About the Role:
    We are looking for a passionate backend engineer to join our team.
    
    Requirements:
    - Strong proficiency in Python or Java
    - Experience with PostgreSQL or MySQL
    - Knowledge of REST API design
    - Familiarity with Docker and Kubernetes is a plus
    
    Nice to Have:
    - Experience with AWS or GCP
    - Understanding of microservices architecture
    
    Education:
    - B.Tech/B.E. in Computer Science or related field
    
    Salary: 15-25 LPA
    """
    
    # Insert
    mongo_id = service.insert(job_id=1, jd_text=sample_jd)
    print(f"    ✅ Inserted raw JD: {mongo_id}")
    
    # Fetch
    doc = service.get_by_job(job_id=1)
    print(f"    ✅ Fetched JD for job_id: {doc['job_id']}")
    
    return mongo_id


def test_parsed_job_descriptions():
    """Test parsed JD operations."""
    print("\n[4] Testing parsed_job_descriptions collection...")
    
    service = ParsedJobDescriptionService()
    
    parsed_data = {
        "title": "Software Engineer - Backend",
        "required_skills": ["Python", "Java", "PostgreSQL", "MySQL", "REST API"],
        "preferred_skills": ["Docker", "Kubernetes", "AWS", "GCP", "Microservices"],
        "min_experience": 2,
        "max_experience": 5,
        "education_required": "B.Tech/B.E. in Computer Science"
    }
    
    # Insert
    mongo_id = service.insert(
        job_id=1,
        raw_jd_id="test_raw_jd_id",
        parsed_data=parsed_data
    )
    print(f"    ✅ Inserted parsed JD: {mongo_id}")
    
    # Fetch required skills
    skills = service.get_required_skills(job_id=1)
    print(f"    ✅ Required skills: {skills}")
    
    return mongo_id


def test_embedding_cache():
    """Test embedding cache operations."""
    print("\n[5] Testing embedding_cache collection...")
    
    service = EmbeddingCacheService()
    
    # Sample embedding (normally 1536 dimensions for OpenAI, but we'll use small for demo)
    sample_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 20  # 100 dimensions
    
    # Store student embedding
    result = service.store_embedding(
        entity_type="student",
        entity_id=1,
        embedding=sample_embedding,
        text_hash="abc123"
    )
    print(f"    ✅ Stored student embedding: {result}")
    
    # Store job embedding
    result = service.store_embedding(
        entity_type="job",
        entity_id=1,
        embedding=sample_embedding,
        text_hash="def456"
    )
    print(f"    ✅ Stored job embedding: {result}")
    
    # Fetch embedding
    embedding = service.get_embedding(entity_type="student", entity_id=1)
    print(f"    ✅ Fetched embedding length: {len(embedding)}")
    
    # Get all job embeddings
    all_jobs = service.get_all_job_embeddings()
    print(f"    ✅ Total job embeddings: {len(all_jobs)}")
    
    return True


def cleanup_test_data():
    """Remove test data from collections."""
    print("\n[6] Cleaning up test data...")
    
    db = get_mongo_db()
    
    # Delete test documents (student_id=1, job_id=1)
    db["raw_resumes"].delete_many({"student_id": 1})
    db["parsed_resumes"].delete_many({"student_id": 1})
    db["raw_job_descriptions"].delete_many({"job_id": 1})
    db["parsed_job_descriptions"].delete_many({"job_id": 1})
    db["embedding_cache"].delete_many({"entity_id": 1})
    
    print("    ✅ Test data cleaned up")


def main():
    print("=" * 60)
    print("MONGODB COLLECTION TEST")
    print("=" * 60)
    
    # Test connection first
    if not test_mongo_connection():
        print("❌ MongoDB connection failed!")
        return
    
    print("✅ MongoDB connected!")
    
    # Initialize indexes
    init_mongo_indexes()
    
    # Run tests
    try:
        test_raw_resumes()
        test_parsed_resumes()
        test_raw_job_descriptions()
        test_parsed_job_descriptions()
        test_embedding_cache()
        
        print("\n" + "=" * 60)
        print("✅ ALL MONGODB TESTS PASSED!")
        print("=" * 60)
        
        # Ask about cleanup
        response = input("\nClean up test data? (y/n): ").strip().lower()
        if response == 'y':
            cleanup_test_data()
        else:
            print("Test data retained in MongoDB.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()