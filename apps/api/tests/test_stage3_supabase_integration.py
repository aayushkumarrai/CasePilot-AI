"""Opt-in verification of the applied Stage 3 analysis lifecycle RPCs.

Run only against a disposable owned case that already has a ready passage:
RUN_SUPABASE_INTEGRATION_TESTS=1 STAGE3_TEST_ACCESS_TOKEN=... \
STAGE3_TEST_CASE_ID=... STAGE3_TEST_PASSAGE_ID=... uv run pytest -m integration
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings

pytestmark = pytest.mark.integration


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"{name} is required for live Stage 3.1 integration testing")
    return value


@pytest.mark.integration
def test_analysis_lifecycle_persists_a_cited_fixture_output() -> None:
    if os.getenv("RUN_SUPABASE_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_SUPABASE_INTEGRATION_TESTS=1 to run live Supabase integration tests")
    settings = Settings()
    if not settings.supabase_is_configured:
        pytest.skip("Supabase configuration is required")

    token = _required("STAGE3_TEST_ACCESS_TOKEN")
    case_id = _required("STAGE3_TEST_CASE_ID")
    passage_id = _required("STAGE3_TEST_PASSAGE_ID")
    headers = {"apikey": settings.supabase_anon_key or "", "Authorization": f"Bearer {token}"}
    ref = uuid4().hex
    base_url = settings.supabase_url or ""

    with httpx.Client(base_url=base_url, headers=headers, timeout=20) as client:
        started = client.post(
            "/rest/v1/rpc/start_analysis_run_with_activity",
            json={"p_case_id": case_id, "p_lawyer_context": "  Verify payment records.  "},
        )
        assert started.status_code == 200, started.text
        run = started.json()[0]
        assert run["status"] == "queued"
        assert run["lawyer_context_snapshot"] == "Verify payment records."

        processing = client.post(
            "/rest/v1/rpc/mark_analysis_run_processing_with_activity",
            json={"p_analysis_run_id": run["id"]},
        )
        assert processing.status_code == 200, processing.text
        assert processing.json()[0]["status"] == "processing"

        completed = client.post(
            "/rest/v1/rpc/complete_analysis_run_with_outputs",
            json={
                "p_analysis_run_id": run["id"],
                "p_case_summary": "Integration-test fixture summary.",
                "p_case_fields": [
                    {
                        "ref": ref,
                        "field_key": "fixture_field",
                        "label": "Fixture field",
                        "value": "Verified from the supplied passage.",
                    }
                ],
                "p_citations": [
                    {
                        "target_type": "case_summary",
                        "target_ref": "case_summary",
                        "passage_id": passage_id,
                        "quote": "Fixture citation quote.",
                    },
                    {
                        "target_type": "case_field",
                        "target_ref": ref,
                        "passage_id": passage_id,
                        "quote": "Fixture citation quote.",
                    }
                ],
            },
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()[0]["status"] == "completed"

        fields = client.get(
            "/rest/v1/case_fields",
            params={"select": "id,analysis_run_id,value", "analysis_run_id": f"eq.{run['id']}"},
        )
        assert fields.status_code == 200, fields.text
        assert len(fields.json()) == 1
        citations = client.get(
            "/rest/v1/analysis_citations",
            params={"select": "case_field_id,passage_id", "case_field_id": f"eq.{fields.json()[0]['id']}"},
        )
        assert citations.status_code == 200, citations.text
        assert citations.json()[0]["passage_id"] == passage_id

        summary_citations = client.get(
            "/rest/v1/analysis_citations",
            params={
                "select": "analysis_run_id,passage_id,target_type",
                "analysis_run_id": f"eq.{run['id']}",
                "target_type": "eq.case_summary",
            },
        )
        assert summary_citations.status_code == 200, summary_citations.text
        assert summary_citations.json() == [
            {
                "analysis_run_id": run["id"],
                "passage_id": passage_id,
                "target_type": "case_summary",
            }
        ]
