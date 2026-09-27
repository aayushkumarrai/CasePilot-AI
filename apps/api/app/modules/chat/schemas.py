from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GENERAL_GUIDANCE_PREFIX = "General guidance — not based on case documents."


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatSendRequest(StrictModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]

    @field_validator("message")
    @classmethod
    def message_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chat message cannot be empty")
        return value.strip()


class ChatCitationDraft(StrictModel):
    passage_id: UUID
    quote: Annotated[str, Field(min_length=1, max_length=1000)]


class ChatResult(StrictModel):
    response_type: Literal["evidence", "general_guidance"]
    content: Annotated[str, Field(min_length=1, max_length=10000)]
    citations: Annotated[list[ChatCitationDraft], Field(max_length=5)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_response_type(self) -> "ChatResult":
        if self.response_type == "evidence" and not self.citations:
            raise ValueError("Evidence responses require at least one citation")
        if self.response_type == "general_guidance":
            if self.citations:
                raise ValueError("General guidance cannot include citations")
            if not self.content.startswith(GENERAL_GUIDANCE_PREFIX):
                raise ValueError("General guidance label is required")
        return self


class ChatHistoryItem(StrictModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=10000)]


class ChatPrompt(StrictModel):
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    uploaded_evidence: Annotated[str, Field(max_length=60000)] = ""
    lawyer_reviewed_details: Annotated[str, Field(max_length=20000)] = ""
    history: Annotated[list[ChatHistoryItem], Field(max_length=20)] = Field(default_factory=list)


class ChatCitationResponse(BaseModel):
    document_id: UUID
    document_name: str
    passage_id: UUID
    passage_label: str
    page_number: int | None = None
    quote: str


class ChatMessageResponse(BaseModel):
    id: UUID
    exchange_id: UUID
    role: Literal["user", "assistant"]
    content: str
    response_type: Literal["evidence", "general_guidance"] | None = None
    citations: list[ChatCitationResponse] = Field(default_factory=list)
    created_at: datetime


class ChatExchangeResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse

