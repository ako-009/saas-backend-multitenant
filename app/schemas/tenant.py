import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
import re


class TenantCreate(BaseModel):
    name: str
    admin_email: EmailStr

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Tenant name must be at least 2 characters')
        return v.strip()


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    admin_email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantRegistrationResponse(BaseModel):
    message: str
    tenant: TenantResponse
    schema_created: str  # e.g. "tenant_acme"