"""
Intelligent Placement Platform - Main Application

FastAPI backend with:
- PostgreSQL for structured data
- MongoDB for documents (resumes, JDs)
- DeepSeek AI for parsing
- JWT authentication
- React Frontend served from /frontend

Run: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routes import api_router
from app.db.mongodb import init_mongo_indexes
from app.core.config import get_settings

settings = get_settings()

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend", "public")

# Create FastAPI app
app = FastAPI(
    title="Intelligent Placement Platform",
    description="""
    A DBMS-dominant placement system with AI-assisted parsing.
    
    ## Features
    - **Authentication**: JWT-based auth for students and companies
    - **Students**: Profile management, resume upload with AI parsing
    - **Companies**: Job posting and application management
    - **Jobs**: Search, filter, and apply to jobs
    - **AI Recommendations**: Skill-based job matching
    - **Analytics**: SQL views for insights
    
    ## Databases
    - PostgreSQL: Structured data (users, students, companies, jobs, applications)
    - MongoDB: Documents (resumes, job descriptions, embeddings)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Serve static files (for any additional assets)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB indexes on startup."""
    try:
        init_mongo_indexes()
        print("✅ MongoDB indexes initialized")
    except Exception as e:
        print(f"⚠️ MongoDB index initialization failed: {e}")


# Serve React frontend for root path
@app.get("/", tags=["Frontend"])
async def serve_frontend():
    """Serve the React frontend."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "healthy", "app": "Intelligent Placement Platform", "message": "Frontend not found. API is running."}


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    from app.db.postgres import test_postgres_connection
    from app.db.mongodb import test_mongo_connection
    
    return {
        "status": "healthy",
        "postgres": "connected" if test_postgres_connection() else "disconnected",
        "mongodb": "connected" if test_mongo_connection() else "disconnected"
    }