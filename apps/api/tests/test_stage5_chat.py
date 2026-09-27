from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.groq_client import GroqTemporaryError
from app.main import app
from app.modules.chat.schemas import ChatResult, ChatSendRequest
from app.modules.chat.service import (
    ChatGroundingError,
    MAX_EVIDENCE_CHARS,
    rank_passages,
    render_evidence,
    send_chat_message,
    validate_chat_result,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def passage(content: str, *, document_name: str = "evidence.txt", sequence: int = 1) -> dict:
    return {
        "id": str(uuid4()),
        "document_id": str(uuid4()),
        "document_name": document_name,
        "sequence_number": sequence,
        "page_number": None,
        "passage_label": f"Passage {sequence}",
        "content": content,
    }


def test_keyword_ranking_is_deterministic_and_uses_a_bounded_fallback() -> None:
    rows = [
        passage("Keys were handed over.", document_name="handover.txt", sequence=1),
        passage("Buyer Rao paid INR 500000.", document_name="receipt.txt", sequence=2),
        passage("Possession remains disputed.", sequence=3),
    ]
    ranked = rank_passages(rows, "What payment did Rao make?")
    assert ranked[0]["document_name"] == "receipt.txt"
    assert rank_passages(rows, "unrelated broad question") == rows
    assert rank_passages(rows * 5, "unrelated broad question") == (rows * 5)[:10]


def test_evidence_rendering_respects_the_character_limit_without_splitting_passages() -> None:
    first = passage("a" * (MAX_EVIDENCE_CHARS - 200))
    second = passage("b" * 500)
    rendered, selected = render_evidence([first, second])
    assert selected == [first]
    assert len(rendered) <= MAX_EVIDENCE_CHARS
    assert "b" * 20 not in rendered


def test_chat_grounding_accepts_normalized_quotes_and_rejects_missing_or_wrong_passages() -> None:
    stored = passage("Buyer Rao\npaid   INR 500000.")
    valid = ChatResult.model_validate({
        "response_type": "evidence",
        "content": "The uploaded material records a payment.",
        "citations": [{"passage_id": stored["id"], "quote": "Buyer Rao paid INR 500000."}],
    })
    assert validate_chat_result(valid, [stored]) == valid
    wrong_id = valid.model_copy(update={"citations": [valid.citations[0].model_copy(update={"passage_id": uuid4()})]})
    with pytest.raises(ChatGroundingError):
        validate_chat_result(wrong_id, [stored])
    wrong_quote = valid.model_copy(update={"citations": [valid.citations[0].model_copy(update={"quote": "Seller admitted possession."})]})
    with pytest.raises(ChatGroundingError):
        validate_chat_result(wrong_quote, [stored])


def test_general_guidance_contract_requires_label_and_no_citations() -> None:
    result = ChatResult.model_validate({
        "response_type": "general_guidance",
        "content": "General guidance — not based on case documents. This was not found in uploaded material; request the signed handover record.",
        "citations": [],
    })
    assert validate_chat_result(result, []) == result
    with pytest.raises(ValueError):
        ChatResult.model_validate({"response_type": "general_guidance", "content": "Request the record.", "citations": []})


class ChatGateway:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        self.case_id = str(uuid4())
        self.document_id = str(uuid4())
        self.passage_id = str(uuid4())
        self.messages: list[dict] = []
        self.citations: list[dict] = []
        self.rpc_calls = 0

    async def select(self, table: str, params: dict[str, str], *, single: bool = False):
        if table == "cases":
            rows = [{"id": self.case_id, "external_case_id": "CHAT-1", "case_name": "Rao v Mehta", "status": "review", "archived_at": None, "created_at": now(), "updated_at": now()}] if params.get("id") == f"eq.{self.case_id}" else []
        elif table == "documents":
            if params.get("status") == "eq.ready":
                rows = [{"id": self.document_id, "file_name": "receipt.txt", "created_at": now()}]
            else:
                rows = [{"id": self.document_id, "file_name": "receipt.txt"}]
        elif table == "document_passages":
            rows = [{"id": self.passage_id, "document_id": self.document_id, "sequence_number": 1, "page_number": None, "passage_label": "Passage 1", "content": "Buyer Rao paid INR 500000."}]
        elif table == "chat_messages":
            rows = list(reversed(self.messages))
        elif table == "chat_message_citations":
            rows = self.citations
        elif table == "analysis_runs":
            rows = []
        else:
            rows = []
        return rows[0] if single and rows else (None if single else rows)

    async def rpc(self, function: str, payload: dict):
        assert function == "save_chat_exchange_with_activity"
        self.rpc_calls += 1
        exchange_id, user_id, assistant_id = str(uuid4()), str(uuid4()), str(uuid4())
        self.messages.extend([
            {"id": user_id, "case_id": self.case_id, "exchange_id": exchange_id, "role": "user", "response_type": None, "content": payload["p_question"], "created_at": now()},
            {"id": assistant_id, "case_id": self.case_id, "exchange_id": exchange_id, "role": "assistant", "response_type": payload["p_response_type"], "content": payload["p_answer"], "created_at": now()},
        ])
        for item in payload["p_citations"]:
            self.citations.append({"id": str(uuid4()), "assistant_message_id": assistant_id, "passage_id": item["passage_id"], "quote": item["quote"], "created_at": now()})
        return [{"user_message_id": user_id, "assistant_message_id": assistant_id}]


def test_success_persists_one_atomic_exchange_and_provider_failure_persists_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    user = CurrentUser(id=uuid4(), email="owner@example.com", access_token="token")
    gateway = ChatGateway(user)
    result = ChatResult.model_validate({
        "response_type": "evidence",
        "content": "The evidence records a payment.",
        "citations": [{"passage_id": gateway.passage_id, "quote": "Buyer Rao paid INR 500000."}],
    })

    async def answer_success(self, prompt):
        assert "Buyer Rao paid" in prompt.uploaded_evidence
        return result

    async def close(self):
        return None

    monkeypatch.setattr("app.modules.chat.service.GroqClient.answer_case_question", answer_success)
    monkeypatch.setattr("app.modules.chat.service.GroqClient.close", close)
    async def success() -> None:
        response = await send_chat_message(
            gateway,
            user,
            UUID(gateway.case_id),
            ChatSendRequest(message="What payment is recorded?"),
            Settings(groq_api_key="key", groq_model="model"),
        )
        assert response.user_message.content == "What payment is recorded?"
        assert response.assistant_message.response_type == "evidence"
        assert response.assistant_message.citations[0].document_name == "receipt.txt"
        assert gateway.rpc_calls == 1
        assert len(gateway.messages) == 2

    asyncio.run(success())

    failed_gateway = ChatGateway(user)

    async def answer_failure(self, prompt):
        raise GroqTemporaryError()

    monkeypatch.setattr("app.modules.chat.service.GroqClient.answer_case_question", answer_failure)

    async def failure() -> None:
        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message(
                failed_gateway,
                user,
                UUID(failed_gateway.case_id),
                ChatSendRequest(message="What payment is recorded?"),
                Settings(groq_api_key="key", groq_model="model"),
            )
        assert exc_info.value.status_code == 503
        assert failed_gateway.rpc_calls == 0
        assert failed_gateway.messages == []

    asyncio.run(failure())


def test_public_chat_routes_auth_validation_and_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    assert client.get(f"/v1/cases/{uuid4()}/chat").status_code == 401

    user = CurrentUser(id=uuid4(), email="owner@example.com", access_token="token")
    gateway = ChatGateway(user)

    async def user_override() -> CurrentUser:
        return user

    async def gateway_override():
        yield gateway

    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    app.dependency_overrides[get_settings] = lambda: Settings(groq_api_key="key", groq_model="model")
    try:
        assert client.get(f"/v1/cases/{uuid4()}/chat", headers={"Authorization": "Bearer token"}).status_code == 404
        invalid = client.post(
            f"/v1/cases/{gateway.case_id}/chat",
            headers={"Authorization": "Bearer token"},
            json={"message": "   "},
        )
        assert invalid.status_code == 422
        assert "/v1/cases/{case_id}/chat" in app.openapi()["paths"]
    finally:
        app.dependency_overrides.clear()
