import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.core.security import hash_password
from app.services.cache_service import cache


async def list_users(tenant_id: str, db: AsyncSession) -> list[User]:
    """
    List all users — with Redis cache-aside.
    
    Flow:
    1. Check Redis for cached user list
    2. Cache HIT → return immediately (no DB query)
    3. Cache MISS → query DB → store in Redis → return
    
    TTL: 60 seconds — user lists are read-heavy, change rarely
    """
    # Step 1: Check cache
    cached = await cache.get(tenant_id, "users")
    if cached:
        # Return cached data as User-like objects
        # We reconstruct from dict since Redis stores JSON
        return [_dict_to_user(u) for u in cached]

    # Step 2: Cache miss — query DB
    result = await db.execute(select(User))
    users = result.scalars().all()

    # Step 3: Store in cache
    users_data = [_user_to_dict(u) for u in users]
    await cache.set(tenant_id, "users", users_data, ttl=60)

    return users


async def invite_user(
    email: str,
    role: str,
    invited_by: str,
    tenant_id: str,
    db: AsyncSession
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists in this tenant"
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("TempPass@123"),
        role=role,
        is_active=True,
        invited_by=uuid.UUID(invited_by)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Invalidate cache — user list changed
    await cache.delete(tenant_id, "users")

    return user


async def update_user_role(
    user_id: str,
    new_role: str,
    tenant_id: str,
    db: AsyncSession
) -> User:
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    await db.commit()
    await db.refresh(user)

    # Invalidate cache — roles changed
    await cache.delete(tenant_id, "users")

    return user


async def delete_user(user_id: str, tenant_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()

    # Invalidate cache
    await cache.delete(tenant_id, "users")

    return {"message": f"User {user_id} deactivated successfully"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _user_to_dict(user: User) -> dict:
    """Convert User model to JSON-serializable dict for Redis."""
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "invited_by": str(user.invited_by) if user.invited_by else None,
        "hashed_password": user.hashed_password
    }


def _dict_to_user(data: dict) -> User:
    """Reconstruct User object from cached dict."""
    from datetime import datetime
    user = User()
    user.id = uuid.UUID(data["id"])
    user.email = data["email"]
    user.role = data["role"]
    user.is_active = data["is_active"]
    user.hashed_password = data.get("hashed_password", "")
    user.created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
    user.invited_by = uuid.UUID(data["invited_by"]) if data.get("invited_by") else None
    return user