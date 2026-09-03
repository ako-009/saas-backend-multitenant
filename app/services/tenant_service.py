import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from fastapi import HTTPException, status
from app.models.tenant import Tenant


def slugify(name: str) -> str:
    """
    Convert tenant name to a valid PostgreSQL schema name.
    
    Rules:
    - Lowercase only
    - Only letters, numbers, underscores
    - No spaces or special characters
    
    Examples:
    "Acme Corp"    → "acme_corp"
    "Tech Co. 2"   → "tech_co_2"
    "My Company!"  → "my_company"
    """
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s]', '', slug)   # remove special chars
    slug = re.sub(r'\s+', '_', slug)            # spaces → underscores
    slug = re.sub(r'_+', '_', slug)             # multiple underscores → one
    slug = slug.strip('_')                      # remove leading/trailing underscores
    return slug


async def provision_tenant_schema(tenant_slug: str, session: AsyncSession):
    """
    Creates a complete PostgreSQL schema for a new tenant.
    
    This runs inside the SAME transaction as tenant creation.
    If anything fails, everything rolls back automatically.
    
    INTERVIEW POINT:
    "We use raw DDL statements inside a SQLAlchemy async session.
    The schema name is derived from the tenant slug, which is validated
    to only contain safe characters — preventing SQL injection in DDL."
    """
    schema_name = f"tenant_{tenant_slug}"

    # Step 1: Create the schema
    await session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    # Step 2: Create users table in tenant schema
    await session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS "{schema_name}".users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            invited_by UUID,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Step 3: Create documents table in tenant schema
    await session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS "{schema_name}".documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            uploaded_by UUID REFERENCES "{schema_name}".users(id),
            file_name VARCHAR(255) NOT NULL,
            s3_key VARCHAR(500) NOT NULL,
            file_size INTEGER,
            mime_type VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Step 4: Create settings table in tenant schema
    await session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS "{schema_name}".settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key VARCHAR(100) NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    return schema_name


async def create_tenant(name: str, admin_email: str, session: AsyncSession) -> Tenant:
    """
    Full tenant registration flow:
    1. Generate slug from name
    2. Check slug uniqueness
    3. Create tenant record in public schema
    4. Provision tenant schema with all tables
    5. Commit everything atomically
    """
    # Generate slug
    slug = slugify(name)

    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant name could not be converted to a valid slug"
        )

    # Check uniqueness — no two tenants can share a slug
    existing = await session.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{slug}' already exists"
        )

    # Create tenant record in public.tenants
    tenant = Tenant(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
        admin_email=admin_email,
        is_active=True,
    )
    session.add(tenant)

    # Flush to get the tenant ID assigned without committing yet
    await session.flush()

    # Provision the schema — still inside same transaction
    await provision_tenant_schema(slug, session)

    # Commit everything at once — atomic
    await session.commit()
    await session.refresh(tenant)

    return tenant