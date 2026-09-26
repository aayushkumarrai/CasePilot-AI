from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.config import Settings, get_settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import DocumentDetailResponse, DocumentResponse, RegisterDocumentRequest, UploadUrlRequest, UploadUrlResponse
from .service import create_upload_url, get_document, list_documents, register_document, retry_document

router = APIRouter(tags=["documents"])


@router.post("/v1/cases/{case_id}/documents/upload-url", response_model=UploadUrlResponse)
async def upload_url_route(
    case_id: UUID, payload: UploadUrlRequest, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)
) -> UploadUrlResponse:
    return await create_upload_url(gateway, user, case_id, payload)


@router.post("/v1/cases/{case_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document_route(
    case_id: UUID, payload: RegisterDocumentRequest, background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway), settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    return await register_document(gateway, user, case_id, payload, background_tasks, settings)


@router.get("/v1/cases/{case_id}/documents", response_model=list[DocumentResponse])
async def list_documents_route(
    case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)
) -> list[DocumentResponse]:
    return await list_documents(gateway, user, case_id)


@router.get("/v1/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_route(
    document_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)
) -> DocumentDetailResponse:
    return await get_document(gateway, user, document_id)


@router.post("/v1/documents/{document_id}/retry", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_document_route(
    document_id: UUID, background_tasks: BackgroundTasks, user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway), settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    return await retry_document(gateway, user, document_id, background_tasks, settings)
