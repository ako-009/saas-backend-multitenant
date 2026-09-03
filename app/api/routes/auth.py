from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db, get_tenant_db
from app.core.security import create_access_token
from app.schemas.user import UserRegister, UserLogin, TokenResponse
from app.services.auth_service import register_tenant_admin, login_user
from app.models.tenant import Tenant

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_tenant_or_404(tenant_slug: str, db: AsyncSession) -> Tenant:
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not found"
        )
    return tenant


@router.post("/register/{tenant_slug}", response_model=TokenResponse, status_code=201)
async def register(
    tenant_slug: str,
    payload: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    await get_tenant_or_404(tenant_slug, db)

    async for tenant_db in get_tenant_db(tenant_slug):
        user = await register_tenant_admin(
            email=payload.email,
            password=payload.password,
            tenant_slug=tenant_slug,
            db=tenant_db
        )
        token = create_access_token(
            user_id=str(user.id),
            tenant_id=tenant_slug,
            role=user.role
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user,
            tenant_id=tenant_slug
        )


@router.post("/login/{tenant_slug}", response_model=TokenResponse)
async def login(
    tenant_slug: str,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    await get_tenant_or_404(tenant_slug, db)

    async for tenant_db in get_tenant_db(tenant_slug):
        result = await login_user(
            email=payload.email,
            password=payload.password,
            tenant_slug=tenant_slug,
            db=tenant_db
        )
        return TokenResponse(**result)