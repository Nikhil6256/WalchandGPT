"""
Async SQLAlchemy engine, session factory, and database initialization.
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base

log = structlog.get_logger(__name__)

# Create the async engine
# NullPool is used in tests; for production AsyncAdaptedQueuePool is used by default
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Create all tables. In production, prefer Alembic migrations.
    This is kept here for development convenience.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables initialized")
