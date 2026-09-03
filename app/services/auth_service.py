import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from fastapi import HTTPException, status
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User


async def register_tenant_admin(
    email: str,
    password: str,
    tenant_slug: str,
    db: AsyncSession
) -> User:
    """
    Register the first admin user for a tenant.
    Called right after tenant schema is provisioned.
    
    The db session must already have search_path set to tenant schema.
    """
    # Check if email already exists in this tenant
    result = await db.execute(
        select(User).where(User.email == email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant"
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_user(
    email: str,
    password: str,
    tenant_slug: str,
    db: AsyncSession
) -> dict:
    """
    Authenticate a user and return a JWT token.
    
    The db session must already have search_path set to tenant schema
    so we query the correct tenant's users table.
    """
    # Find user in this tenant's schema
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Create JWT with tenant_id and role embedded
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=tenant_slug,
        role=user.role
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
        "tenant_id": tenant_slug
    }