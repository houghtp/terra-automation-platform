"""
Database configuration and session management.
"""
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


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


# Import all models for relationship resolution
import app.features.administration.tenants.db_models
import app.features.administration.users.models
import app.features.administration.tenants.models
import app.features.administration.secrets.models
import app.features.administration.audit.models

# Create async engine with PostgreSQL-specific configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
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
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables."""
    # Import all models to ensure they're registered with the metadata
    from app.features.administration.secrets.models import TenantSecret
    from app.features.administration.audit.models import AuditLog

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
