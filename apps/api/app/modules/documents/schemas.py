from __future__ import annotations

from datetime import datetime
from pathlib import PurePath
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

MAX_DOCUMENTS_PER_CASE = 50
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
SIGNED_URL_EXPIRES_SECONDS = 3600

SUPPORTED_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}
DocumentStatus = Literal["uploaded", "processing", "ready", "failed", "unsupported"]
FileName = Annotated[str, Field(min_length=1, max_length=255)]


def normalize_file_name(value: str) -> str:
    value = value.strip()
    if not value or PurePath(value).name != value or value in {".", ".."}:
        raise ValueError("file_name must be a plain file name")
    return value


def normalized_content_type(value: str) -> str:
    return value.strip().lower().split(";", 1)[0]


def supported_type(file_name: str, content_type: str) -> bool:
    extension = PurePath(file_name).suffix.lower()
    return SUPPORTED_CONTENT_TYPES.get(extension) == normalized_content_type(content_type)


class UploadUrlRequest(BaseModel):
    file_name: FileName
    content_type: Annotated[str, Field(min_length=1, max_length=255)]
    size_bytes: Annotated[int, Field(gt=0, le=MAX_FILE_SIZE_BYTES)]

    _normalize_file_name = field_validator("file_name")(normalize_file_name)
    _normalize_content_type = field_validator("content_type")(normalized_content_type)


class UploadUrlResponse(BaseModel):
    storage_path: str
    upload_url: str
    expires_in_seconds: int = SIGNED_URL_EXPIRES_SECONDS


class RegisterDocumentRequest(UploadUrlRequest):
    storage_path: str | None = Field(default=None, max_length=1024)


class DocumentPassageResponse(BaseModel):
    id: UUID
    sequence_number: int
    page_number: int | None = None
    passage_label: str
    content: str
    created_at: datetime


class DocumentResponse(BaseModel):
    id: UUID
    case_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    passages: list[DocumentPassageResponse] = Field(default_factory=list)
    read_url: str | None = None
