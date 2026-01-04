"""
API Routes - Combines all route modules into single router.
"""

from fastapi import APIRouter

from app.api.routes.auth_routes import router as auth_router
from app.api.routes.student_routes import router as student_router
from app.api.routes.company_routes import router as company_router
from app.api.routes.job_routes import router as job_router
from app.api.routes.recommendation_routes import router as recommendation_router

# Main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(student_router)
api_router.include_router(company_router)
api_router.include_router(job_router)
api_router.include_router(recommendation_router)