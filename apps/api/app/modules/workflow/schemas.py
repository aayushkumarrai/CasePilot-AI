from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class FieldReviewRequest(BaseModel):
    action: Literal["confirm", "edit", "reject"]
    value: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_action(self) -> "FieldReviewRequest":
        if self.action == "edit" and not (self.value or "").strip():
            raise ValueError("A replacement value is required when editing a field")
        if self.action != "edit" and self.value is not None:
            raise ValueError("A replacement value is valid only when editing a field")
        return self


class PartyReviewRequest(BaseModel):
    action: Literal["confirm", "edit", "reject"]
    name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_action(self) -> "PartyReviewRequest":
        if self.action == "edit" and not ((self.name or "").strip() or (self.role or "").strip()):
            raise ValueError("A replacement name or role is required when editing a party")
        if self.action != "edit" and (self.name is not None or self.role is not None):
            raise ValueError("Replacement party details are valid only when editing a party")
        return self


class ManualTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def trim_required_text(self) -> "ManualTaskCreateRequest":
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.title or not self.description:
            raise ValueError("Task title and description are required")
        return self


class TaskUpdateRequest(BaseModel):
    status: Literal["approved", "rejected", "done"] | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_operation(self) -> "TaskUpdateRequest":
        text_change = self.title is not None or self.description is not None
        if self.status is not None and text_change:
            raise ValueError("Edit task text or change status in separate requests")
        if self.status is None and not text_change:
            raise ValueError("Provide a task edit or status change")
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("Task title cannot be empty")
        if self.description is not None:
            self.description = self.description.strip()
            if not self.description:
                raise ValueError("Task description cannot be empty")
        return self


class FieldReviewResponse(BaseModel):
    id: UUID
    field_key: str
    label: str
    suggested_value: str
    reviewed_value: str | None = None
    value: str
    status: Literal["pending", "confirmed", "rejected"]
    reviewed_at: datetime | None = None


class PartyReviewResponse(BaseModel):
    id: UUID
    suggested_name: str
    suggested_role: str
    reviewed_name: str | None = None
    reviewed_role: str | None = None
    name: str
    role: str
    status: Literal["pending", "confirmed", "rejected"]
    reviewed_at: datetime | None = None


class TaskMutationResponse(BaseModel):
    id: UUID
    case_id: UUID | None = None
    source: Literal["ai", "manual"]
    title: str
    description: str
    status: Literal["proposed", "approved", "done", "rejected"]
    updated_at: datetime
