from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.dependencies import CurrentUser
from app.integrations.supabase_gateway import SupabaseGateway

from .repository import AnalysisRepository
from .schemas import AnalysisPrompt, AnalysisResult, CASE_SUMMARY_REF, Citation

MAX_EVIDENCE_CHARS = 180_000


class EvidenceTooLarge(Exception):
    safe_message = "Uploaded evidence is too large to analyze together. Narrow the uploaded material and try again."


class NoReadyEvidence(Exception):
    safe_message = "No readable passages were found in ready documents."


class GroundingValidationError(Exception):
    safe_message = "The AI response did not provide valid evidence for the case summary."


class StoredPassage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    document_id: UUID
    sequence_number: int
    page_number: int | None = None
    passage_label: str
    content: str


class StoredDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    file_name: str
    passages: list[StoredPassage]


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: list[StoredDocument]
    prompt: AnalysisPrompt


class ValidatedAnalysisResult(BaseModel):
    """Only evidence-grounded output that Stage 3.4 may send to the completion RPC."""

    model_config = ConfigDict(frozen=True)

    result: AnalysisResult

    def completion_payload(self) -> dict:
        data = self.result.model_dump(mode="json")
        for field_name in (
            "document_summaries",
            "case_fields",
            "case_parties",
            "timeline_events",
            "findings",
            "tasks",
        ):
            for item in data[field_name]:
                item.pop("confidence", None)
        return {
            "p_case_summary": data["case_summary"],
            "p_document_summaries": data["document_summaries"],
            "p_case_fields": data["case_fields"],
            "p_case_parties": data["case_parties"],
            "p_timeline_events": data["timeline_events"],
            "p_findings": data["findings"],
            "p_tasks": data["tasks"],
            "p_citations": data["citations"],
        }


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def _citation_is_valid(citation: Citation, passages: dict[UUID, StoredPassage]) -> bool:
    passage = passages.get(citation.passage_id)
    if not passage:
        return False
    quote = _normalized(citation.quote)
    return bool(quote and quote in _normalized(passage.content))


class EvidenceAssembler:
    def __init__(self, repository: AnalysisRepository) -> None:
        self.repository = repository

    async def assemble(self, case_id: UUID, lawyer_context: str | None = None) -> EvidenceBundle:
        rows = await self.repository.ready_documents_with_passages(case_id)
        documents = [
            StoredDocument(
                id=UUID(str(row["id"])),
                file_name=row["file_name"],
                passages=[StoredPassage.model_validate(passage) for passage in row["passages"]],
            )
            for row in rows
        ]
        rendered = self._render(documents)
        if not rendered:
            raise NoReadyEvidence()
        if len(rendered) > MAX_EVIDENCE_CHARS:
            raise EvidenceTooLarge()
        return EvidenceBundle(
            documents=documents,
            prompt=AnalysisPrompt(uploaded_evidence=rendered, lawyer_context=lawyer_context),
        )

    @staticmethod
    def _render(documents: list[StoredDocument]) -> str:
        chunks: list[str] = []
        for document in documents:
            chunks.append(f"### Document: {document.file_name}\nDocument ID: {document.id}")
            for passage in document.passages:
                page = f" | Page: {passage.page_number}" if passage.page_number is not None else ""
                chunks.append(
                    f"Passage ID: {passage.id} | Label: {passage.passage_label}{page}\n{passage.content}"
                )
        return "\n\n".join(chunks)


class CitationValidator:
    def validate(self, result: AnalysisResult, bundle: EvidenceBundle) -> ValidatedAnalysisResult:
        passages = {
            passage.id: passage
            for document in bundle.documents
            for passage in document.passages
        }
        document_ids = {document.id for document in bundle.documents}
        citations_by_target: dict[tuple[str, str], list[Citation]] = defaultdict(list)
        for citation in result.citations:
            if not _citation_is_valid(citation, passages):
                continue
            if citation.target_type == "document_summary":
                summary = next((item for item in result.document_summaries if item.ref == citation.target_ref), None)
                if not summary or passages[citation.passage_id].document_id != summary.document_id:
                    continue
            citations_by_target[(citation.target_type, citation.target_ref)].append(citation)

        if not citations_by_target.get(("case_summary", CASE_SUMMARY_REF)):
            raise GroundingValidationError()

        document_summaries = [
            item for item in result.document_summaries
            if item.document_id in document_ids and citations_by_target.get(("document_summary", item.ref))
        ]
        case_fields = [item for item in result.case_fields if citations_by_target.get(("case_field", item.ref))]
        case_parties = [item for item in result.case_parties if citations_by_target.get(("case_party", item.ref))]
        timeline_events = [item for item in result.timeline_events if citations_by_target.get(("timeline_event", item.ref))]
        findings = [item for item in result.findings if citations_by_target.get(("finding", item.ref))]
        kept_finding_refs = {item.ref for item in findings}
        tasks = [
            item for item in result.tasks
            if citations_by_target.get(("task", item.ref))
            and (item.finding_ref is None or item.finding_ref in kept_finding_refs)
        ]

        kept_refs = {
            ("case_summary", CASE_SUMMARY_REF),
            *[("document_summary", item.ref) for item in document_summaries],
            *[("case_field", item.ref) for item in case_fields],
            *[("case_party", item.ref) for item in case_parties],
            *[("timeline_event", item.ref) for item in timeline_events],
            *[("finding", item.ref) for item in findings],
            *[("task", item.ref) for item in tasks],
        }
        citations = [
            citation for citation in result.citations
            if (citation.target_type, citation.target_ref) in kept_refs
            and citation in citations_by_target[(citation.target_type, citation.target_ref)]
        ]
        validated = AnalysisResult(
            case_summary=result.case_summary,
            document_summaries=document_summaries,
            case_fields=case_fields,
            case_parties=case_parties,
            timeline_events=timeline_events,
            findings=findings,
            tasks=tasks,
            citations=citations,
        )
        return ValidatedAnalysisResult(result=validated)


def analysis_assembler(gateway: SupabaseGateway, user: CurrentUser) -> EvidenceAssembler:
    return EvidenceAssembler(AnalysisRepository(gateway, user))
