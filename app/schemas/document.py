import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class DocumentUploadRequest(BaseModel):
    file_name: str
    mime_type: Optional[str] = "application/octet-stream"


class DocumentUploadResponse(BaseModel):
    upload_url: str      # pre-signed S3 URL — client uploads directly here
    s3_key: str          # key to send back in confirm request
    expires_in: int      # seconds until URL expires (900 = 15 min)


class DocumentConfirmRequest(BaseModel):
    s3_key: str
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    s3_key: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}