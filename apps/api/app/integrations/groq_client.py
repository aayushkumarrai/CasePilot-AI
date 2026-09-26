from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.analysis.schemas import AnalysisPrompt, AnalysisResult


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


SYSTEM_PROMPT = """You are CasePilot AI, a legal case-preparation assistant. Return one JSON object only.
Use only uploaded evidence for factual claims. Do not provide legal conclusions or decide which conflicting account is true.
Preserve competing accounts as conflicts. Describe absent records only as \"not found in uploaded material.\"
Use unknown rather than guessing names, dates, amounts, or legal meaning. Proposed tasks must be lawyer-review actions.
Lawyer-provided context is not document evidence: never cite it, convert it into a fact, timeline event, payment claim, or conflict resolution.
Every factual output, including the case summary, must have at least one citation. Every citation must use a supplied passage_id and target an output ref in this response. Case-summary citations must use target_type \"case_summary\" and target_ref \"case_summary\".

Return exactly this JSON object shape. When evidence explicitly names a party and role (for example Buyer, Seller, Landlord, Tenant, Plaintiff, Defendant), include that grounded party. When evidence explicitly states material payment, possession, property, date, or agreement facts, include grounded case fields. Use empty arrays only when the uploaded evidence lacks that category.
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
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.groq_api_key}",
        }
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
            return self._parse_response(response)
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
    def _parse_response(response: httpx.Response) -> AnalysisResult:
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
