from __future__ import annotations

import re
import unicodedata
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.dependencies import CurrentUser
from app.core.errors import unavailable
from app.integrations.groq_client import GroqClient, GroqError
from app.integrations.supabase_gateway import SupabaseGateway

from .repository import ChatRepository
from .schemas import (
    ChatCitationResponse,
    ChatExchangeResponse,
    ChatHistoryItem,
    ChatMessageResponse,
    ChatPrompt,
    ChatResult,
    ChatSendRequest,
)

MAX_RETRIEVED_PASSAGES = 20
FALLBACK_PASSAGES = 10
MAX_EVIDENCE_CHARS = 60_000
PROMPT_HISTORY_MESSAGES = 20
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does", "for", "from",
    "had", "has", "have", "how", "i", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "what", "when", "where", "which", "who", "why", "with",
}


class ChatGroundingError(Exception):
    safe_message = "The chat response could not be grounded in the selected case evidence. Please try again."


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def _tokens(value: str) -> set[str]:
    result: set[str] = set()
    for raw in re.findall(r"[\w₹]+", _normalized(value)):
        if len(raw) < 2 or raw in STOP_WORDS:
            continue
        result.add(raw)
        for suffix in ("ing", "ed", "es", "s"):
            if raw.endswith(suffix) and len(raw) > len(suffix) + 2:
                result.add(raw[: -len(suffix)])
                break
    return result


def _phrases(value: str) -> set[str]:
    words = [word for word in re.findall(r"[\w₹]+", _normalized(value)) if word not in STOP_WORDS]
    return {f"{words[index]} {words[index + 1]}" for index in range(len(words) - 1)}


def rank_passages(passages: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
    query_tokens = _tokens(question)
    query_phrases = _phrases(question)
    normalized_question = _normalized(question)
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, passage in enumerate(passages):
        content = str(passage.get("content", ""))
        document_name = str(passage.get("document_name", ""))
        content_tokens = _tokens(content)
        name_tokens = _tokens(document_name)
        overlap = len(query_tokens & content_tokens)
        name_overlap = len(query_tokens & name_tokens)
        normalized_content = _normalized(content)
        phrase_bonus = sum(4 for phrase in query_phrases if phrase in normalized_content)
        if normalized_question and normalized_question in normalized_content:
            phrase_bonus += 10
        score = overlap * 3 + name_overlap * 5 + phrase_bonus
        ranked.append((score, index, passage))
    positive = [item for item in ranked if item[0] > 0]
    if positive:
        positive.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in positive[:MAX_RETRIEVED_PASSAGES]]
    return passages[:FALLBACK_PASSAGES]


def render_evidence(passages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    selected: list[dict[str, Any]] = []
    size = 0
    for passage in passages[:MAX_RETRIEVED_PASSAGES]:
        page = f" | Page: {passage['page_number']}" if passage.get("page_number") is not None else ""
        chunk = (
            f"Document: {passage['document_name']}\n"
            f"Passage ID: {passage['id']} | Label: {passage['passage_label']}{page}\n"
            f"{passage['content']}"
        )
        addition = len(chunk) + (2 if chunks else 0)
        if size + addition > MAX_EVIDENCE_CHARS:
            break
        chunks.append(chunk)
        selected.append(passage)
        size += addition
    return "\n\n".join(chunks), selected


def validate_chat_result(result: ChatResult, selected_passages: list[dict[str, Any]]) -> ChatResult:
    if result.response_type == "general_guidance":
        return result
    passages = {str(row["id"]): row for row in selected_passages}
    for citation in result.citations:
        passage = passages.get(str(citation.passage_id))
        if not passage:
            raise ChatGroundingError()
        quote = _normalized(citation.quote)
        if not quote or quote not in _normalized(str(passage["content"])):
            raise ChatGroundingError()
    return result


def _message_response(row: dict[str, Any], citations: list[dict[str, Any]]) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=row["id"],
        exchange_id=row["exchange_id"],
        role=row["role"],
        content=row["content"],
        response_type=row.get("response_type"),
        citations=[ChatCitationResponse.model_validate(item) for item in citations],
        created_at=row["created_at"],
    )


async def get_chat_history(
    gateway: SupabaseGateway, user: CurrentUser, case_id: UUID
) -> list[ChatMessageResponse]:
    repository = ChatRepository(gateway, user)
    rows = await repository.latest_messages(case_id, 100)
    assistant_ids = [str(row["id"]) for row in rows if row["role"] == "assistant"]
    citations = await repository.citations_for_messages(assistant_ids)
    return [_message_response(row, citations.get(str(row["id"]), [])) for row in rows]


async def send_chat_message(
    gateway: SupabaseGateway,
    user: CurrentUser,
    case_id: UUID,
    payload: ChatSendRequest,
    settings: Settings,
) -> ChatExchangeResponse:
    repository = ChatRepository(gateway, user)
    passages = await repository.ready_passages(case_id)
    ranked = rank_passages(passages, payload.message)
    evidence_text, selected = render_evidence(ranked)
    history_rows = await repository.latest_messages(case_id, PROMPT_HISTORY_MESSAGES)
    reviewed_details = await repository.confirmed_details(case_id)
    prompt = ChatPrompt(
        question=payload.message,
        uploaded_evidence=evidence_text,
        lawyer_reviewed_details="\n".join(reviewed_details),
        history=[ChatHistoryItem(role=row["role"], content=row["content"]) for row in history_rows],
    )
    if not settings.groq_is_configured:
        raise unavailable("AI chat is not configured")

    client = GroqClient(settings)
    try:
        result = validate_chat_result(await client.answer_case_question(prompt), selected)
    except (GroqError, ChatGroundingError) as exc:
        detail = exc.safe_message if hasattr(exc, "safe_message") else "Chat could not be completed. Please try again."
        raise unavailable(detail) from exc
    finally:
        await client.close()

    user_id, assistant_id = await repository.save_exchange(
        case_id,
        payload.message,
        result.content,
        result.response_type,
        [citation.model_dump(mode="json") for citation in result.citations],
    )
    rows = await repository.latest_messages(case_id, 100)
    by_id = {str(row["id"]): row for row in rows}
    if user_id not in by_id or assistant_id not in by_id:
        raise unavailable("Saved chat response could not be loaded. Please refresh the conversation.")
    citations = await repository.citations_for_messages([assistant_id])
    return ChatExchangeResponse(
        user_message=_message_response(by_id[user_id], []),
        assistant_message=_message_response(by_id[assistant_id], citations.get(assistant_id, [])),
    )
