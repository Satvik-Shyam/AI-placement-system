"""
Pydantic Schemas - Request/Response Validation

All API request and response schemas in one file for simplicity.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class UserRole(str, Enum):
    student = "student"
    company = "company"
    admin = "admin"


class JobType(str, Enum):
    full_time = "full-time"
    part_time = "part-time"
    internship = "internship"
    contract = "contract"


class JobStatus(str, Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
    filled = "filled"


class ApplicationStatus(str, Enum):
    applied = "applied"
    under_review = "under_review"
    shortlisted = "shortlisted"
    interviewed = "interviewed"
    offered = "offered"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class CompanySize(str, Enum):
    startup = "startup"
    small = "small"
    medium = "medium"
    large = "large"
    enterprise = "enterprise"


class ProficiencyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


# ============================================================
# AUTH SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str

class UserResponse(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime


# ============================================================
# STUDENT SCHEMAS
# ============================================================

class StudentCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    university: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = Field(None, ge=2000, le=2100)
    cgpa: Optional[float] = Field(None, ge=0, le=10)

class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    university: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = Field(None, ge=2000, le=2100)
    cgpa: Optional[float] = Field(None, ge=0, le=10)

class StudentResponse(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    university: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    resume_uploaded: bool = False
    skills: List[str] = []
    created_at: datetime

class SkillAdd(BaseModel):
    skill_name: str
    proficiency_level: ProficiencyLevel = ProficiencyLevel.intermediate


# ============================================================
# COMPANY SCHEMAS
# ============================================================

class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    industry: Optional[str] = None
    company_size: Optional[CompanySize] = None
    website: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2100)

class CompanyUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    industry: Optional[str] = None
    company_size: Optional[CompanySize] = None
    website: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2100)

class CompanyResponse(BaseModel):
    company_id: int
    user_id: int
    company_name: str
    email: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None
    is_verified: bool = False
    created_at: datetime


# ============================================================
# JOB SCHEMAS
# ============================================================

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    job_type: JobType = JobType.full_time
    location: Optional[str] = None
    is_remote: bool = False
    min_experience: int = Field(0, ge=0)
    max_experience: Optional[int] = Field(None, ge=0)
    min_salary: Optional[float] = Field(None, ge=0)
    max_salary: Optional[float] = Field(None, ge=0)
    currency: str = "INR"
    openings: int = Field(1, ge=1)
    application_deadline: Optional[datetime] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[JobType] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    openings: Optional[int] = None
    application_deadline: Optional[datetime] = None
    status: Optional[JobStatus] = None

class JobResponse(BaseModel):
    job_id: int
    company_id: int
    company_name: str
    title: str
    description: Optional[str] = None
    job_type: str
    location: Optional[str] = None
    is_remote: bool
    min_experience: int
    max_experience: Optional[int] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    currency: str
    openings: int
    application_deadline: Optional[datetime] = None
    status: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    created_at: datetime

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# APPLICATION SCHEMAS
# ============================================================

class ApplicationCreate(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    application_id: int
    student_id: int
    student_name: str
    job_id: int
    job_title: str
    company_name: str
    status: str
    cover_letter: Optional[str] = None
    applied_at: datetime
    updated_at: datetime


# ============================================================
# RESUME SCHEMAS
# ============================================================

class ResumeUploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    extracted_skills: List[str] = []
    skills_synced: int = 0
    parsed_data: Optional[dict] = None


# ============================================================
# RECOMMENDATION SCHEMAS
# ============================================================

class RecommendationResponse(BaseModel):
    recommendation_id: int
    job_id: int
    job_title: str
    company_name: str
    match_score: float
    skill_match_pct: float
    experience_match: bool
    recommendation_reason: str
    is_viewed: bool
    is_applied: bool
    created_at: datetime

class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationResponse]
    total: int


# ============================================================
# ANALYTICS SCHEMAS (for Views)
# ============================================================

class SkillDemandResponse(BaseModel):
    skill_id: int
    skill_name: str
    skill_category: Optional[str] = None
    students_with_skill: int
    total_job_demand: int
    supply_demand_ratio: Optional[float] = None
    market_status: str

class StudentSummaryResponse(BaseModel):
    student_id: int
    full_name: str
    email: str
    university: Optional[str] = None
    cgpa: Optional[float] = None
    total_skills: int
    total_applications: int
    shortlisted_count: int
    offers_received: int
    active_recommendations: int
    avg_match_score: Optional[float] = None
    profile_status: str

class CompanyStatsResponse(BaseModel):
    company_id: int
    company_name: str
    industry: Optional[str] = None
    total_jobs_posted: int
    active_jobs: int
    total_applications_received: int
    candidates_shortlisted: int
    offers_extended: int
    hires_completed: int
    offer_rate_percentage: float


# ============================================================
# GENERIC SCHEMAS
# ============================================================

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    detail: str