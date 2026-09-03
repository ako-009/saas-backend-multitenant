import uuid
from fastapi import APIRouter, Depends
from app.core.database import get_tenant_db
from app.api.middleware.rbac import require_permission, TokenData
from app.schemas.document import (
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentConfirmRequest, DocumentResponse
)
from app.services.document_service import (
    generate_upload_url, confirm_upload,
    list_documents, delete_document
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload-url", response_model=DocumentUploadResponse)
async def get_upload_url(
    payload: DocumentUploadRequest,
    current_user: TokenData = Depends(require_permission("documents:upload"))
):
    """
    Step 1 of 2: Get a pre-signed S3 URL.
    Client uses this URL to upload directly to S3.
    API server never touches the file.
    """
    return await generate_upload_url(
        tenant_slug=current_user.tenant_id,
        user_id=current_user.user_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type
    )


@router.post("/confirm", response_model=DocumentResponse, status_code=201)
async def confirm_document_upload(
    payload: DocumentConfirmRequest,
    current_user: TokenData = Depends(require_permission("documents:upload"))
):
    """
    Step 2 of 2: After uploading to S3, save document metadata to DB.
    """
    async for db in get_tenant_db(current_user.tenant_id):
        return await confirm_upload(
            s3_key=payload.s3_key,
            file_name=payload.file_name,
            user_id=current_user.user_id,
            file_size=payload.file_size or 0,
            mime_type=payload.mime_type or "application/octet-stream",
            db=db
        )


@router.get("/", response_model=list[DocumentResponse])
async def get_documents(
    current_user: TokenData = Depends(require_permission("documents:list"))
):
    """List all documents for this tenant."""
    async for db in get_tenant_db(current_user.tenant_id):
        return await list_documents(db)


@router.delete("/{document_id}")
async def remove_document(
    document_id: uuid.UUID,
    current_user: TokenData = Depends(require_permission("documents:delete"))
):
    """Delete a document. Admin only."""
    async for db in get_tenant_db(current_user.tenant_id):
        return await delete_document(str(document_id), db)