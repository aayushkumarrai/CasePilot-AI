from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.groq_client import (
    GroqClient,
    GroqConfigurationError,
    GroqInvalidJsonError,
    GroqInvalidOutputError,
    GroqProviderError,
    GroqTemporaryError,
)
from app.main import app
from app.modules.analysis.schemas import AnalysisPrompt, AnalysisResult


def fixture_result() -> dict:
    document_id = str(uuid4())
    passage_id = str(uuid4())
    return {
        "case_summary": "Payment evidence is present and possession remains disputed.",
        "document_summaries": [{"ref": "summary-1", "document_id": document_id, "summary": "Payment receipt."}],
        "case_fields": [{"ref": "field-1", "field_key": "payment_status", "label": "Payment status", "value": "Receipt present", "confidence": 0.91}],
        "case_parties": [{"ref": "party-1", "name": "Rao", "role": "Buyer"}],
        "timeline_events": [{"ref": "event-1", "event_date_text": "unknown", "date_confidence": "unknown", "title": "Payment receipt", "description": "A receipt is present."}],
        "findings": [{"ref": "finding-1", "kind": "gap", "title": "Handover acknowledgment", "description": "Not found in uploaded material."}],
        "tasks": [{"ref": "task-1", "finding_ref": "finding-1", "title": "Request acknowledgment", "description": "Request the signed handover acknowledgment."}],
        "citations": [{"target_type": "case_field", "target_ref": "field-1", "passage_id": passage_id, "quote": "Payment receipt received."}],
    }


def configured_settings() -> Settings:
    return Settings(groq_api_key="test-key", groq_model="openai/gpt-oss-20b", groq_base_url="https://groq.test/v1")


def test_missing_groq_configuration_fails_before_network_request() -> None:
    async def run() -> None:
        client = GroqClient(Settings(groq_api_key=None, groq_model=None))
        with pytest.raises(GroqConfigurationError):
            await client.analyze_case(AnalysisPrompt(uploaded_evidence="passage"))
        await client.close()

    asyncio.run(run())


def test_client_requests_json_and_keeps_context_separate() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["timeout"] = request.extensions["timeout"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(fixture_result())}}]})

    async def run() -> AnalysisResult:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=transport) as http_client:
            client = GroqClient(configured_settings(), http_client)
            return await client.analyze_case(AnalysisPrompt(uploaded_evidence="passage-1: payment", lawyer_context="Focus on possession"))

    result = asyncio.run(run())
    assert result.case_fields[0].confidence == 0.91
    assert captured["url"] == "https://groq.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["payload"]["model"] == "openai/gpt-oss-20b"
    assert captured["payload"]["temperature"] == 0
    assert captured["payload"]["max_completion_tokens"] == 8192
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["reasoning_effort"] == "low"
    assert captured["payload"]["reasoning_format"] == "hidden"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    user_content = captured["payload"]["messages"][1]["content"]
    assert "## Uploaded evidence" in user_content
    assert "## Lawyer-provided context — not document evidence" in user_content
    assert "Focus on possession" in user_content
    assert captured["timeout"]["connect"] == 10
    assert captured["timeout"]["read"] == 60


def test_context_section_is_omitted_when_context_is_absent() -> None:
    assert "Lawyer-provided context" not in GroqClient._user_prompt(AnalysisPrompt(uploaded_evidence="passage"))


def test_client_accepts_text_content_blocks() -> None:
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": [{"type": "text", "text": json.dumps(fixture_result())}]}}]},
    )
    result = GroqClient._parse_response(response)
    assert result.case_summary.startswith("Payment evidence")


def test_transient_provider_failure_retries_once(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.integrations.groq_client.asyncio.sleep", no_sleep)
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"message": "rate limited"})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(fixture_result())}}]})

    async def run() -> None:
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=httpx.MockTransport(handler)) as http_client:
            await GroqClient(configured_settings(), http_client).analyze_case(AnalysisPrompt(uploaded_evidence="passage"))

    asyncio.run(run())
    assert attempts == 2


def test_timeout_retries_once_then_returns_safe_temporary_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.integrations.groq_client.asyncio.sleep", no_sleep)
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timed out", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=httpx.MockTransport(handler)) as http_client:
            with pytest.raises(GroqTemporaryError):
                await GroqClient(configured_settings(), http_client).analyze_case(AnalysisPrompt(uploaded_evidence="passage"))

    asyncio.run(run())
    assert attempts == 2


def test_invalid_json_and_invalid_output_are_rejected_without_retry() -> None:
    async def invalid_json() -> None:
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]}))) as http_client:
            with pytest.raises(GroqInvalidJsonError):
                await GroqClient(configured_settings(), http_client).analyze_case(AnalysisPrompt(uploaded_evidence="passage"))

    invalid = fixture_result()
    invalid["citations"][0]["target_ref"] = "missing-ref"

    async def invalid_output() -> None:
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(invalid)}}]}))) as http_client:
            with pytest.raises(GroqInvalidOutputError):
                await GroqClient(configured_settings(), http_client).analyze_case(AnalysisPrompt(uploaded_evidence="passage"))

    asyncio.run(invalid_json())
    asyncio.run(invalid_output())


def test_non_retryable_provider_error_and_no_public_analysis_route() -> None:
    async def run() -> None:
        async with httpx.AsyncClient(base_url="https://groq.test/v1", transport=httpx.MockTransport(lambda _: httpx.Response(400, json={"message": "bad request"}))) as http_client:
            with pytest.raises(GroqProviderError):
                await GroqClient(configured_settings(), http_client).analyze_case(AnalysisPrompt(uploaded_evidence="passage"))

    asyncio.run(run())
    assert "/v1/cases/{case_id}/analysis" not in app.openapi()["paths"]


def test_contract_rejects_excessive_or_invalid_values() -> None:
    too_many = fixture_result()
    too_many["case_fields"] = [fixture_result()["case_fields"][0] for _ in range(51)]
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(too_many)
    invalid_confidence = fixture_result()
    invalid_confidence["case_fields"][0]["confidence"] = 1.1
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(invalid_confidence)
