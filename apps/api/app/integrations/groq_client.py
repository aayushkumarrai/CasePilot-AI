from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.analysis.schemas import AnalysisPrompt, AnalysisResult
from app.modules.chat.schemas import ChatPrompt, ChatResult


class GroqError(Exception):
    safe_message = "The AI provider could not complete the request."
    retryable = False


class GroqConfigurationError(GroqError):
    safe_message = "AI analysis is not configured."


class GroqTemporaryError(GroqError):
    safe_message = "The AI provider is temporarily unavailable. Please try again."
    retryable = True

    def __init__(self, reason: str = "temporary provider failure") -> None:
        self.reason = reason
        super().__init__(self.safe_message)


class GroqProviderError(GroqError):
    safe_message = "The AI provider rejected the request."

    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(self.safe_message)


class GroqInvalidJsonError(GroqError):
    safe_message = "The AI provider returned an unreadable response."


class GroqInvalidOutputError(GroqError):
    safe_message = "The AI provider returned an invalid analysis result."


class GroqInvalidChatOutputError(GroqError):
    safe_message = "The AI provider returned an invalid chat response. Please try again."


SYSTEM_PROMPT = """You are CasePilot AI, a legal case-preparation assistant. Return one JSON object only.
Use only uploaded evidence for factual claims. Do not provide legal conclusions or decide which conflicting account is true.
Preserve competing accounts as conflicts. Describe absent records only as \"not found in uploaded material.\"
Use unknown rather than guessing names, dates, amounts, or legal meaning. Proposed tasks must be lawyer-review actions.
Lawyer-provided context is not document evidence: never cite it, convert it into a fact, timeline event, payment claim, or conflict resolution.
Every factual output, including the case summary, must have at least one citation. Every citation must use a supplied passage_id and target an output ref in this response. Case-summary citations must use target_type \"case_summary\" and target_ref \"case_summary\".

Return exactly this JSON object shape. When evidence explicitly names a party and role (for example Buyer, Seller, Landlord, Tenant, Plaintiff, Defendant), include it in case_parties rather than encoding the person as a case field. When evidence explicitly states material payment, possession, property, or agreement facts, include grounded case fields. Create a timeline event for every explicit material date or dated act. Create a conflict finding whenever the evidence contains competing accounts, a refusal, disputed acceptance or possession, or inconsistent performance. Create a gap finding when a material expected record is expressly absent or not found in the uploaded material. Create at least one grounded lawyer-review task for every finding; tasks may also request verification of a material fact or record and may use a null finding_ref. Use empty arrays only when the uploaded evidence genuinely lacks that category.
Use empty arrays when an output category has no evidence-backed items:
{
  \"case_summary\": \"string\",
  \"document_summaries\": [{\"ref\": \"doc_summary_1\", \"document_id\": \"UUID from evidence\", \"summary\": \"string\"}],
  \"case_fields\": [{\"ref\": \"field_1\", \"field_key\": \"string\", \"label\": \"string\", \"value\": \"string\", \"confidence\": 0.0}],
  \"case_parties\": [{\"ref\": \"party_1\", \"name\": \"string\", \"role\": \"string\"}],
  \"timeline_events\": [{\"ref\": \"event_1\", \"event_date_text\": \"string\", \"date_confidence\": \"exact|month|year|unknown\", \"title\": \"string\", \"description\": \"string\"}],
  \"findings\": [{\"ref\": \"finding_1\", \"kind\": \"conflict|gap\", \"title\": \"string\", \"description\": \"string\"}],
  \"tasks\": [{\"ref\": \"task_1\", \"finding_ref\": \"optional finding ref or null\", \"title\": \"string\", \"description\": \"string\"}],
  \"citations\": [{\"target_type\": \"case_summary|document_summary|case_field|case_party|timeline_event|finding|task\", \"target_ref\": \"case_summary or matching output ref\", \"passage_id\": \"UUID from evidence\", \"quote\": \"verbatim supporting text\"}]
}
Do not add fields. Include no markdown or text outside the JSON object."""
CHAT_SYSTEM_PROMPT = """You are CasePilot AI, an evidence-grounded legal case-preparation assistant. Return one JSON object only.
Do not provide legal conclusions, decide which conflicting account is true, or invent facts. Preserve conflicts and use "not found in uploaded material" when the supplied passages do not answer the question.

Uploaded evidence is the only source that may support factual case answers or citations. Conversation history and confirmed lawyer-reviewed details provide context only; never cite them or silently use them to override uploaded evidence.

If uploaded evidence answers the question, return response_type "evidence", include one to five citations, and use only supplied passage IDs. Every quote must be a verbatim substring of the cited passage.
If uploaded evidence cannot answer the question, return response_type "general_guidance", no citations, and begin content exactly with "General guidance — not based on case documents." Explain that the answer was not found in uploaded material and suggest a record to inspect or request.

Return exactly this shape with no extra fields, markdown, or text outside the JSON object:
{
  "response_type": "evidence|general_guidance",
  "content": "string",
  "citations": [{"passage_id": "UUID from uploaded evidence", "quote": "verbatim supporting text"}]
}"""
REQUEST_TIMEOUT = httpx.Timeout(connect=10, read=60, write=60, pool=10)
MAX_COMPLETION_TOKENS = 8192


class GroqClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.groq_base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def analyze_case(self, prompt: AnalysisPrompt, corrective_instruction: str | None = None) -> AnalysisResult:
        if not self.settings.groq_is_configured:
            raise GroqConfigurationError()
        payload = {
            "model": self.settings.groq_model,
            "temperature": 0,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "stream": False,
            "reasoning_effort": "low",
            "reasoning_format": "hidden",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + ("\n\n" + corrective_instruction if corrective_instruction else "")},
                {"role": "user", "content": self._user_prompt(prompt)},
            ],
        }
        return self._parse_response(await self._request(payload))

    async def answer_case_question(self, prompt: ChatPrompt) -> ChatResult:
        if not self.settings.groq_is_configured:
            raise GroqConfigurationError()
        payload = {
            "model": self.settings.groq_model,
            "temperature": 0,
            "max_completion_tokens": 4096,
            "stream": False,
            "reasoning_effort": "low",
            "reasoning_format": "hidden",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": self._chat_user_prompt(prompt)},
            ],
        }
        return self._parse_chat_response(await self._request(payload))

    async def _request(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.settings.groq_api_key}"}
        for attempt in range(2):
            try:
                response = await self._client.post(
                    "/chat/completions", json=payload, headers=headers, timeout=REQUEST_TIMEOUT
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise GroqTemporaryError("request timed out or could not connect") from exc
            if response.status_code in {408, 429} or response.status_code >= 500:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise GroqTemporaryError(f"provider returned HTTP {response.status_code}")
            if response.is_error:
                raise GroqProviderError(response.status_code)
            return response
        raise GroqTemporaryError()

    @staticmethod
    def _user_prompt(prompt: AnalysisPrompt) -> str:
        sections = [f"## Uploaded evidence\n{prompt.uploaded_evidence}"]
        if prompt.lawyer_context:
            sections.append(
                "## Lawyer-provided context — not document evidence\n"
                f"{prompt.lawyer_context}"
            )
        return "\n\n".join(sections)

    @staticmethod
    def _chat_user_prompt(prompt: ChatPrompt) -> str:
        sections = [
            "## Uploaded evidence\n" + (prompt.uploaded_evidence or "No relevant uploaded passages were retrieved."),
        ]
        if prompt.history:
            sections.append(
                "## Recent conversation — context only, not evidence\n"
                + "\n".join(f"{item.role}: {item.content}" for item in prompt.history)
            )
        if prompt.lawyer_reviewed_details:
            sections.append(
                "## Confirmed lawyer-reviewed details — not document evidence\n"
                + prompt.lawyer_reviewed_details
            )
        sections.append("## Lawyer question\n" + prompt.question)
        return "\n\n".join(sections)

    @staticmethod
    def _message_content(response: httpx.Response) -> str:
        try:
            payload: dict[str, Any] = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GroqInvalidJsonError() from exc
        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            )
        if not isinstance(content, str) or not content.strip():
            raise GroqInvalidJsonError()
        return content

    @staticmethod
    def _parse_response(response: httpx.Response) -> AnalysisResult:
        content = GroqClient._message_content(response)
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GroqInvalidJsonError() from exc
        if not isinstance(result, dict):
            raise GroqInvalidJsonError()
        try:
            return AnalysisResult.model_validate(result)
        except ValidationError as exc:
            raise GroqInvalidOutputError() from exc

    @staticmethod
    def _parse_chat_response(response: httpx.Response) -> ChatResult:
        content = GroqClient._message_content(response)
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GroqInvalidJsonError() from exc
        if not isinstance(result, dict):
            raise GroqInvalidJsonError()
        try:
            return ChatResult.model_validate(result)
        except ValidationError as exc:
            raise GroqInvalidChatOutputError() from exc
