from __future__ import annotations

from uuid import uuid4

import asyncio

from app.core.dependencies import CurrentUser
from app.modules.review.service import get_overview, get_timeline


class ReviewGateway:
    def __init__(self, *, completed: bool = True) -> None:
        self.case_id, self.doc_id, self.passage_id = map(lambda _: str(uuid4()), range(3))
        self.run_id = str(uuid4())
        self.case = {"id": self.case_id, "external_case_id": "PROP-REVIEW-1", "case_name": "Rao v Mehta", "status": "review", "archived_at": None, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z", "lawyer_context": "Check possession records."}
        self.run = {"id": self.run_id, "case_id": self.case_id, "status": "completed", "case_summary": "Payment is recorded and possession remains disputed.", "completed_at": "2026-01-02T00:00:00Z", "created_at": "2026-01-01T00:00:00Z"} if completed else None
        self.ids = {kind: str(uuid4()) for kind in ("summary", "field_pending", "field_confirmed", "party", "timeline_exact", "timeline_month", "timeline_year", "timeline_unknown", "finding", "task")}

    async def select(self, table, params, *, single=False):
        rows = []
        if table == "cases": rows = [self.case] if self.case["archived_at"] is None else []
        elif table == "analysis_runs": rows = [self.run] if self.run else []
        elif self.run:
            data = {
                "document_summaries": [{"id": self.ids["summary"], "analysis_run_id": self.run_id, "document_id": self.doc_id, "summary": "Payment and possession statement.", "created_at": "2026-01-01T00:00:00Z"}],
                "case_fields": [{"id": self.ids["field_pending"], "analysis_run_id": self.run_id, "field_key": "payment", "label": "Payment", "value": "INR 500000", "status": "pending", "created_at": "2026-01-01T00:00:00Z"}, {"id": self.ids["field_confirmed"], "analysis_run_id": self.run_id, "field_key": "status", "label": "Status", "value": "Paid", "status": "confirmed", "created_at": "2026-01-01T00:00:00Z"}],
                "case_parties": [{"id": self.ids["party"], "analysis_run_id": self.run_id, "name": "Rao", "role": "Buyer", "status": "pending", "created_at": "2026-01-01T00:00:00Z"}],
                "timeline_events": [{"id": self.ids["timeline_unknown"], "analysis_run_id": self.run_id, "event_date_text": "unknown", "date_confidence": "unknown", "title": "Unknown", "description": "Unknown", "created_at": "2026-01-04T00:00:00Z"}, {"id": self.ids["timeline_year"], "analysis_run_id": self.run_id, "event_date_text": "2025", "date_confidence": "year", "title": "Year", "description": "Year", "created_at": "2026-01-03T00:00:00Z"}, {"id": self.ids["timeline_month"], "analysis_run_id": self.run_id, "event_date_text": "June 2025", "date_confidence": "month", "title": "Month", "description": "Month", "created_at": "2026-01-02T00:00:00Z"}, {"id": self.ids["timeline_exact"], "analysis_run_id": self.run_id, "event_date_text": "10 May 2025", "date_confidence": "exact", "title": "Exact", "description": "Exact", "created_at": "2026-01-01T00:00:00Z"}],
                "findings": [{"id": self.ids["finding"], "analysis_run_id": self.run_id, "kind": "conflict", "title": "Possession", "description": "Possession remains disputed.", "created_at": "2026-01-01T00:00:00Z"}],
                "tasks": [{"id": self.ids["task"], "analysis_run_id": self.run_id, "finding_id": self.ids["finding"], "title": "Request handover", "description": "Request record.", "status": "proposed", "created_at": "2026-01-01T00:00:00Z"}],
            }
            if table in data: rows = data[table]
            elif table == "analysis_citations":
                if params.get("target_type") == "eq.case_summary": rows = [{"id": str(uuid4()), "passage_id": self.passage_id, "quote": "Payment is recorded", "created_at": "2026-01-01T00:00:00Z"}]
                else:
                    parent = next((v for k,v in params.items() if k.endswith("_id") and k != "analysis_run_id"), "")
                    if parent.startswith("in.("):
                        parent_id = parent[4:-1].split(",")[0]
                        rows = [{"id": str(uuid4()), "passage_id": self.passage_id, "quote": "Possession remains disputed", "created_at": "2026-01-01T00:00:00Z"}]
                        # Repository expects the selected parent-column key.
                        column = next(k for k in params if k.endswith("_id") and k != "analysis_run_id")
                        rows[0][column] = parent_id
            elif table == "document_passages": rows = [{"id": self.passage_id, "document_id": self.doc_id, "page_number": 2, "passage_label": "Page 2, Passage 1"}]
            elif table == "documents": rows = [{"id": self.doc_id, "file_name": "seller-notice.pdf"}]
        return rows[0] if single and rows else (None if single else rows)


def test_review_overview_returns_grounded_grouped_latest_output() -> None:
    gateway = ReviewGateway()
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    overview = asyncio.run(get_overview(gateway, user, uuid4()))
    assert overview.analysis_run and str(overview.analysis_run.id) == gateway.run_id
    assert overview.lawyer_context == "Check possession records."
    assert overview.document_summaries[0].document_name == "seller-notice.pdf"
    assert overview.case_summary_citations[0].passage_label == "Page 2, Passage 1"
    assert len(overview.fields.pending) == 1 and len(overview.fields.confirmed) == 1
    assert overview.pending_tasks[0].status == "proposed"


def test_review_empty_state_before_first_completion() -> None:
    gateway = ReviewGateway(completed=False)
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    overview = asyncio.run(get_overview(gateway, user, uuid4()))
    assert overview.analysis_run is None and overview.case_summary is None
    assert overview.counts.pending_tasks == 0


def test_timeline_sorts_recognized_dates_then_unknown() -> None:
    gateway = ReviewGateway()
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    timeline = asyncio.run(get_timeline(gateway, user, uuid4()))
    assert [item.title for item in timeline] == ["Year", "Exact", "Month", "Unknown"]
