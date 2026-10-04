"""
SmartFarm - Database Connection
SQLAlchemy engine, session factory, and base model.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


is_sqlite = settings.database_url.startswith("sqlite")
engine_kwargs = {
    "echo": settings.is_development,
    "pool_pre_ping": True,
}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables. Called at startup. Falls back to SQLite if primary DB is unavailable."""
    global engine, SessionLocal
    try:
        # Import models so SQLAlchemy registers them before create_all
        from backend import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database tables initialized successfully on {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'local db'}.")
    except Exception as e:
        logger.error(f"Primary database initialization failed: {e}")
        if not settings.database_url.startswith("sqlite"):
            logger.warning("Falling back to local SQLite database so SmartFarm can start...")
            try:
                engine = create_engine(
                    "sqlite:///./smartfarm.db",
                    connect_args={"check_same_thread": False},
                    pool_pre_ping=True,
                )
                SessionLocal.configure(bind=engine)
                from backend import models  # noqa: F401
                Base.metadata.create_all(bind=engine)
                logger.info("✅ Fallback SQLite database initialized successfully.")
                return
            except Exception as fe:
                logger.error(f"Fallback SQLite also failed: {fe}")
        raise
