from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from app.modules.analysis.schemas import AnalysisResult
from app.modules.analysis.service import (
    CASE_SUMMARY_REF,
    MAX_EVIDENCE_CHARS,
    CitationValidator,
    EvidenceAssembler,
    EvidenceTooLarge,
    GroundingValidationError,
)


CASE_ID = uuid4()
DOCUMENT_A = uuid4()
DOCUMENT_B = uuid4()
PASSAGE_A = uuid4()
PASSAGE_B = uuid4()


class FakeRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    async def ready_documents_with_passages(self, case_id: UUID) -> list[dict]:
        assert case_id == CASE_ID
        return self.rows


def evidence_rows() -> list[dict]:
    return [
        {
            "id": str(DOCUMENT_A),
            "file_name": "receipt.txt",
            "passages": [
                {
                    "id": str(PASSAGE_A),
                    "document_id": str(DOCUMENT_A),
                    "sequence_number": 1,
                    "page_number": None,
                    "passage_label": "Passage 1",
                    "content": "Payment receipt received. Possession remains disputed.",
                }
            ],
        },
        {
            "id": str(DOCUMENT_B),
            "file_name": "notice.txt",
            "passages": [
                {
                    "id": str(PASSAGE_B),
                    "document_id": str(DOCUMENT_B),
                    "sequence_number": 1,
                    "page_number": 2,
                    "passage_label": "Page 2, Passage 1",
                    "content": "Seller states keys were handed over on 10 June.",
                }
            ],
        },
    ]


def assemble(rows: list[dict] | None = None):
    return asyncio.run(EvidenceAssembler(FakeRepository(rows or evidence_rows())).assemble(CASE_ID, "Focus on payment."))


def valid_result() -> AnalysisResult:
    return AnalysisResult.model_validate(
        {
            "case_summary": "Payment is documented and possession remains disputed.",
            "document_summaries": [{"ref": "doc-1", "document_id": str(DOCUMENT_A), "summary": "Receipt documents payment."}],
            "case_fields": [{"ref": "field-1", "field_key": "payment", "label": "Payment", "value": "Receipt received", "confidence": 0.9}],
            "case_parties": [],
            "timeline_events": [],
            "findings": [{"ref": "finding-1", "kind": "conflict", "title": "Possession", "description": "Possession remains disputed."}],
            "tasks": [{"ref": "task-1", "finding_ref": "finding-1", "title": "Verify possession", "description": "Request handover records."}],
            "citations": [
                {"target_type": "case_summary", "target_ref": CASE_SUMMARY_REF, "passage_id": str(PASSAGE_A), "quote": "Payment receipt received."},
                {"target_type": "document_summary", "target_ref": "doc-1", "passage_id": str(PASSAGE_A), "quote": "Payment receipt received."},
                {"target_type": "case_field", "target_ref": "field-1", "passage_id": str(PASSAGE_A), "quote": "Payment receipt received."},
                {"target_type": "finding", "target_ref": "finding-1", "passage_id": str(PASSAGE_A), "quote": "Possession remains disputed."},
                {"target_type": "task", "target_ref": "task-1", "passage_id": str(PASSAGE_A), "quote": "Possession remains disputed."},
            ],
        }
    )


def test_assembler_builds_deterministic_ready_evidence() -> None:
    bundle = assemble()
    assert "Document: receipt.txt" in bundle.prompt.uploaded_evidence
    assert bundle.prompt.uploaded_evidence.index(str(DOCUMENT_A)) < bundle.prompt.uploaded_evidence.index(str(DOCUMENT_B))
    assert f"Passage ID: {PASSAGE_B} | Label: Page 2, Passage 1 | Page: 2" in bundle.prompt.uploaded_evidence
    assert bundle.prompt.lawyer_context == "Focus on payment."


def test_assembler_rejects_evidence_over_budget_without_truncating() -> None:
    rows = evidence_rows()
    rows[0]["passages"][0]["content"] = "x" * MAX_EVIDENCE_CHARS
    with pytest.raises(EvidenceTooLarge):
        assemble(rows)


def test_validator_keeps_only_grounded_output_and_payload_maps_summary_citations() -> None:
    validated = CitationValidator().validate(valid_result(), assemble())
    payload = validated.completion_payload()
    assert payload["p_case_summary"]
    assert payload["p_citations"][0]["target_type"] == "case_summary"
    assert "confidence" not in payload["p_case_fields"][0]


def test_validator_drops_cross_document_summary_and_wrong_quote() -> None:
    result = valid_result().model_copy(deep=True)
    result.citations[1] = result.citations[1].model_copy(update={"passage_id": PASSAGE_B})
    result.citations[2] = result.citations[2].model_copy(update={"quote": "Invented payment"})
    validated = CitationValidator().validate(result, assemble()).result
    assert validated.document_summaries == []
    assert validated.case_fields == []


def test_validator_normalizes_unicode_and_whitespace_quotes() -> None:
    rows = evidence_rows()
    rows[0]["passages"][0]["content"] = "Payment\u00a0receipt\nreceived. Possession remains disputed."
    result = valid_result().model_copy(deep=True)
    result.citations[0] = result.citations[0].model_copy(update={"quote": "Payment receipt received."})
    validated = CitationValidator().validate(result, assemble(rows)).result
    assert validated.citations[0].target_type == "case_summary"


def test_validator_drops_task_when_its_finding_is_ungrounded() -> None:
    result = valid_result().model_copy(deep=True)
    result.citations[3] = result.citations[3].model_copy(update={"quote": "Missing handover proof"})
    validated = CitationValidator().validate(result, assemble()).result
    assert validated.findings == []
    assert validated.tasks == []


def test_validator_rejects_uncited_case_summary_and_context_is_not_a_source() -> None:
    result = valid_result().model_copy(deep=True)
    result.citations = [citation for citation in result.citations if citation.target_type != "case_summary"]
    with pytest.raises(GroundingValidationError):
        CitationValidator().validate(result, assemble())
