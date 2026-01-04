"""
Job Routes

POST /jobs - Create job posting (company only)
GET /jobs - List all open jobs with filters
GET /jobs/{job_id} - Get job details
PUT /jobs/{job_id} - Update job (company only)
DELETE /jobs/{job_id} - Delete job (company only)
POST /jobs/{job_id}/apply - Apply to job (student only)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from typing import List, Optional

from app.db.postgres import get_db_session, execute_raw_sql
from app.core.auth import get_current_student, get_current_company
from app.services.ai_parsing_service import get_jd_parser
from app.schemas.schemas import (
    JobCreate, JobUpdate, JobResponse, JobListResponse,
    ApplicationCreate, MessageResponse
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreate, company: dict = Depends(get_current_company)):
    """Create a new job posting. Only companies can create jobs."""
    with get_db_session() as db:
        # Create job
        result = db.execute(
            text("""
                INSERT INTO jobs (company_id, title, description, job_type, location, is_remote,
                    min_experience, max_experience, min_salary, max_salary, currency, openings,
                    application_deadline, status)
                VALUES (:company_id, :title, :description, :job_type, :location, :is_remote,
                    :min_exp, :max_exp, :min_salary, :max_salary, :currency, :openings, :deadline, 'open')
                RETURNING job_id, created_at
            """),
            {
                "company_id": company["company_id"], "title": job.title, "description": job.description,
                "job_type": job.job_type.value, "location": job.location, "is_remote": job.is_remote,
                "min_exp": job.min_experience, "max_exp": job.max_experience,
                "min_salary": job.min_salary, "max_salary": job.max_salary,
                "currency": job.currency, "openings": job.openings, "deadline": job.application_deadline
            }
        )
        job_id, created_at = result.fetchone()
        
        # Add required skills
        for skill_name in job.required_skills:
            skill_result = db.execute(
                text("INSERT INTO skills (skill_name, category) VALUES (:name, 'uncategorized') ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name RETURNING skill_id"),
                {"name": skill_name}
            )
            skill_id = skill_result.fetchone()[0]
            db.execute(
                text("INSERT INTO job_required_skills (job_id, skill_id, is_mandatory) VALUES (:jid, :sid, TRUE) ON CONFLICT DO NOTHING"),
                {"jid": job_id, "sid": skill_id}
            )
        
        # Add preferred skills
        for skill_name in job.preferred_skills:
            skill_result = db.execute(
                text("INSERT INTO skills (skill_name, category) VALUES (:name, 'uncategorized') ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name RETURNING skill_id"),
                {"name": skill_name}
            )
            skill_id = skill_result.fetchone()[0]
            db.execute(
                text("INSERT INTO job_required_skills (job_id, skill_id, is_mandatory) VALUES (:jid, :sid, FALSE) ON CONFLICT DO NOTHING"),
                {"jid": job_id, "sid": skill_id}
            )
        
        # Get company name
        cn_result = db.execute(text("SELECT company_name FROM companies WHERE company_id = :id"), {"id": company["company_id"]})
        company_name = cn_result.fetchone()[0]
    
    # Parse JD with AI (background, non-blocking)
    if job.description:
        try:
            parser = get_jd_parser()
            parser.parse_and_store(job_id, job.description)
        except Exception:
            pass
    
    return JobResponse(
        job_id=job_id, company_id=company["company_id"], company_name=company_name,
        title=job.title, description=job.description, job_type=job.job_type.value,
        location=job.location, is_remote=job.is_remote, min_experience=job.min_experience,
        max_experience=job.max_experience, min_salary=job.min_salary, max_salary=job.max_salary,
        currency=job.currency, openings=job.openings, application_deadline=job.application_deadline,
        status="open", required_skills=job.required_skills, preferred_skills=job.preferred_skills,
        created_at=created_at
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None, description="Search in title"),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    remote_only: bool = Query(False),
    skill: Optional[str] = Query(None, description="Filter by required skill")
):
    """List all open job postings with filters and pagination."""
    # Base query
    sql = """
        SELECT DISTINCT j.job_id, j.company_id, c.company_name, j.title, j.description, j.job_type,
               j.location, j.is_remote, j.min_experience, j.max_experience, j.min_salary,
               j.max_salary, j.currency, j.openings, j.application_deadline, j.status, j.created_at
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        LEFT JOIN job_required_skills jrs ON j.job_id = jrs.job_id
        LEFT JOIN skills sk ON jrs.skill_id = sk.skill_id
        WHERE j.status = 'open'
    """
    params = {}
    
    if search:
        sql += " AND j.title ILIKE :search"
        params["search"] = f"%{search}%"
    if location:
        sql += " AND j.location ILIKE :location"
        params["location"] = f"%{location}%"
    if job_type:
        sql += " AND j.job_type = :job_type"
        params["job_type"] = job_type
    if remote_only:
        sql += " AND j.is_remote = TRUE"
    if skill:
        sql += " AND LOWER(sk.skill_name) = LOWER(:skill)"
        params["skill"] = skill
    
    # Get total count
    count_results = execute_raw_sql(sql, params)
    total = len(count_results)
    
    # Paginate
    offset = (page - 1) * page_size
    sql += f" ORDER BY j.created_at DESC LIMIT {page_size} OFFSET {offset}"
    results = execute_raw_sql(sql, params)
    
    jobs = []
    for r in results:
        skills = execute_raw_sql("""
            SELECT sk.skill_name, jrs.is_mandatory FROM job_required_skills jrs
            JOIN skills sk ON jrs.skill_id = sk.skill_id WHERE jrs.job_id = :jid
        """, {"jid": r["job_id"]})
        
        jobs.append(JobResponse(
            job_id=r["job_id"], company_id=r["company_id"], company_name=r["company_name"],
            title=r["title"], description=r["description"], job_type=r["job_type"],
            location=r["location"], is_remote=r["is_remote"], min_experience=r["min_experience"],
            max_experience=r["max_experience"],
            min_salary=float(r["min_salary"]) if r["min_salary"] else None,
            max_salary=float(r["max_salary"]) if r["max_salary"] else None,
            currency=r["currency"], openings=r["openings"], application_deadline=r["application_deadline"],
            status=r["status"],
            required_skills=[s["skill_name"] for s in skills if s["is_mandatory"]],
            preferred_skills=[s["skill_name"] for s in skills if not s["is_mandatory"]],
            created_at=r["created_at"]
        ))
    
    return JobListResponse(jobs=jobs, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int):
    """Get details of a specific job."""
    results = execute_raw_sql("""
        SELECT j.job_id, j.company_id, c.company_name, j.title, j.description, j.job_type,
               j.location, j.is_remote, j.min_experience, j.max_experience, j.min_salary,
               j.max_salary, j.currency, j.openings, j.application_deadline, j.status, j.created_at
        FROM jobs j JOIN companies c ON j.company_id = c.company_id
        WHERE j.job_id = :jid
    """, {"jid": job_id})
    
    if not results:
        raise HTTPException(status_code=404, detail="Job not found")
    
    r = results[0]
    skills = execute_raw_sql("""
        SELECT sk.skill_name, jrs.is_mandatory FROM job_required_skills jrs
        JOIN skills sk ON jrs.skill_id = sk.skill_id WHERE jrs.job_id = :jid
    """, {"jid": job_id})
    
    return JobResponse(
        job_id=r["job_id"], company_id=r["company_id"], company_name=r["company_name"],
        title=r["title"], description=r["description"], job_type=r["job_type"],
        location=r["location"], is_remote=r["is_remote"], min_experience=r["min_experience"],
        max_experience=r["max_experience"],
        min_salary=float(r["min_salary"]) if r["min_salary"] else None,
        max_salary=float(r["max_salary"]) if r["max_salary"] else None,
        currency=r["currency"], openings=r["openings"], application_deadline=r["application_deadline"],
        status=r["status"],
        required_skills=[s["skill_name"] for s in skills if s["is_mandatory"]],
        preferred_skills=[s["skill_name"] for s in skills if not s["is_mandatory"]],
        created_at=r["created_at"]
    )


@router.put("/{job_id}", response_model=MessageResponse)
async def update_job(job_id: int, update: JobUpdate, company: dict = Depends(get_current_company)):
    """Update a job posting. Only the owning company can update."""
    with get_db_session() as db:
        result = db.execute(
            text("SELECT job_id FROM jobs WHERE job_id = :jid AND company_id = :cid"),
            {"jid": job_id, "cid": company["company_id"]}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Job not found or access denied")
        
        updates = []
        params = {"jid": job_id}
        
        for field in ["title", "description", "location", "is_remote", "min_experience", "max_experience", "min_salary", "max_salary", "openings", "application_deadline"]:
            value = getattr(update, field, None)
            if value is not None:
                updates.append(f"{field} = :{field}")
                params[field] = value
        
        if update.job_type:
            updates.append("job_type = :job_type")
            params["job_type"] = update.job_type.value
        if update.status:
            updates.append("status = :status")
            params["status"] = update.status.value
        
        if updates:
            db.execute(
                text(f"UPDATE jobs SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE job_id = :jid"),
                params
            )
    
    return MessageResponse(message="Job updated successfully")


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job(job_id: int, company: dict = Depends(get_current_company)):
    """Delete a job posting. Cascades to applications."""
    with get_db_session() as db:
        result = db.execute(
            text("DELETE FROM jobs WHERE job_id = :jid AND company_id = :cid"),
            {"jid": job_id, "cid": company["company_id"]}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found or access denied")
    
    return MessageResponse(message="Job deleted successfully")


@router.post("/{job_id}/apply", response_model=MessageResponse)
async def apply_to_job(job_id: int, application: ApplicationCreate, student: dict = Depends(get_current_student)):
    """Apply to a job. Students only. Cannot apply twice to same job."""
    with get_db_session() as db:
        # Check job exists and is open
        result = db.execute(text("SELECT status FROM jobs WHERE job_id = :jid"), {"jid": job_id})
        job = result.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job[0] != 'open':
            raise HTTPException(status_code=400, detail="Job is not accepting applications")
        
        # Check not already applied
        result = db.execute(
            text("SELECT application_id FROM applications WHERE student_id = :sid AND job_id = :jid"),
            {"sid": student["student_id"], "jid": job_id}
        )
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Already applied to this job")
        
        # Create application
        db.execute(
            text("INSERT INTO applications (student_id, job_id, cover_letter, status) VALUES (:sid, :jid, :cover, 'applied')"),
            {"sid": student["student_id"], "jid": job_id, "cover": application.cover_letter}
        )
        
        # Mark recommendation as applied (if exists)
        db.execute(
            text("UPDATE ai_recommendations SET is_applied = TRUE WHERE student_id = :sid AND job_id = :jid"),
            {"sid": student["student_id"], "jid": job_id}
        )
    
    return MessageResponse(message="Application submitted successfully")