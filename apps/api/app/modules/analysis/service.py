from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.dependencies import CurrentUser
from app.core.errors import unavailable
from app.integrations.groq_client import GroqClient, GroqError, GroqInvalidJsonError, GroqInvalidOutputError
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway

from .repository import AnalysisRepository
from .schemas import (
    AnalysisPrompt,
    AnalysisRunResponse,
    AnalysisStatusResponse,
    AnalysisResult,
    CASE_SUMMARY_REF,
    Citation,
    StartAnalysisRequest,
)

MAX_EVIDENCE_CHARS = 180_000
logger = logging.getLogger(__name__)


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
        # A provider may return a useful set of individually grounded outputs
        # while failing to ground its prose case summary. Persist those useful
        # outputs, but never store or display the unsupported summary. The RPC
        # converts this empty value to SQL null.
        summary_is_grounded = any(
            citation["target_type"] == "case_summary"
            and citation["target_ref"] == CASE_SUMMARY_REF
            for citation in data["citations"]
        )
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
            "p_case_summary": data["case_summary"] if summary_is_grounded else "",
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
    def validate(
        self,
        result: AnalysisResult,
        bundle: EvidenceBundle,
        *,
        require_case_summary: bool = True,
    ) -> ValidatedAnalysisResult:
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
            target = (citation.target_type, citation.target_ref)
            # Provider output may repeat or over-supply otherwise valid
            # citations. Persistence supports at most five per output, so keep
            # the provider's first five grounded citations deterministically.
            if len(citations_by_target[target]) < 5:
                citations_by_target[target].append(citation)

        if require_case_summary and not citations_by_target.get(("case_summary", CASE_SUMMARY_REF)):
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
            *[("document_summary", item.ref) for item in document_summaries],
            *[("case_field", item.ref) for item in case_fields],
            *[("case_party", item.ref) for item in case_parties],
            *[("timeline_event", item.ref) for item in timeline_events],
            *[("finding", item.ref) for item in findings],
            *[("task", item.ref) for item in tasks],
        }
        if citations_by_target.get(("case_summary", CASE_SUMMARY_REF)):
            kept_refs.add(("case_summary", CASE_SUMMARY_REF))
        citations: list[Citation] = []
        retained_counts: dict[tuple[str, str], int] = defaultdict(int)
        for citation in result.citations:
            target = (citation.target_type, citation.target_ref)
            if target not in kept_refs:
                continue
            retained = citations_by_target[target]
            position = retained_counts[target]
            if position < len(retained) and citation == retained[position]:
                citations.append(citation)
                retained_counts[target] += 1
        try:
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
        except ValidationError as exc:
            logger.error(
                "Grounded analysis validation failed: %s",
                exc.errors(include_input=False),
            )
            raise
        return ValidatedAnalysisResult(result=validated)


def analysis_assembler(gateway: SupabaseGateway, user: CurrentUser) -> EvidenceAssembler:
    return EvidenceAssembler(AnalysisRepository(gateway, user))


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


async def start_analysis(
    gateway: SupabaseGateway,
    user: CurrentUser,
    case_id: UUID,
    payload: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    settings: Settings,
) -> AnalysisRunResponse:
    """Preflight evidence before creating an immutable analysis run."""
    try:
        bundle = await analysis_assembler(gateway, user).assemble(case_id, payload.lawyer_context)
    except EvidenceTooLarge as exc:
        raise _unprocessable(exc.safe_message) from exc
    except NoReadyEvidence as exc:
        raise _unprocessable("At least one ready document is required for analysis") from exc
    if not settings.groq_is_configured:
        raise unavailable("AI analysis is not configured")

    run = await AnalysisRepository(gateway, user).start_run(case_id, payload.lawyer_context)
    # The RPC's snapshot is authoritative: it has trimmed the submitted text
    # and converted whitespace-only input to null before the provider sees it.
    snapshot = run.get("lawyer_context_snapshot")
    prepared_bundle = EvidenceBundle(
        documents=bundle.documents,
        prompt=AnalysisPrompt(
            uploaded_evidence=bundle.prompt.uploaded_evidence,
            lawyer_context=snapshot,
        ),
    )
    background_tasks.add_task(process_analysis, str(run["id"]), user.access_token, settings, prepared_bundle)
    return AnalysisRunResponse.model_validate(run)


async def get_analysis_status(
    gateway: SupabaseGateway, user: CurrentUser, case_id: UUID
) -> AnalysisStatusResponse:
    latest, has_completed_outputs = await AnalysisRepository(gateway, user).latest_run_status(case_id)
    return AnalysisStatusResponse(
        run=AnalysisRunResponse.model_validate(latest) if latest else None,
        has_completed_outputs=has_completed_outputs,
    )


async def process_analysis(
    analysis_run_id: str,
    access_token: str,
    settings: Settings,
    bundle: EvidenceBundle,
) -> None:
    """Execute one in-process run using the caller JWT so RLS remains active."""
    gateway = SupabaseGateway(settings.supabase_url or "", settings.supabase_anon_key or "", access_token)
    client = GroqClient(settings)
    try:
        processing = await gateway.rpc(
            "mark_analysis_run_processing_with_activity",
            {"p_analysis_run_id": analysis_run_id},
        )
        if not processing:
            return
        try:
            result = await client.analyze_case(bundle.prompt)
        except (GroqInvalidJsonError, GroqInvalidOutputError):
            result = await client.analyze_case(
                bundle.prompt,
                "SCHEMA REGENERATION: The previous response could not be validated. Return exactly the required JSON object shape, "
                "with valid enum values, unique refs, valid UUIDs copied from evidence, arrays within their limits, and citations that target existing refs. "
                "Do not include markdown or any text outside the JSON object.",
            )
        validator = CitationValidator()
        # Keep every independently grounded output even if the provider's case
        # summary citation is missing or invalid. completion_payload omits the
        # unsupported summary before persistence.
        validated = validator.validate(result, bundle, require_case_summary=False)
        missing_categories = _missing_supported_categories(validated.result, bundle)
        if missing_categories:
            try:
                corrected = await client.analyze_case(
                    bundle.prompt,
                    "CORRECTIVE PASS: The first grounded result omitted evidence-supported output categories: "
                    + ", ".join(sorted(missing_categories))
                    + ". Return the complete JSON shape again. The arrays for those specifically named categories MUST be non-empty because the uploaded evidence contains explicit support. "
                    "For timeline_events, extract every material dated act. For findings, capture disputed acceptance, possession, performance, competing accounts, and expressly missing records. "
                    "For tasks, propose a grounded lawyer-review or record-verification action and link it to a finding when applicable. "
                    "Populate all other categories only where the uploaded evidence explicitly supports them. "
                    "Every item must have a citation whose quote is an exact verbatim substring of the supplied passage. "
                    "Include grounded review tasks for supported conflicts or missing records. Do not invent anything.",
                )
                candidate = validator.validate(
                    corrected,
                    bundle,
                    require_case_summary=False,
                )
                validated = ValidatedAnalysisResult(
                    result=_merge_grounded_results(validated.result, candidate.result)
                )
                remaining = _missing_supported_categories(validated.result, bundle)
                logger.info(
                    "Analysis corrective pass retained counts fields=%d parties=%d timeline=%d findings=%d tasks=%d remaining_categories=%d",
                    len(validated.result.case_fields),
                    len(validated.result.case_parties),
                    len(validated.result.timeline_events),
                    len(validated.result.findings),
                    len(validated.result.tasks),
                    len(remaining),
                )
            except Exception as exc:
                # A valid first response is retained when the optional correction cannot improve it.
                logger.warning(
                    "Analysis corrective pass was discarded after %s",
                    type(exc).__name__,
                )
        validated = ValidatedAnalysisResult(result=_ensure_grounded_tasks(validated.result))
        await gateway.rpc(
            "complete_analysis_run_with_outputs",
            {"p_analysis_run_id": analysis_run_id, **validated.completion_payload()},
        )
    except Exception as exc:
        # Record only the exception type. Analysis inputs, provider output,
        # lawyer context, and credentials must never enter application logs.
        logger.error(
            "Analysis run %s failed with %s",
            analysis_run_id,
            type(exc).__name__,
        )
        await _fail_analysis(gateway, analysis_run_id, _safe_analysis_error(exc))
    finally:
        await client.close()
        await gateway.close()


def _missing_supported_categories(result: AnalysisResult, bundle: EvidenceBundle) -> set[str]:
    """Identify empty categories that the uploaded evidence clearly supports."""
    evidence = bundle.prompt.uploaded_evidence.casefold()
    party_signal = bool(re.search(r"\b(buyer|seller|landlord|tenant|plaintiff|defendant|vendor|purchaser)\b", evidence))
    field_signal = bool(re.search(r"\b(inr|rs\.?|payment|paid|possession|property|agreement|handover|keys?)\b", evidence))
    date_signal = bool(
        re.search(
            r"\b(?:19|20)\d{2}\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
            evidence,
        )
    )
    finding_signal = bool(
        re.search(
            r"\b(dispute[ds]?|conflict(?:ing)?|contradict(?:s|ed|ory)?|missing|absent|not found|no signed|no record|"
            r"did not accept|refus(?:e|ed|al)|den(?:y|ied)|declin(?:e|ed)|failed to|delay(?:ed)?|requested inspection|"
            r"remains? pending|not delivered|not received)\b",
            evidence,
        )
    )
    missing: set[str] = set()
    if len(result.document_summaries) < len(bundle.documents):
        missing.add("document_summaries")
    if party_signal and not result.case_parties:
        missing.add("case_parties")
    if field_signal and not result.case_fields:
        missing.add("case_fields")
    if date_signal and not result.timeline_events:
        missing.add("timeline_events")
    if finding_signal and not result.findings:
        missing.add("findings")
    if (finding_signal or result.findings or result.case_fields or result.case_parties) and not result.tasks:
        missing.add("tasks")
    return missing


def _needs_corrective_retry(result: AnalysisResult, bundle: EvidenceBundle) -> bool:
    """Compatibility wrapper used by tests and callers that need a boolean."""
    return bool(_missing_supported_categories(result, bundle))


def _merge_grounded_results(primary: AnalysisResult, correction: AnalysisResult) -> AnalysisResult:
    """Fill empty categories from a grounded correction without erasing valid first-pass output."""
    category_targets = {
        "document_summaries": "document_summary",
        "case_fields": "case_field",
        "case_parties": "case_party",
        "timeline_events": "timeline_event",
        "findings": "finding",
        "tasks": "task",
    }
    selected: dict[str, list] = {}
    selected_refs: dict[str, set[str]] = {"case_summary": {CASE_SUMMARY_REF}}
    source_for_target: dict[str, AnalysisResult] = {"case_summary": primary}
    for category, target_type in category_targets.items():
        primary_items = list(getattr(primary, category))
        correction_items = list(getattr(correction, category))
        correction_is_better = (
            category == "document_summaries"
            and len(correction_items) > len(primary_items)
        )
        source = correction if correction_is_better or not primary_items else primary
        items = correction_items if correction_is_better or not primary_items else primary_items
        selected[category] = items
        selected_refs[target_type] = {item.ref for item in items}
        source_for_target[target_type] = source

    # A correction task may refer to an equivalent correction finding that was
    # not selected because the first pass already had findings. The task still
    # has its own grounded citation, so retain it without the stale link.
    selected["tasks"] = [
        task if task.finding_ref is None or task.finding_ref in selected_refs["finding"]
        else task.model_copy(update={"finding_ref": None})
        for task in selected["tasks"]
    ]
    selected_refs["task"] = {item.ref for item in selected["tasks"]}

    citations: list[Citation] = []
    for target_type, refs in selected_refs.items():
        source = source_for_target[target_type]
        citations.extend(
            citation
            for citation in source.citations
            if citation.target_type == target_type and citation.target_ref in refs
        )
    return AnalysisResult(
        case_summary=primary.case_summary,
        citations=citations,
        **selected,
    )


def _ensure_grounded_tasks(result: AnalysisResult) -> AnalysisResult:
    """Create review actions for grounded findings when the provider omitted tasks."""
    if result.tasks or not result.findings:
        return result
    data = result.model_dump(mode="json")
    # Provider output can contain a citation for a task that it then omitted
    # from the tasks array. Drop every stale task citation before adding the
    # deterministic grounded review tasks below.
    citations: list[dict] = [
        citation for citation in data["citations"]
        if citation["target_type"] != "task"
    ]
    tasks: list[dict] = []
    for index, finding in enumerate(data["findings"], start=1):
        ref = f"grounded_review_task_{index}"
        finding_citations = [
            citation for citation in data["citations"]
            if citation["target_type"] == "finding" and citation["target_ref"] == finding["ref"]
        ]
        if not finding_citations:
            continue
        tasks.append(
            {
                "ref": ref,
                "finding_ref": finding["ref"],
                "title": f"Review {finding['title']}",
                "description": "Review the cited evidence and record the appropriate lawyer follow-up.",
            }
        )
        citations.extend(
            {**citation, "target_type": "task", "target_ref": ref}
            for citation in finding_citations
        )
    data["tasks"] = tasks
    data["citations"] = citations
    return AnalysisResult.model_validate(data)


def _safe_analysis_error(exc: Exception) -> str:
    if isinstance(exc, GroqError):
        return exc.safe_message
    if isinstance(exc, GroundingValidationError):
        return exc.safe_message
    if isinstance(exc, EvidenceTooLarge):
        return exc.safe_message
    if isinstance(exc, NoReadyEvidence):
        return "No ready document evidence was available for analysis."
    if isinstance(exc, SupabaseError):
        return "Analysis results could not be saved. Please try again."
    return "Analysis could not be completed. Please try again."


async def _fail_analysis(gateway: SupabaseGateway, analysis_run_id: str, message: str) -> None:
    try:
        await gateway.rpc(
            "fail_analysis_run_with_activity",
            {"p_analysis_run_id": analysis_run_id, "p_error_message": message},
        )
    except SupabaseError:
        # There is no safe recovery if the same RLS-scoped connection cannot
        # report the failure. Do not expose storage/provider internals.
        return
