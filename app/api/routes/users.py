import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_tenant_db
from app.api.middleware.rbac import require_permission, get_current_user, TokenData
from app.schemas.user import UserResponse, UserRole
from app.services.user_service import list_users, invite_user, update_user_role, delete_user
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/users", tags=["Users"])


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: UserRole


class UpdateRoleRequest(BaseModel):
    role: UserRole


@router.get("/", response_model=list[UserResponse])
async def get_users(
    current_user: TokenData = Depends(require_permission("users:list"))
):
    async for db in get_tenant_db(current_user.tenant_id):
        return await list_users(current_user.tenant_id, db)


@router.post("/invite", response_model=UserResponse, status_code=201)
async def invite_new_user(
    payload: InviteUserRequest,
    current_user: TokenData = Depends(require_permission("users:invite"))
):
    async for db in get_tenant_db(current_user.tenant_id):
        return await invite_user(
            email=payload.email,
            role=payload.role.value,
            invited_by=current_user.user_id,
            tenant_id=current_user.tenant_id,
            db=db
        )


@router.put("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    payload: UpdateRoleRequest,
    current_user: TokenData = Depends(require_permission("users:update_role"))
):
    async for db in get_tenant_db(current_user.tenant_id):
        return await update_user_role(
            user_id=str(user_id),
            new_role=payload.role.value,
            tenant_id=current_user.tenant_id,
            db=db
        )


@router.delete("/{user_id}")
async def remove_user(
    user_id: uuid.UUID,
    current_user: TokenData = Depends(require_permission("users:delete"))
):
    async for db in get_tenant_db(current_user.tenant_id):
        return await delete_user(str(user_id), current_user.tenant_id, db)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: TokenData = Depends(get_current_user)
):
    async for db in get_tenant_db(current_user.tenant_id):
        from sqlalchemy import select
        from app.models.user import User
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(current_user.user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")
        return user