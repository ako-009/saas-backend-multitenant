from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse, TenantRegistrationResponse
from app.services.tenant_service import create_tenant
from app.models.tenant import Tenant
from sqlalchemy import select
import uuid

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("/register", response_model=TenantRegistrationResponse, status_code=201)
async def register_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new tenant.
    
    This endpoint:
    1. Creates a tenant record in public.tenants
    2. Provisions a new PostgreSQL schema (tenant_{slug})
    3. Creates users, documents, settings tables in that schema
    
    All of this happens in a single atomic transaction.
    """
    tenant = await create_tenant(
        name=payload.name,
        admin_email=payload.admin_email,
        session=db
    )

    return TenantRegistrationResponse(
        message="Tenant registered successfully",
        tenant=TenantResponse.model_validate(tenant),
        schema_created=f"tenant_{tenant.slug}"
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant details by ID.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant