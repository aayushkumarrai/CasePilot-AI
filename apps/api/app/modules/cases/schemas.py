from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

CaseIdentifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._/-]+$")]
CaseName = Annotated[str, Field(min_length=1, max_length=160)]


def normalize(value: str) -> str:
    return value.strip()


class CreateCaseRequest(BaseModel):
    case_id: CaseIdentifier
    case_name: CaseName

    _normalize_case_id = field_validator("case_id")(normalize)
    _normalize_case_name = field_validator("case_name")(normalize)


class UpdateCaseRequest(BaseModel):
    case_id: CaseIdentifier | None = None
    case_name: CaseName | None = None

    _normalize_case_id = field_validator("case_id")(normalize)
    _normalize_case_name = field_validator("case_name")(normalize)

    @model_validator(mode="after")
    def has_update(self) -> "UpdateCaseRequest":
        if self.case_id is None and self.case_name is None:
            raise ValueError("Provide case_id or case_name")
        return self


class CaseResponse(BaseModel):
    id: UUID
    case_id: str = Field(validation_alias="external_case_id")
    case_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
