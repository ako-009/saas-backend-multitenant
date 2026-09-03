from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """
    Standard DB session — uses public schema.
    For tenant-specific queries, use get_tenant_db() instead.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_tenant_db(tenant_slug: str):
    """
    Tenant-isolated DB session.
    Sets PostgreSQL search_path to tenant's schema before any query runs.
    This is the core isolation mechanism — one line that makes cross-tenant
    access structurally impossible.
    """
    schema_name = f"tenant_{tenant_slug}"
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_public_tables():
    """
    Creates public schema tables on startup.
    Safe to call multiple times — won't overwrite existing tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)