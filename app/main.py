from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import create_public_tables
from app.models import tenant  # noqa: F401
from app.models import user    # noqa: F401
from app.models import document  # noqa: F401
from app.api.routes import api_router
from app.storage.s3_client import create_bucket_if_not_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting SaaS Backend...")
    await create_public_tables()
    print("✅ Public schema tables ready")
    create_bucket_if_not_exists()
    print("✅ S3 bucket ready")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    description="Scalable B2B SaaS backend with schema-per-tenant isolation",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "saas-backend-multitenant",
        "version": "1.0.0"
    }