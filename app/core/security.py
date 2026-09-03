from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    bcrypt automatically salts — same password hashes differently each time.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    Used during login.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT token with tenant_id and role baked in.
    
    This is the key multi-tenant addition — standard JWTs only have 'sub'.
    We add tenant_id and role so every request carries full context.
    
    INTERVIEW POINT:
    "We embed tenant_id and role into the JWT payload so our middleware
    can resolve both tenant context and RBAC permissions with a single
    token decode — avoiding an extra database round trip per request."
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": user_id,           # subject — who this token belongs to
        "tenant_id": tenant_id,   # which tenant schema to use
        "role": role,             # admin, manager, or user
        "exp": expire,            # expiry time
        "iat": datetime.utcnow()  # issued at
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    Raises JWTError if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise