"""
Database configuration and session management.
"""
import os
import importlib
import structlog
from pathlib import Path
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = structlog.get_logger(__name__)

# --- Base class for all models ---
class Base(DeclarativeBase):
    """Base class for all models."""
    pass

# Database URL - PostgreSQL only
from .config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Ensure PostgreSQL URL format
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)


def _discover_and_import_models():
    """
    Dynamically discover and import all model files for relationship resolution.
    This replaces hard-coded imports and makes the system more maintainable.
    """
    # Get the app directory path
    app_dir = Path(__file__).parent.parent.parent  # Go up from core -> features -> app
    features_dir = app_dir / "features"

    models_imported = []

    if not features_dir.exists():
        logger.warning(f"Features directory not found at {features_dir}")
        return models_imported

    # Walk through all feature directories looking for models.py files
    # Exclude routes, templates, and other non-model directories
    excluded_dirs = {'routes', 'templates', 'static', 'tests', '__pycache__'}

    for feature_path in features_dir.rglob("*/"):
        if feature_path.is_dir():
            # Skip excluded directories (routes, templates, etc.)
            if any(excluded_dir in feature_path.parts for excluded_dir in excluded_dirs):
                continue

            models_file = feature_path / "models.py"
            db_models_file = feature_path / "db_models.py"

            # Try to import models.py
            if models_file.exists():
                try:
                    # Convert file path to module path
                    relative_path = models_file.relative_to(app_dir)
                    module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
                    module_name = f"app.{module_path}"

                    importlib.import_module(module_name)
                    models_imported.append(module_name)
                except ImportError as e:
                    logger.warning(f"Failed to import {module_name}: {e}")
                except Exception as e:
                    logger.error(f"Error importing {module_name}: {e}")

            # Try to import db_models.py (some features use this naming)
            if db_models_file.exists():
                try:
                    relative_path = db_models_file.relative_to(app_dir)
                    module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
                    module_name = f"app.{module_path}"

                    importlib.import_module(module_name)
                    models_imported.append(module_name)
                except ImportError as e:
                    logger.warning(f"Failed to import {module_name}: {e}")
                except Exception as e:
                    logger.error(f"Error importing {module_name}: {e}")

    logger.info(f"Dynamically imported {len(models_imported)} model modules: {models_imported}")
    return models_imported


# Discover and import all models for relationship resolution
_discover_and_import_models()

# Create async engine with PostgreSQL-specific configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Disable SQL logging for cleaner output
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Create async session maker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Dependency to get database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a dependency.

    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Function to get async session for direct use (not as dependency)
def get_async_session():
    """
    Get an async session for direct use in background tasks.

    Returns:
        async_sessionmaker: Session maker for creating sessions
    """
    return async_session


async def create_tables() -> None:
    """
    Create all tables.
    Models are now automatically discovered and imported by _discover_and_import_models().
    """
    # Create tables - all models should already be registered with metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")
