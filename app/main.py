from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import create_public_tables

# This import is REQUIRED — it registers the Tenant model with SQLAlchemy
# Without this, create_all() doesn't know the tenants table should exist
from app.models import tenant  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting SaaS Backend...")
    await create_public_tables()
    print("✅ Public schema tables ready")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    description="Scalable B2B SaaS backend with schema-per-tenant isolation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "saas-backend-multitenant",
        "version": "1.0.0"
    }