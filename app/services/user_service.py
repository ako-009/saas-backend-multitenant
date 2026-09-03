import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.core.security import hash_password


async def list_users(db: AsyncSession) -> list[User]:
    """List all users in the current tenant schema."""
    result = await db.execute(select(User))
    return result.scalars().all()


async def invite_user(
    email: str,
    role: str,
    invited_by: str,
    db: AsyncSession
) -> User:
    """
    Invite a new user to this tenant.
    Creates user with a temporary password.
    In production, you'd send an email with a reset link.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists in this tenant"
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("TempPass@123"),  # user must reset
        role=role,
        is_active=True,
        invited_by=uuid.UUID(invited_by)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(
    user_id: str,
    new_role: str,
    db: AsyncSession
) -> User:
    """Update a user's role. Only admins can do this."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user_id: str, db: AsyncSession) -> dict:
    """Soft delete — deactivate user instead of removing from DB."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    return {"message": f"User {user_id} deactivated successfully"}