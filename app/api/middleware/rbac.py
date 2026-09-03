from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.security import decode_access_token
from functools import wraps

# HTTP Bearer token extractor
# Reads the Authorization: Bearer <token> header
security = HTTPBearer()

# ─── Permission Matrix ────────────────────────────────────────────────────────
# This is the single source of truth for all permissions.
# To give a role a new permission, add it here. Nowhere else.
PERMISSIONS = {
    "admin": [
        "users:list", "users:invite", "users:delete", "users:update_role",
        "documents:upload", "documents:delete", "documents:list",
        "settings:read", "settings:update",
        "tenant:billing", "tenant:delete"
    ],
    "manager": [
        "documents:upload", "documents:list",
        "users:list",
        "settings:read"
    ],
    "user": [
        "documents:list",
        "profile:read", "profile:update"
    ]
}


# ─── Token Context ─────────────────────────────────────────────────────────────
class TokenData:
    """
    Holds the decoded JWT claims for the current request.
    Passed around as the 'current user' context.
    """
    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


# ─── Core Dependency ──────────────────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    FastAPI dependency — decodes and validates JWT on every protected request.
    
    HOW IT WORKS:
    1. FastAPI reads Authorization: Bearer <token> header
    2. We decode the token using our secret key
    3. We extract user_id, tenant_id, role from the payload
    4. We return a TokenData object the route handler can use
    
    If the token is missing, invalid, or expired → 401 Unauthorized
    
    INTERVIEW POINT:
    "We use FastAPI's dependency injection for auth. Any route that 
    declares `current_user: TokenData = Depends(get_current_user)` 
    is automatically protected. No decorator needed — just add the 
    dependency parameter."
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)

        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        role: str = payload.get("role")

        if not user_id or not tenant_id or not role:
            raise credentials_exception

        return TokenData(user_id=user_id, tenant_id=tenant_id, role=role)

    except JWTError:
        raise credentials_exception


# ─── Permission Checker ───────────────────────────────────────────────────────
def require_permission(permission: str):
    """
    Returns a FastAPI dependency that checks if the current user's role
    has the required permission.
    
    USAGE:
        @router.get("/users/")
        async def list_users(
            current_user: TokenData = Depends(require_permission("users:list"))
        ):
            ...
    
    HOW IT WORKS:
    require_permission("users:list") returns a dependency function.
    That function first calls get_current_user (gets the token),
    then checks if the role has the permission.
    If not → 403 Forbidden.
    
    INTERVIEW POINT:
    "require_permission is a dependency factory — it returns a dependency
    function that's parameterized with the required permission string.
    This pattern lets us declare permissions declaratively at the route
    level, making it immediately clear what each endpoint requires."
    """
    async def permission_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        role_permissions = PERMISSIONS.get(current_user.role, [])

        if permission not in role_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: '{permission}', "
                       f"Your role '{current_user.role}' does not have this permission."
            )

        return current_user

    return permission_checker