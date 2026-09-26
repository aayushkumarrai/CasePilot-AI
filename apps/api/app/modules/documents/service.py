from __future__ import annotations

import re
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, status

from app.core.config import Settings
from app.core.dependencies import CurrentUser
from app.core.errors import conflict, not_found, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway
from app.modules.cases.repository import CaseRepository

from .parser import DocumentExtractionError, extract_passages
from .repository import DocumentRepository
from .schemas import (
    MAX_DOCUMENTS_PER_CASE,
    SIGNED_URL_EXPIRES_SECONDS,
    DocumentDetailResponse,
    DocumentResponse,
    RegisterDocumentRequest,
    UploadUrlRequest,
    UploadUrlResponse,
    supported_type,
)

BUCKET = "case-documents"
UNSUPPORTED_MESSAGE = "Unsupported file type. Supported formats are PDF, DOCX, and TXT."


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


async def _active_case(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> dict:
    return await CaseRepository(gateway, user).get(case_id)


async def _within_limit(repository: DocumentRepository, case_id: UUID) -> None:
    if len(await repository.list(case_id)) >= MAX_DOCUMENTS_PER_CASE:
        raise conflict("A case can contain at most 50 documents")


def _owned_storage_path(user: CurrentUser, case_id: UUID, storage_path: str) -> bool:
    return storage_path.startswith(f"{user.id}/{case_id}/") and len(storage_path.split("/")) >= 3


def _safe_storage_file_name(file_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", file_name).strip("._")
    return sanitized or "document"


async def create_upload_url(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID, payload: UploadUrlRequest) -> UploadUrlResponse:
    await _active_case(gateway, user, case_id)
    if not supported_type(payload.file_name, payload.content_type):
        raise _unprocessable(UNSUPPORTED_MESSAGE)
    repository = DocumentRepository(gateway, user)
    await _within_limit(repository, case_id)
    storage_path = f"{user.id}/{case_id}/{uuid4()}-{_safe_storage_file_name(payload.file_name)}"
    try:
        upload_url = await gateway.create_signed_upload_url(BUCKET, storage_path, SIGNED_URL_EXPIRES_SECONDS)
    except SupabaseError as exc:
        raise unavailable("Private Storage is unavailable") from exc
    return UploadUrlResponse(storage_path=storage_path, upload_url=upload_url)


async def register_document(
    gateway: SupabaseGateway,
    user: CurrentUser,
    case_id: UUID,
    payload: RegisterDocumentRequest,
    background_tasks: BackgroundTasks,
    settings: Settings,
) -> DocumentResponse:
    await _active_case(gateway, user, case_id)
    repository = DocumentRepository(gateway, user)
    await _within_limit(repository, case_id)
    is_supported = supported_type(payload.file_name, payload.content_type)
    storage_path = payload.storage_path
    if is_supported:
        if not storage_path:
            raise _unprocessable("storage_path is required for supported documents")
        if not _owned_storage_path(user, case_id, storage_path):
            raise _unprocessable("storage_path does not belong to this case")
        try:
            if not await gateway.object_exists(BUCKET, storage_path):
                raise _unprocessable("Uploaded file was not found in private storage")
        except SupabaseError as exc:
            raise unavailable("Private Storage is unavailable") from exc
        document = await repository.mutate(
            "register_document_with_activity",
            {"p_case_id": str(case_id), "p_file_name": payload.file_name, "p_content_type": payload.content_type,
             "p_size_bytes": payload.size_bytes, "p_storage_path": storage_path, "p_status": "uploaded", "p_error_message": None},
        )
        background_tasks.add_task(process_document, str(document["id"]), user.access_token, settings)
    else:
        if storage_path is not None:
            raise _unprocessable("storage_path must be null for unsupported documents")
        document = await repository.mutate(
            "register_document_with_activity",
            {"p_case_id": str(case_id), "p_file_name": payload.file_name, "p_content_type": payload.content_type,
             "p_size_bytes": payload.size_bytes, "p_storage_path": None, "p_status": "unsupported", "p_error_message": UNSUPPORTED_MESSAGE},
        )
    return DocumentResponse.model_validate(document)


async def list_documents(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[DocumentResponse]:
    await _active_case(gateway, user, case_id)
    return [DocumentResponse.model_validate(row) for row in await DocumentRepository(gateway, user).list(case_id)]


async def get_document(gateway: SupabaseGateway, user: CurrentUser, document_id: UUID) -> DocumentDetailResponse:
    repository = DocumentRepository(gateway, user)
    document = await repository.get(document_id)
    await _active_case(gateway, user, UUID(str(document["case_id"])))
    passages = await repository.passages(document_id) if document["status"] == "ready" and document["content_type"] != "application/pdf" else []
    read_url = None
    if document["status"] == "ready" and document["content_type"] in {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
        try:
            read_url = await gateway.create_signed_read_url(BUCKET, document["storage_path"], SIGNED_URL_EXPIRES_SECONDS)
        except SupabaseError as exc:
            raise unavailable("Private Storage is unavailable") from exc
    return DocumentDetailResponse.model_validate({**document, "passages": passages, "read_url": read_url})


async def retry_document(
    gateway: SupabaseGateway, user: CurrentUser, document_id: UUID, background_tasks: BackgroundTasks, settings: Settings
) -> DocumentResponse:
    document = await DocumentRepository(gateway, user).get(document_id)
    await _active_case(gateway, user, UUID(str(document["case_id"])))
    if document["status"] != "failed":
        raise conflict("Only failed supported documents can be retried")
    started = await DocumentRepository(gateway, user).mutate(
        "start_document_processing_with_activity",
        {"p_document_id": str(document_id), "p_action": "document_retry_requested"},
    )
    background_tasks.add_task(process_document, str(document_id), user.access_token, settings, True)
    return DocumentResponse.model_validate(started)


async def process_document(
    document_id: str, access_token: str, settings: Settings, already_processing: bool = False
) -> None:
    gateway = SupabaseGateway(settings.supabase_url or "", settings.supabase_anon_key or "", access_token)
    try:
        if already_processing:
            document = await gateway.select("documents", {"select": "*", "id": f"eq.{document_id}"}, single=True)
            if not document or document["status"] != "processing":
                return
        else:
            started = await gateway.rpc("start_document_processing_with_activity", {"p_document_id": document_id, "p_action": "document_processing_started"})
            if not started:
                return
            document = started[0] if isinstance(started, list) else started
        data = await gateway.download_object(BUCKET, document["storage_path"])
        passages = extract_passages(data, document["content_type"])
        await gateway.rpc(
            "complete_document_processing_with_activity",
            {"p_document_id": document_id, "p_passages": [passage.__dict__ for passage in passages]},
        )
    except DocumentExtractionError as exc:
        await _mark_failed(gateway, document_id, str(exc))
    except Exception:
        await _mark_failed(gateway, document_id, "The document could not be processed. Please retry the upload.")
    finally:
        await gateway.close()


async def _mark_failed(gateway: SupabaseGateway, document_id: str, message: str) -> None:
    try:
        await gateway.rpc("fail_document_processing_with_activity", {"p_document_id": document_id, "p_error_message": message})
    except SupabaseError:
        return
