from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.core.config import get_settings

settings = get_settings()

# Create engine with connection pool
# pool_size=5: maintain 5 connections ready
# max_overflow=10: allow 10 extra connections under load
engine = create_engine(
    settings.postgres_url,
    pool_size=5,
    max_overflow=10,
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Usage:
        with get_db_session() as db:
            db.execute(text("SELECT * FROM users"))
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """
    Dependency for FastAPI route injection.
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_postgres_connection() -> bool:
    """
    Test if PostgreSQL is reachable.
    Returns True if connection successful, False otherwise.
    """
    try:
        with get_db_session() as db:
            result = db.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            return row[0] == 1
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return False


def execute_raw_sql(sql: str, params: dict = None) -> list:
    """
    Execute raw SQL and return results as list of dicts.
    This is useful for complex queries and views.
    """
    with get_db_session() as db:
        result = db.execute(text(sql), params or {})
        # Convert rows to dicts
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]