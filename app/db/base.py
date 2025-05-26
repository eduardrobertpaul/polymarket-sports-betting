from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from app.config import get_settings
from typing import AsyncGenerator

# Get settings instance
settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,  # Set to True to log all SQL queries (useful for debugging)
    future=True,  # Use SQLAlchemy 2.0 features
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Don't expire objects after commit
    class_=AsyncSession,  # Use AsyncSession class
)

# Create declarative base for models
Base = declarative_base()


# Dependency for getting a database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session.

    Usage (with FastAPI):
    @app.get("/items/")
    async def read_items(db: AsyncSession = Depends(get_db)):
        # Use db here
        pass
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
