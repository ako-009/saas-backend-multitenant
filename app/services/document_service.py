import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.storage.s3_client import s3_client
from app.core.config import settings


async def generate_upload_url(
    tenant_slug: str,
    user_id: str,
    file_name: str,
    mime_type: str
) -> dict:
    """
    Generate a pre-signed S3 URL for direct browser upload.
    
    S3 KEY STRUCTURE: tenant_slug/user_id/uuid/filename
    Example: acme_corp/139ab52d.../a1b2c3.../report.pdf
    
    This gives us:
    - Per-tenant isolation (acme_corp/ prefix)
    - Per-user traceability
    - UUID prevents filename collisions
    
    INTERVIEW POINT:
    "The S3 key structure enforces logical isolation between tenants
    at the storage layer. Even though all tenants share one bucket,
    their files are namespaced under their tenant slug. Combined with
    IAM policies, this gives defense-in-depth."
    """
    s3_key = f"{tenant_slug}/{user_id}/{uuid.uuid4()}/{file_name}"

    presigned_url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": s3_key,
            "ContentType": mime_type,
        },
        ExpiresIn=900  # 15 minutes
    )

    return {
        "upload_url": presigned_url,
        "s3_key": s3_key,
        "expires_in": 900
    }


async def confirm_upload(
    s3_key: str,
    file_name: str,
    user_id: str,
    file_size: int,
    mime_type: str,
    db: AsyncSession
) -> Document:
    """
    After client uploads to S3, they call this endpoint to
    save the document metadata in the tenant's DB.
    
    Two-step flow:
    1. GET /documents/upload-url → get pre-signed URL
    2. Client uploads to S3
    3. POST /documents/confirm → save metadata
    """
    document = Document(
        id=uuid.uuid4(),
        uploaded_by=uuid.UUID(user_id),
        file_name=file_name,
        s3_key=s3_key,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession) -> list[Document]:
    """List all documents for the current tenant."""
    result = await db.execute(select(Document))
    return result.scalars().all()


async def delete_document(document_id: str, db: AsyncSession) -> dict:
    """Delete document metadata. Does not delete from S3 (add that in production)."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()

    if not document:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(document)
    await db.commit()
    return {"message": f"Document {document_id} deleted"}