#!/usr/bin/env python3
"""
AI Parsing Test Script

Tests:
1. Resume parsing with DeepSeek
2. Job description parsing
3. Skill extraction and normalization

IMPORTANT: This script requires:
- Valid DEEPSEEK_API_KEY in .env
- PostgreSQL running with schema created
- MongoDB running

Run: python scripts/test_ai_parsing.py
"""
import sys
sys.path.insert(0, '.')

from app.services.deepseek_client import get_deepseek_client
from app.services.ai_parsing_service import (
    validate_parsed_resume,
    validate_parsed_jd,
    SkillExtractionService
)


# ============================================================
# SAMPLE DATA FOR TESTING
# ============================================================

SAMPLE_RESUME = """
PRIYA SHARMA
Email: priya.sharma@gmail.com | Phone: +91-9876543210
LinkedIn: linkedin.com/in/priyasharma | GitHub: github.com/priyasharma

SUMMARY
Passionate software engineer with 2 years of experience in full-stack development.
Strong background in Python, React, and cloud technologies.

EDUCATION
Bachelor of Technology in Computer Science
Indian Institute of Technology, Delhi
2018 - 2022 | CGPA: 8.7/10

SKILLS
Programming: Python, JavaScript, TypeScript, Java, SQL
Frontend: React.js, Next.js, HTML5, CSS3, Tailwind CSS
Backend: Node.js, Django, FastAPI, Express.js
Databases: PostgreSQL, MongoDB, Redis
Cloud & DevOps: AWS (EC2, S3, Lambda), Docker, Kubernetes, CI/CD
Tools: Git, JIRA, Postman, VS Code

EXPERIENCE

Software Engineer | TechCorp Solutions, Bangalore
June 2022 - Present (2 years)
- Developed and maintained RESTful APIs using Python and FastAPI
- Built responsive web applications using React.js and TypeScript
- Implemented CI/CD pipelines reducing deployment time by 60%
- Optimized database queries improving response time by 40%

Software Engineering Intern | StartupXYZ, Mumbai
January 2022 - May 2022 (5 months)
- Built internal dashboard using React and Node.js
- Worked with PostgreSQL database and wrote complex SQL queries
- Participated in code reviews and agile ceremonies

PROJECTS
1. E-commerce Platform - Full-stack application with React, Node.js, PostgreSQL
2. Real-time Chat App - WebSocket-based chat using Socket.io
3. ML Pipeline - Automated ML training pipeline using Python and AWS

CERTIFICATIONS
- AWS Certified Developer Associate
- MongoDB Certified Developer
"""

SAMPLE_JOB_DESCRIPTION = """
Senior Software Engineer - Backend

Company: InnovateTech Solutions
Location: Bangalore, India (Hybrid - 3 days office)
Experience: 3-6 years

About Us:
InnovateTech is a fast-growing fintech startup revolutionizing digital payments.

Role Overview:
We are looking for a Senior Backend Engineer to join our platform team.
You will be responsible for designing and building scalable microservices.

Requirements:
- Strong proficiency in Python (Django/FastAPI) or Java (Spring Boot)
- Experience with PostgreSQL or MySQL databases
- Solid understanding of RESTful API design principles
- Experience with message queues (RabbitMQ, Kafka)
- Knowledge of Docker and container orchestration
- 3+ years of professional backend development experience

Nice to Have:
- Experience with AWS or GCP cloud services
- Knowledge of Kubernetes
- Experience with GraphQL
- Understanding of event-driven architecture
- Contributions to open source projects

Education:
- B.Tech/B.E. in Computer Science or equivalent

What We Offer:
- Competitive salary: 25-40 LPA
- Stock options
- Health insurance
- Flexible work hours
- Learning budget
"""


def test_resume_parsing():
    """Test resume parsing with DeepSeek."""
    print("\n" + "=" * 60)
    print("[1] TESTING RESUME PARSING")
    print("=" * 60)
    
    client = get_deepseek_client()
    
    print("\n📄 Input: Sample resume (Priya Sharma)")
    print("-" * 40)
    
    # Parse resume
    print("\n🤖 Calling DeepSeek API...")
    parsed = client.parse_resume(SAMPLE_RESUME)
    
    print("\n📋 Raw AI Output:")
    print(f"   Name: {parsed.get('name')}")
    print(f"   Email: {parsed.get('email')}")
    print(f"   Phone: {parsed.get('phone')}")
    print(f"   Skills: {parsed.get('skills', [])[:5]}...")  # First 5
    print(f"   Experience Years: {parsed.get('experience_years')}")
    print(f"   Education Count: {len(parsed.get('education', []))}")
    print(f"   Experience Count: {len(parsed.get('experience', []))}")
    
    # Validate
    validated = validate_parsed_resume(parsed)
    print("\n✅ Validated Output:")
    print(f"   Name: {validated['name']}")
    print(f"   Skills ({len(validated['skills'])}): {validated['skills']}")
    print(f"   Experience Years: {validated['experience_years']}")
    
    return validated


def test_jd_parsing():
    """Test job description parsing with DeepSeek."""
    print("\n" + "=" * 60)
    print("[2] TESTING JOB DESCRIPTION PARSING")
    print("=" * 60)
    
    client = get_deepseek_client()
    
    print("\n📄 Input: Sample JD (Senior Software Engineer)")
    print("-" * 40)
    
    # Parse JD
    print("\n🤖 Calling DeepSeek API...")
    parsed = client.parse_job_description(SAMPLE_JOB_DESCRIPTION)
    
    print("\n📋 Raw AI Output:")
    print(f"   Title: {parsed.get('title')}")
    print(f"   Required Skills: {parsed.get('required_skills', [])}")
    print(f"   Preferred Skills: {parsed.get('preferred_skills', [])}")
    print(f"   Min Experience: {parsed.get('min_experience')}")
    print(f"   Max Experience: {parsed.get('max_experience')}")
    print(f"   Education: {parsed.get('education_required')}")
    
    # Validate
    validated = validate_parsed_jd(parsed)
    print("\n✅ Validated Output:")
    print(f"   Title: {validated['title']}")
    print(f"   Required Skills ({len(validated['required_skills'])}): {validated['required_skills']}")
    print(f"   Preferred Skills ({len(validated['preferred_skills'])}): {validated['preferred_skills']}")
    print(f"   Experience Range: {validated['min_experience']}-{validated['max_experience']} years")
    
    return validated


def test_skill_normalization():
    """Test skill normalization."""
    print("\n" + "=" * 60)
    print("[3] TESTING SKILL NORMALIZATION")
    print("=" * 60)
    
    client = get_deepseek_client()
    
    # Test with abbreviated/informal skill names
    raw_skills = ["JS", "TS", "py", "postgres", "k8s", "ML", "DL", "node"]
    
    print(f"\n📝 Input Skills: {raw_skills}")
    print("\n🤖 Calling DeepSeek API for normalization...")
    
    normalized = client.normalize_skills(raw_skills)
    
    print(f"\n✅ Normalized Skills: {normalized}")
    
    print("\n📊 Mapping:")
    for raw, norm in zip(raw_skills, normalized):
        print(f"   {raw:10} → {norm}")
    
    return normalized


def test_skill_extraction():
    """Test standalone skill extraction from arbitrary text."""
    print("\n" + "=" * 60)
    print("[4] TESTING SKILL EXTRACTION FROM TEXT")
    print("=" * 60)
    
    extractor = SkillExtractionService()
    
    sample_text = """
    Looking for someone who knows React and Node.js.
    Must have experience with AWS and Docker.
    Python is a plus. Good communication skills required.
    """
    
    print(f"\n📝 Input Text: '{sample_text.strip()}'")
    print("\n🤖 Extracting skills...")
    
    skills = extractor.extract_skills(sample_text)
    
    print(f"\n✅ Extracted Skills: {skills}")
    
    return skills


def test_api_connection():
    """Test basic API connection."""
    print("\n" + "=" * 60)
    print("[0] TESTING DEEPSEEK API CONNECTION")
    print("=" * 60)
    
    client = get_deepseek_client()
    
    if client.test_connection():
        print("✅ DeepSeek API: Connected")
        return True
    else:
        print("❌ DeepSeek API: Connection failed")
        print("   Check your DEEPSEEK_API_KEY in .env")
        return False


def main():
    print("\n" + "=" * 60)
    print("AI PARSING SERVICE TEST")
    print("=" * 60)
    
    # Test connection first
    if not test_api_connection():
        print("\n⚠️  Cannot proceed without API connection.")
        return
    
    try:
        # Run all tests
        resume_data = test_resume_parsing()
        jd_data = test_jd_parsing()
        normalized_skills = test_skill_normalization()
        extracted_skills = test_skill_extraction()
        
        print("\n" + "=" * 60)
        print("✅ ALL AI PARSING TESTS PASSED!")
        print("=" * 60)
        
        print("\n📊 Summary:")
        print(f"   - Resume parsed: {resume_data['name']}")
        print(f"   - Resume skills: {len(resume_data['skills'])} extracted")
        print(f"   - JD parsed: {jd_data['title']}")
        print(f"   - JD required skills: {len(jd_data['required_skills'])}")
        print(f"   - Skills normalized: {len(normalized_skills)}")
        print(f"   - Skills extracted from text: {len(extracted_skills)}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()