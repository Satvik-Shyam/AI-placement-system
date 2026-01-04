"""
Student Routes

POST /students/profile - Create student profile
GET /students/profile - Get own profile
PUT /students/profile - Update profile
POST /students/resume/upload - Upload resume (PDF/DOCX/TXT)
GET /students/resume/formats - Get supported formats
GET /students/skills - Get skills
POST /students/skills - Add skill
DELETE /students/skills/{skill_id} - Remove skill
GET /students/applications - Get my applications
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy import text
from typing import List

from app.db.postgres import get_db_session, execute_raw_sql
from app.core.auth import get_current_user, get_current_student
from app.utils.file_upload import extract_text_from_file, get_supported_formats
from app.services.ai_parsing_service import get_resume_parser
from app.schemas.schemas import (
    StudentCreate, StudentUpdate, StudentResponse, SkillAdd,
    ResumeUploadResponse, ApplicationResponse, MessageResponse
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/profile", response_model=MessageResponse, status_code=201)
async def create_profile(data: StudentCreate, user: dict = Depends(get_current_user)):
    """Create student profile. User must be registered as student."""
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only student accounts can create student profiles")
    
    with get_db_session() as db:
        # Check profile exists
        result = db.execute(
            text("SELECT student_id FROM students WHERE user_id = :id"),
            {"id": user["user_id"]}
        )
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")
        
        # Create profile
        db.execute(
            text("""
                INSERT INTO students (user_id, full_name, phone, university, degree, major, graduation_year, cgpa)
                VALUES (:user_id, :full_name, :phone, :university, :degree, :major, :graduation_year, :cgpa)
            """),
            {
                "user_id": user["user_id"],
                "full_name": data.full_name,
                "phone": data.phone,
                "university": data.university,
                "degree": data.degree,
                "major": data.major,
                "graduation_year": data.graduation_year,
                "cgpa": data.cgpa
            }
        )
    
    return MessageResponse(message="Student profile created successfully")


@router.get("/profile", response_model=StudentResponse)
async def get_profile(student: dict = Depends(get_current_student)):
    """Get current student's profile with skills."""
    with get_db_session() as db:
        result = db.execute(
            text("""
                SELECT s.student_id, s.user_id, s.full_name, u.email, s.phone, s.university,
                       s.degree, s.major, s.graduation_year, s.cgpa, s.resume_mongo_id, s.created_at
                FROM students s JOIN users u ON s.user_id = u.user_id
                WHERE s.student_id = :id
            """),
            {"id": student["student_id"]}
        )
        row = result.fetchone()
        
        # Get skills
        skills_result = db.execute(
            text("""
                SELECT sk.skill_name FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.skill_id
                WHERE ss.student_id = :id ORDER BY sk.skill_name
            """),
            {"id": student["student_id"]}
        )
        skills = [r[0] for r in skills_result.fetchall()]
    
    return StudentResponse(
        student_id=row[0], user_id=row[1], full_name=row[2], email=row[3],
        phone=row[4], university=row[5], degree=row[6], major=row[7],
        graduation_year=row[8], cgpa=float(row[9]) if row[9] else None,
        resume_uploaded=row[10] is not None, skills=skills, created_at=row[11]
    )


@router.put("/profile", response_model=MessageResponse)
async def update_profile(data: StudentUpdate, student: dict = Depends(get_current_student)):
    """Update student profile. Only provided fields are updated."""
    updates = []
    params = {"id": student["student_id"]}
    
    for field in ["full_name", "phone", "university", "degree", "major", "graduation_year", "cgpa"]:
        value = getattr(data, field)
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    with get_db_session() as db:
        db.execute(
            text(f"UPDATE students SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE student_id = :id"),
            params
        )
    
    return MessageResponse(message="Profile updated successfully")


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    student: dict = Depends(get_current_student)
):
    """
    Upload and parse resume using AI.
    
    Supported formats: PDF, DOCX, TXT (max 5MB)
    
    Process:
    1. Extract text from file
    2. AI parses to extract skills, experience, education
    3. Store in MongoDB
    4. Sync skills to PostgreSQL
    """
    # Extract text from file
    resume_text, filename = await extract_text_from_file(file)
    
    # Parse with AI
    parser = get_resume_parser()
    result = parser.parse_and_store(
        student_id=student["student_id"],
        resume_text=resume_text,
        filename=filename
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Parse failed: {result.get('error')}")
    
    extracted_skills = result["parsed_data"].get("skills", []) if result["parsed_data"] else []
    
    return ResumeUploadResponse(
        success=True,
        message=f"Resume parsed. {result['skills_synced']} skills synced to profile.",
        filename=filename,
        extracted_skills=extracted_skills,
        skills_synced=result["skills_synced"],
        parsed_data=result["parsed_data"]
    )


@router.get("/resume/formats")
async def resume_formats():
    """Get supported resume file formats."""
    return get_supported_formats()


@router.get("/skills")
async def get_skills(student: dict = Depends(get_current_student)):
    """Get all skills for current student."""
    results = execute_raw_sql("""
        SELECT sk.skill_id, sk.skill_name, sk.category, ss.proficiency_level
        FROM student_skills ss JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = :id ORDER BY sk.skill_name
    """, {"id": student["student_id"]})
    return results


@router.post("/skills", response_model=MessageResponse)
async def add_skill(skill: SkillAdd, student: dict = Depends(get_current_student)):
    """Add a skill to profile. Creates skill if it doesn't exist."""
    with get_db_session() as db:
        # Find or create skill
        result = db.execute(
            text("""
                INSERT INTO skills (skill_name, category) VALUES (:name, 'uncategorized')
                ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
                RETURNING skill_id
            """),
            {"name": skill.skill_name}
        )
        skill_id = result.fetchone()[0]
        
        # Add to student
        db.execute(
            text("""
                INSERT INTO student_skills (student_id, skill_id, proficiency_level)
                VALUES (:student_id, :skill_id, :level)
                ON CONFLICT (student_id, skill_id) DO UPDATE SET proficiency_level = EXCLUDED.proficiency_level
            """),
            {"student_id": student["student_id"], "skill_id": skill_id, "level": skill.proficiency_level.value}
        )
    
    return MessageResponse(message=f"Skill '{skill.skill_name}' added")


@router.delete("/skills/{skill_id}", response_model=MessageResponse)
async def remove_skill(skill_id: int, student: dict = Depends(get_current_student)):
    """Remove a skill from profile."""
    with get_db_session() as db:
        result = db.execute(
            text("DELETE FROM student_skills WHERE student_id = :sid AND skill_id = :skid"),
            {"sid": student["student_id"], "skid": skill_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Skill not found in profile")
    
    return MessageResponse(message="Skill removed")


@router.get("/applications", response_model=List[ApplicationResponse])
async def get_my_applications(student: dict = Depends(get_current_student)):
    """Get all job applications for current student."""
    results = execute_raw_sql("""
        SELECT a.application_id, a.student_id, s.full_name, a.job_id, j.title, c.company_name,
               a.status, a.cover_letter, a.applied_at, a.updated_at
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE a.student_id = :id ORDER BY a.applied_at DESC
    """, {"id": student["student_id"]})
    
    return [
        ApplicationResponse(
            application_id=r["application_id"], student_id=r["student_id"], student_name=r["full_name"],
            job_id=r["job_id"], job_title=r["title"], company_name=r["company_name"],
            status=r["status"], cover_letter=r["cover_letter"],
            applied_at=r["applied_at"], updated_at=r["updated_at"]
        ) for r in results
    ]