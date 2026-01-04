"""
Company Routes

POST /companies/profile - Create company profile
GET /companies/profile - Get own profile
PUT /companies/profile - Update profile
GET /companies/jobs - Get company's jobs
GET /companies/applications - Get applications received
PUT /companies/applications/{id}/status - Update application status
GET /companies/stats - Get hiring stats from SQL view
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from typing import List, Optional

from app.db.postgres import get_db_session, execute_raw_sql
from app.core.auth import get_current_user, get_current_company
from app.schemas.schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse, JobResponse,
    ApplicationResponse, ApplicationStatusUpdate, CompanyStatsResponse, MessageResponse
)

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("/profile", response_model=MessageResponse, status_code=201)
async def create_profile(data: CompanyCreate, user: dict = Depends(get_current_user)):
    """Create company profile. User must be registered as company."""
    if user["role"] != "company":
        raise HTTPException(status_code=403, detail="Only company accounts can create company profiles")
    
    with get_db_session() as db:
        result = db.execute(
            text("SELECT company_id FROM companies WHERE user_id = :id"),
            {"id": user["user_id"]}
        )
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Profile already exists")
        
        db.execute(
            text("""
                INSERT INTO companies (user_id, company_name, industry, company_size, website, description, headquarters, founded_year)
                VALUES (:user_id, :company_name, :industry, :company_size, :website, :description, :headquarters, :founded_year)
            """),
            {
                "user_id": user["user_id"],
                "company_name": data.company_name,
                "industry": data.industry,
                "company_size": data.company_size.value if data.company_size else None,
                "website": data.website,
                "description": data.description,
                "headquarters": data.headquarters,
                "founded_year": data.founded_year
            }
        )
    
    return MessageResponse(message="Company profile created successfully")


@router.get("/profile", response_model=CompanyResponse)
async def get_profile(company: dict = Depends(get_current_company)):
    """Get current company's profile."""
    with get_db_session() as db:
        result = db.execute(
            text("""
                SELECT c.company_id, c.user_id, c.company_name, u.email, c.industry, c.company_size,
                       c.website, c.description, c.headquarters, c.founded_year, c.is_verified, c.created_at
                FROM companies c JOIN users u ON c.user_id = u.user_id
                WHERE c.company_id = :id
            """),
            {"id": company["company_id"]}
        )
        row = result.fetchone()
    
    return CompanyResponse(
        company_id=row[0], user_id=row[1], company_name=row[2], email=row[3],
        industry=row[4], company_size=row[5], website=row[6], description=row[7],
        headquarters=row[8], founded_year=row[9], is_verified=row[10], created_at=row[11]
    )


@router.put("/profile", response_model=MessageResponse)
async def update_profile(data: CompanyUpdate, company: dict = Depends(get_current_company)):
    """Update company profile."""
    updates = []
    params = {"id": company["company_id"]}
    
    if data.company_name: updates.append("company_name = :company_name"); params["company_name"] = data.company_name
    if data.industry: updates.append("industry = :industry"); params["industry"] = data.industry
    if data.company_size: updates.append("company_size = :company_size"); params["company_size"] = data.company_size.value
    if data.website: updates.append("website = :website"); params["website"] = data.website
    if data.description: updates.append("description = :description"); params["description"] = data.description
    if data.headquarters: updates.append("headquarters = :headquarters"); params["headquarters"] = data.headquarters
    if data.founded_year: updates.append("founded_year = :founded_year"); params["founded_year"] = data.founded_year
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    with get_db_session() as db:
        db.execute(
            text(f"UPDATE companies SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE company_id = :id"),
            params
        )
    
    return MessageResponse(message="Profile updated successfully")


@router.get("/jobs", response_model=List[JobResponse])
async def get_company_jobs(
    status: Optional[str] = Query(None),
    company: dict = Depends(get_current_company)
):
    """Get all jobs posted by this company."""
    sql = """
        SELECT j.job_id, j.company_id, c.company_name, j.title, j.description, j.job_type,
               j.location, j.is_remote, j.min_experience, j.max_experience, j.min_salary,
               j.max_salary, j.currency, j.openings, j.application_deadline, j.status, j.created_at
        FROM jobs j JOIN companies c ON j.company_id = c.company_id
        WHERE j.company_id = :cid
    """
    params = {"cid": company["company_id"]}
    
    if status:
        sql += " AND j.status = :status"
        params["status"] = status
    
    sql += " ORDER BY j.created_at DESC"
    results = execute_raw_sql(sql, params)
    
    jobs = []
    for r in results:
        # Get skills
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
    
    return jobs


@router.get("/applications", response_model=List[ApplicationResponse])
async def get_applications(
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    company: dict = Depends(get_current_company)
):
    """Get all applications for company's job postings."""
    sql = """
        SELECT a.application_id, a.student_id, s.full_name, a.job_id, j.title, c.company_name,
               a.status, a.cover_letter, a.applied_at, a.updated_at
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.company_id = :cid
    """
    params = {"cid": company["company_id"]}
    
    if job_id:
        sql += " AND a.job_id = :jid"
        params["jid"] = job_id
    if status:
        sql += " AND a.status = :status"
        params["status"] = status
    
    sql += " ORDER BY a.applied_at DESC"
    results = execute_raw_sql(sql, params)
    
    return [
        ApplicationResponse(
            application_id=r["application_id"], student_id=r["student_id"], student_name=r["full_name"],
            job_id=r["job_id"], job_title=r["title"], company_name=r["company_name"],
            status=r["status"], cover_letter=r["cover_letter"],
            applied_at=r["applied_at"], updated_at=r["updated_at"]
        ) for r in results
    ]


@router.put("/applications/{application_id}/status", response_model=MessageResponse)
async def update_application_status(
    application_id: int,
    update: ApplicationStatusUpdate,
    company: dict = Depends(get_current_company)
):
    """Update status of a job application."""
    with get_db_session() as db:
        # Verify ownership
        result = db.execute(
            text("""
                SELECT a.application_id FROM applications a
                JOIN jobs j ON a.job_id = j.job_id
                WHERE a.application_id = :aid AND j.company_id = :cid
            """),
            {"aid": application_id, "cid": company["company_id"]}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Application not found")
        
        db.execute(
            text("""
                UPDATE applications SET status = :status, notes = COALESCE(:notes, notes), updated_at = CURRENT_TIMESTAMP
                WHERE application_id = :aid
            """),
            {"aid": application_id, "status": update.status.value, "notes": update.notes}
        )
    
    return MessageResponse(message=f"Status updated to '{update.status.value}'")


@router.get("/stats", response_model=CompanyStatsResponse)
async def get_company_stats(company: dict = Depends(get_current_company)):
    """Get hiring statistics from SQL view (vw_company_hiring_stats)."""
    results = execute_raw_sql("""
        SELECT * FROM vw_company_hiring_stats WHERE company_id = :id
    """, {"id": company["company_id"]})
    
    if not results:
        raise HTTPException(status_code=404, detail="Stats not found")
    
    r = results[0]
    return CompanyStatsResponse(
        company_id=r["company_id"], company_name=r["company_name"], industry=r["industry"],
        total_jobs_posted=r["total_jobs_posted"], active_jobs=r["active_jobs"],
        total_applications_received=r["total_applications_received"],
        candidates_shortlisted=r["candidates_shortlisted"], offers_extended=r["offers_extended"],
        hires_completed=r["hires_completed"],
        offer_rate_percentage=float(r["offer_rate_percentage"]) if r["offer_rate_percentage"] else 0
    )