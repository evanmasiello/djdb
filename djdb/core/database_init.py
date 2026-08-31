"""Database initialization and management."""

import logging
from pathlib import Path
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from djdb.core.config import settings
from djdb.core.database import Base

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Get SQLite database URL.
    
    Returns:
        SQLite connection URL
    """
    return f"sqlite:///{settings.db_path}"


def create_database_engine() -> Engine:
    """
    Create SQLAlchemy database engine.
    
    Returns:
        SQLAlchemy Engine configured for SQLite
    """
    url = get_database_url()
    
    # Use StaticPool to avoid threading issues with SQLite
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.debug,
    )
    
    return engine


def initialize_database() -> Engine:
    """
    Initialize database and create tables.
    
    Returns:
        SQLAlchemy Engine
    """
    logger.info(f"Initializing database at {settings.db_path}")
    
    # Create engine
    engine = create_database_engine()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    logger.info("Database initialized successfully")
    
    return engine


def get_session_factory(engine: Engine):
    """
    Create a session factory.
    
    Args:
        engine: SQLAlchemy Engine
        
    Returns:
        Session factory
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine() -> Engine:
    """
    Get or create the global database engine.
    
    Returns:
        SQLAlchemy Engine
    """
    global _engine
    if _engine is None:
        _engine = initialize_database()
    return _engine


def get_session() -> Session:
    """
    Get a new database session.
    
    Yields:
        SQLAlchemy Session
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = get_session_factory(engine)
    
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
