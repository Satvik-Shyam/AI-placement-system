"""
Recommendation Routes

GET /recommendations - Get AI recommendations for student
POST /recommendations/generate - Generate new recommendations
PUT /recommendations/{job_id}/viewed - Mark as viewed
GET /recommendations/skills-analysis - Get skill demand from SQL view
GET /recommendations/student-summary - Get student summary from SQL view
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List

from app.db.postgres import execute_raw_sql
from app.core.auth import get_current_student
from app.services.matching_service import get_recommendation_service
from app.schemas.schemas import (
    RecommendationResponse, RecommendationListResponse, SkillDemandResponse,
    StudentSummaryResponse, MessageResponse
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=RecommendationListResponse)
async def get_recommendations(
    include_applied: bool = Query(False, description="Include jobs already applied to"),
    student: dict = Depends(get_current_student)
):
    """
    Get AI-generated job recommendations.
    
    Recommendations are based on:
    - Skills match (from parsed resume)
    - Experience match
    - Semantic similarity (embeddings)
    
    Uses PostgreSQL ai_recommendations table.
    """
    service = get_recommendation_service()
    results = service.get_student_recommendations(
        student_id=student["student_id"],
        include_applied=include_applied
    )
    
    recs = [
        RecommendationResponse(
            recommendation_id=r["recommendation_id"],
            job_id=r["job_id"],
            job_title=r["job_title"],
            company_name=r["company_name"],
            match_score=float(r["match_score"]),
            skill_match_pct=float(r["skill_match_pct"]),
            experience_match=r["experience_match"],
            recommendation_reason=r["recommendation_reason"],
            is_viewed=r["is_viewed"],
            is_applied=r["is_applied"],
            created_at=r["created_at"]
        ) for r in results
    ]
    
    return RecommendationListResponse(recommendations=recs, total=len(recs))


@router.post("/generate", response_model=MessageResponse)
async def generate_recommendations(
    top_n: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.3, ge=0, le=1),
    student: dict = Depends(get_current_student)
):
    """
    Generate new AI recommendations.
    
    Process:
    1. Get student embedding (from parsed resume)
    2. Compare with all open job embeddings
    3. Calculate match scores
    4. Store top recommendations in PostgreSQL
    
    Requires: Resume must be uploaded first.
    """
    # Check resume exists
    results = execute_raw_sql(
        "SELECT resume_mongo_id FROM students WHERE student_id = :id",
        {"id": student["student_id"]}
    )
    if not results or not results[0]["resume_mongo_id"]:
        raise HTTPException(status_code=400, detail="Upload resume first to get recommendations")
    
    service = get_recommendation_service()
    
    recommendations = service.generate_recommendations(
        student_id=student["student_id"],
        top_n=top_n,
        min_score=min_score
    )
    
    if not recommendations:
        return MessageResponse(message="No matching jobs found. Try lowering minimum score.", success=True)
    
    stored = service.store_recommendations(student["student_id"], recommendations)
    
    return MessageResponse(message=f"Generated {stored} job recommendations", success=True)


@router.put("/{job_id}/viewed", response_model=MessageResponse)
async def mark_viewed(job_id: int, student: dict = Depends(get_current_student)):
    """Mark recommendation as viewed."""
    service = get_recommendation_service()
    success = service.mark_recommendation_viewed(student["student_id"], job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return MessageResponse(message="Marked as viewed")


@router.get("/skills-analysis", response_model=List[SkillDemandResponse])
async def skills_analysis(
    limit: int = Query(20, ge=1, le=100),
    category: str = Query(None, description="Filter by skill category")
):
    """
    Get skill demand analysis from SQL view (vw_skill_demand_analysis).
    
    Shows supply/demand ratio and market status for each skill.
    Useful for students to understand which skills are in demand.
    """
    sql = """
        SELECT skill_id, skill_name, skill_category, students_with_skill,
               total_job_demand, supply_demand_ratio, market_status
        FROM vw_skill_demand_analysis
        WHERE students_with_skill > 0 OR total_job_demand > 0
    """
    params = {}
    
    if category:
        sql += " AND skill_category = :category"
        params["category"] = category
    
    sql += f" ORDER BY total_job_demand DESC NULLS LAST LIMIT {limit}"
    results = execute_raw_sql(sql, params)
    
    return [
        SkillDemandResponse(
            skill_id=r["skill_id"],
            skill_name=r["skill_name"],
            skill_category=r["skill_category"],
            students_with_skill=r["students_with_skill"],
            total_job_demand=r["total_job_demand"],
            supply_demand_ratio=float(r["supply_demand_ratio"]) if r["supply_demand_ratio"] else None,
            market_status=r["market_status"]
        ) for r in results
    ]


@router.get("/student-summary", response_model=StudentSummaryResponse)
async def student_summary(student: dict = Depends(get_current_student)):
    """
    Get student summary from SQL view (vw_student_application_summary).
    
    Shows comprehensive profile stats including skills, applications, and AI metrics.
    """
    results = execute_raw_sql(
        "SELECT * FROM vw_student_application_summary WHERE student_id = :id",
        {"id": student["student_id"]}
    )
    
    if not results:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    r = results[0]
    return StudentSummaryResponse(
        student_id=r["student_id"],
        full_name=r["full_name"],
        email=r["email"],
        university=r["university"],
        cgpa=float(r["cgpa"]) if r["cgpa"] else None,
        total_skills=r["total_skills"],
        total_applications=r["total_applications"],
        shortlisted_count=r["shortlisted_count"],
        offers_received=r["offers_received"],
        active_recommendations=r["active_recommendations"],
        avg_match_score=float(r["avg_match_score"]) if r["avg_match_score"] else None,
        profile_status=r["profile_status"]
    )