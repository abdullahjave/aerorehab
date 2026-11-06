"""Database configuration for AeroRehab.

SQLite database with SQLAlchemy ORM.
Database file: aerorehab.db (created automatically on first run)
"""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database file location (project root)
DB_PATH = Path(__file__).resolve().parent.parent / "aerorehab.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine (connects to database)
# check_same_thread=False allows FastAPI to use the database from different threads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Set to True to see all SQL queries in console (useful for debugging)
)

# Session factory (creates database sessions for read/write operations)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()


def get_db():
    """Dependency function for FastAPI endpoints.

    Creates a database session, yields it to the endpoint,
    then closes it automatically when the request is done.

    Usage in endpoints:
        def my_endpoint(db: Session = Depends(get_db)):
            # db is now available here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database: create all tables.

    Call this once when the FastAPI app starts.
    Safe to call multiple times (won't overwrite existing data).
    """
    Base.metadata.create_all(bind=engine)
