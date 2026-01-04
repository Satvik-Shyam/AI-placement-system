#!/usr/bin/env python3
"""
Embedding & Matching Test Script

Tests:
1. Embedding generation for students and jobs
2. Cosine similarity computation
3. Skill match percentage calculation
4. Full recommendation pipeline

PREREQUISITES:
- PostgreSQL with schema created
- MongoDB running
- At least one student and one job in the database
- Parsed resume and JD in MongoDB

Run: python scripts/test_matching.py
"""
import sys
sys.path.insert(0, '.')

import numpy as np
from app.services.matching_service import (
    EmbeddingService,
    RecommendationService,
    cosine_similarity,
    compute_skill_match_percentage,
    check_experience_match
)
from app.db.postgres import execute_raw_sql, get_db_session
from app.db.mongodb import get_mongo_db
from sqlalchemy import text


def setup_test_data():
    """Create test data in PostgreSQL and MongoDB for matching tests."""
    print("\n[0] Setting up test data...")
    
    # Create test user, student, company, and job in PostgreSQL
    with get_db_session() as db:
        # Check if test data exists
        result = db.execute(text("SELECT COUNT(*) FROM users WHERE email = 'test_student@test.com'"))
        if result.fetchone()[0] > 0:
            print("    ⚠️  Test data already exists, skipping creation")
            # Get existing IDs
            result = db.execute(text("SELECT student_id FROM students WHERE user_id = (SELECT user_id FROM users WHERE email = 'test_student@test.com')"))
            student_id = result.fetchone()[0]
            result = db.execute(text("SELECT job_id FROM jobs LIMIT 1"))
            row = result.fetchone()
            job_id = row[0] if row else None
            return student_id, job_id
        
        # Create test student user
        result = db.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES ('test_student@test.com', 'hash123', 'student')
                RETURNING user_id
            """)
        )
        student_user_id = result.fetchone()[0]
        
        # Create student profile
        result = db.execute(
            text("""
                INSERT INTO students (user_id, full_name, university, degree, major, graduation_year, cgpa)
                VALUES (:user_id, 'Test Student', 'IIT Delhi', 'B.Tech', 'Computer Science', 2024, 8.5)
                RETURNING student_id
            """),
            {"user_id": student_user_id}
        )
        student_id = result.fetchone()[0]
        
        # Create test company user
        result = db.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES ('test_company@test.com', 'hash456', 'company')
                RETURNING user_id
            """)
        )
        company_user_id = result.fetchone()[0]
        
        # Create company profile
        result = db.execute(
            text("""
                INSERT INTO companies (user_id, company_name, industry, company_size)
                VALUES (:user_id, 'Test Tech Corp', 'Technology', 'medium')
                RETURNING company_id
            """),
            {"user_id": company_user_id}
        )
        company_id = result.fetchone()[0]
        
        # Create test job
        result = db.execute(
            text("""
                INSERT INTO jobs (company_id, title, description, job_type, location, min_experience, max_experience, status)
                VALUES (:company_id, 'Software Engineer', 'Looking for a Python developer', 'full-time', 'Bangalore', 0, 3, 'open')
                RETURNING job_id
            """),
            {"company_id": company_id}
        )
        job_id = result.fetchone()[0]
        
        # Add some skills to student
        skill_ids = db.execute(
            text("SELECT skill_id FROM skills WHERE skill_name IN ('Python', 'JavaScript', 'PostgreSQL', 'React', 'Docker') LIMIT 5")
        ).fetchall()
        
        for (skill_id,) in skill_ids:
            db.execute(
                text("""
                    INSERT INTO student_skills (student_id, skill_id, proficiency_level)
                    VALUES (:student_id, :skill_id, 'intermediate')
                    ON CONFLICT DO NOTHING
                """),
                {"student_id": student_id, "skill_id": skill_id}
            )
        
        # Add required skills to job
        for (skill_id,) in skill_ids[:3]:  # First 3 skills
            db.execute(
                text("""
                    INSERT INTO job_required_skills (job_id, skill_id, is_mandatory)
                    VALUES (:job_id, :skill_id, TRUE)
                    ON CONFLICT DO NOTHING
                """),
                {"job_id": job_id, "skill_id": skill_id}
            )
        
        print(f"    ✅ Created test student (ID: {student_id})")
        print(f"    ✅ Created test company (ID: {company_id})")
        print(f"    ✅ Created test job (ID: {job_id})")
    
    # Create parsed resume in MongoDB
    db = get_mongo_db()
    
    parsed_resume = {
        "student_id": student_id,
        "raw_resume_id": "test_raw_id",
        "parsed_data": {
            "name": "Test Student",
            "email": "test_student@test.com",
            "skills": ["Python", "JavaScript", "PostgreSQL", "React", "Docker", "FastAPI", "Git"],
            "experience_years": 1,
            "education": [{"degree": "B.Tech", "field": "Computer Science", "institution": "IIT Delhi"}],
            "experience": [{"company": "Startup XYZ", "role": "Intern", "duration": "6 months"}]
        },
        "parsed_at": "2024-01-15T10:00:00Z"
    }
    
    db["parsed_resumes"].update_one(
        {"student_id": student_id},
        {"$set": parsed_resume},
        upsert=True
    )
    print(f"    ✅ Created parsed resume in MongoDB")
    
    # Create parsed JD in MongoDB
    parsed_jd = {
        "job_id": job_id,
        "raw_jd_id": "test_raw_jd_id",
        "parsed_data": {
            "title": "Software Engineer",
            "required_skills": ["Python", "PostgreSQL", "REST API"],
            "preferred_skills": ["Docker", "React", "AWS"],
            "min_experience": 0,
            "max_experience": 3,
            "education_required": "B.Tech"
        },
        "parsed_at": "2024-01-15T10:00:00Z"
    }
    
    db["parsed_job_descriptions"].update_one(
        {"job_id": job_id},
        {"$set": parsed_jd},
        upsert=True
    )
    print(f"    ✅ Created parsed JD in MongoDB")
    
    return student_id, job_id


def test_cosine_similarity():
    """Test cosine similarity computation."""
    print("\n[1] Testing cosine similarity...")
    
    # Test 1: Identical vectors (should be 1.0)
    vec1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    vec2 = [1.0, 2.0, 3.0, 4.0, 5.0]
    sim = cosine_similarity(vec1, vec2)
    print(f"    Identical vectors: {sim:.4f} (expected: 1.0)")
    assert abs(sim - 1.0) < 0.001, "Identical vectors should have similarity 1.0"
    
    # Test 2: Orthogonal vectors (should be 0.0)
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    sim = cosine_similarity(vec1, vec2)
    print(f"    Orthogonal vectors: {sim:.4f} (expected: 0.0)")
    assert abs(sim - 0.0) < 0.001, "Orthogonal vectors should have similarity 0.0"
    
    # Test 3: Opposite vectors (should be -1.0)
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [-1.0, -2.0, -3.0]
    sim = cosine_similarity(vec1, vec2)
    print(f"    Opposite vectors: {sim:.4f} (expected: -1.0)")
    assert abs(sim - (-1.0)) < 0.001, "Opposite vectors should have similarity -1.0"
    
    # Test 4: Similar vectors (should be high)
    vec1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    vec2 = [1.1, 2.1, 3.0, 4.0, 4.9]
    sim = cosine_similarity(vec1, vec2)
    print(f"    Similar vectors: {sim:.4f} (expected: >0.99)")
    assert sim > 0.99, "Similar vectors should have high similarity"
    
    print("    ✅ Cosine similarity tests passed!")


def test_skill_matching():
    """Test skill match percentage calculation."""
    print("\n[2] Testing skill match percentage...")
    
    # Test 1: Perfect match
    student_skills = ["Python", "SQL", "Docker"]
    required_skills = ["Python", "SQL", "Docker"]
    pct = compute_skill_match_percentage(student_skills, required_skills)
    print(f"    Perfect match: {pct:.1f}% (expected: 100.0%)")
    assert pct == 100.0
    
    # Test 2: Partial match
    student_skills = ["Python", "JavaScript"]
    required_skills = ["Python", "SQL", "Docker", "AWS"]
    pct = compute_skill_match_percentage(student_skills, required_skills)
    print(f"    Partial match (1/4): {pct:.1f}% (expected: 25.0%)")
    assert pct == 25.0
    
    # Test 3: No match
    student_skills = ["Ruby", "Rails"]
    required_skills = ["Python", "Django"]
    pct = compute_skill_match_percentage(student_skills, required_skills)
    print(f"    No match: {pct:.1f}% (expected: 0.0%)")
    assert pct == 0.0
    
    # Test 4: Case insensitive
    student_skills = ["python", "JAVASCRIPT", "Docker"]
    required_skills = ["Python", "JavaScript", "docker"]
    pct = compute_skill_match_percentage(student_skills, required_skills)
    print(f"    Case insensitive: {pct:.1f}% (expected: 100.0%)")
    assert pct == 100.0
    
    # Test 5: Empty requirements
    student_skills = ["Python"]
    required_skills = []
    pct = compute_skill_match_percentage(student_skills, required_skills)
    print(f"    No requirements: {pct:.1f}% (expected: 100.0%)")
    assert pct == 100.0
    
    print("    ✅ Skill match tests passed!")


def test_experience_matching():
    """Test experience range matching."""
    print("\n[3] Testing experience matching...")
    
    # Test 1: Within range
    result = check_experience_match(2.0, 1, 3)
    print(f"    2 years, range 1-3: {result} (expected: True)")
    assert result == True
    
    # Test 2: Below minimum
    result = check_experience_match(0.5, 2, 5)
    print(f"    0.5 years, range 2-5: {result} (expected: False)")
    assert result == False
    
    # Test 3: Slightly above max (allowed)
    result = check_experience_match(5.0, 2, 4)
    print(f"    5 years, range 2-4: {result} (expected: True, 2yr flexibility)")
    assert result == True
    
    # Test 4: Way above max
    result = check_experience_match(10.0, 2, 4)
    print(f"    10 years, range 2-4: {result} (expected: False)")
    assert result == False
    
    # Test 5: No max limit
    result = check_experience_match(15.0, 5, None)
    print(f"    15 years, min 5, no max: {result} (expected: True)")
    assert result == True
    
    print("    ✅ Experience match tests passed!")


def test_embedding_generation(student_id: int, job_id: int):
    """Test embedding generation for student and job."""
    print("\n[4] Testing embedding generation...")
    
    service = EmbeddingService()
    
    # Generate student embedding
    student_embedding = service.get_student_embedding(student_id)
    if student_embedding:
        print(f"    ✅ Student embedding generated: {len(student_embedding)} dimensions")
        print(f"       First 5 values: {student_embedding[:5]}")
    else:
        print(f"    ⚠️  No student embedding (missing parsed resume?)")
        return None, None
    
    # Generate job embedding
    job_embedding = service.get_job_embedding(job_id)
    if job_embedding:
        print(f"    ✅ Job embedding generated: {len(job_embedding)} dimensions")
        print(f"       First 5 values: {job_embedding[:5]}")
    else:
        print(f"    ⚠️  No job embedding (missing parsed JD?)")
        return student_embedding, None
    
    # Compute similarity between them
    similarity = cosine_similarity(student_embedding, job_embedding)
    print(f"    📊 Student-Job similarity: {similarity:.4f}")
    
    return student_embedding, job_embedding


def test_recommendation_generation(student_id: int):
    """Test full recommendation pipeline."""
    print("\n[5] Testing recommendation generation...")
    
    service = RecommendationService()
    
    # Generate recommendations
    recommendations = service.generate_recommendations(
        student_id=student_id,
        top_n=5,
        min_score=0.0  # Include all for testing
    )
    
    if recommendations:
        print(f"    ✅ Generated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"       {i}. {rec['job_title']}")
            print(f"          Match Score: {rec['match_score']:.2%}")
            print(f"          Skill Match: {rec['skill_match_pct']:.1f}%")
            print(f"          Experience OK: {rec['experience_match']}")
    else:
        print("    ⚠️  No recommendations generated")
        print("       (This is expected if no open jobs exist)")
        return []
    
    return recommendations


def test_recommendation_storage(student_id: int, recommendations: list):
    """Test storing recommendations in PostgreSQL."""
    print("\n[6] Testing recommendation storage...")
    
    if not recommendations:
        print("    ⚠️  No recommendations to store")
        return
    
    service = RecommendationService()
    
    # Store recommendations
    stored_count = service.store_recommendations(student_id, recommendations)
    print(f"    ✅ Stored {stored_count} recommendations in PostgreSQL")
    
    # Fetch them back
    fetched = service.get_student_recommendations(student_id)
    print(f"    ✅ Fetched {len(fetched)} recommendations from PostgreSQL")
    
    if fetched:
        print(f"       Top recommendation: {fetched[0]['job_title']}")
        print(f"       Reason: {fetched[0]['recommendation_reason']}")


def test_sql_verification(student_id: int):
    """Verify recommendations in PostgreSQL with raw SQL."""
    print("\n[7] SQL Verification...")
    
    # Query ai_recommendations table directly
    results = execute_raw_sql("""
        SELECT 
            r.student_id,
            r.job_id,
            j.title,
            r.match_score,
            r.skill_match_pct,
            r.recommendation_reason
        FROM ai_recommendations r
        JOIN jobs j ON r.job_id = j.job_id
        WHERE r.student_id = :student_id
        ORDER BY r.match_score DESC
        LIMIT 5
    """, {"student_id": student_id})
    
    if results:
        print(f"    ✅ Found {len(results)} recommendations in ai_recommendations table:")
        for row in results:
            print(f"       Job: {row['title']}")
            print(f"       Score: {row['match_score']:.4f}, Skills: {row['skill_match_pct']}%")
    else:
        print("    ⚠️  No recommendations found in database")


def cleanup_test_data(student_id: int):
    """Clean up test data."""
    print("\n[8] Cleaning up test data...")
    
    with get_db_session() as db:
        # Delete in reverse order of dependencies
        db.execute(text("DELETE FROM ai_recommendations WHERE student_id = :id"), {"id": student_id})
        db.execute(text("DELETE FROM student_skills WHERE student_id = :id"), {"id": student_id})
        db.execute(text("DELETE FROM applications WHERE student_id = :id"), {"id": student_id})
        db.execute(text("DELETE FROM job_required_skills WHERE job_id IN (SELECT job_id FROM jobs WHERE company_id IN (SELECT company_id FROM companies WHERE user_id = (SELECT user_id FROM users WHERE email = 'test_company@test.com')))"))
        db.execute(text("DELETE FROM jobs WHERE company_id IN (SELECT company_id FROM companies WHERE user_id = (SELECT user_id FROM users WHERE email = 'test_company@test.com'))"))
        db.execute(text("DELETE FROM students WHERE user_id = (SELECT user_id FROM users WHERE email = 'test_student@test.com')"))
        db.execute(text("DELETE FROM companies WHERE user_id = (SELECT user_id FROM users WHERE email = 'test_company@test.com')"))
        db.execute(text("DELETE FROM users WHERE email IN ('test_student@test.com', 'test_company@test.com')"))
    
    # Clean MongoDB
    mongo_db = get_mongo_db()
    mongo_db["parsed_resumes"].delete_many({"student_id": student_id})
    mongo_db["parsed_job_descriptions"].delete_many({"job_id": {"$exists": True}})
    mongo_db["embedding_cache"].delete_many({"entity_id": student_id})
    
    print("    ✅ Test data cleaned up")


def main():
    print("=" * 60)
    print("EMBEDDING & MATCHING SERVICE TEST")
    print("=" * 60)
    
    try:
        # Setup test data
        student_id, job_id = setup_test_data()
        
        # Run unit tests
        test_cosine_similarity()
        test_skill_matching()
        test_experience_matching()
        
        # Run integration tests
        if student_id and job_id:
            test_embedding_generation(student_id, job_id)
            recommendations = test_recommendation_generation(student_id)
            test_recommendation_storage(student_id, recommendations)
            test_sql_verification(student_id)
        
        print("\n" + "=" * 60)
        print("✅ ALL MATCHING TESTS PASSED!")
        print("=" * 60)
        
        # Cleanup prompt
        response = input("\nClean up test data? (y/n): ").strip().lower()
        if response == 'y':
            cleanup_test_data(student_id)
        else:
            print(f"Test data retained. Student ID: {student_id}, Job ID: {job_id}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()