from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.groq_client import GroqTemporaryError
from app.integrations.supabase_gateway import SupabaseError
from app.main import app
from app.modules.analysis import router as analysis_router_module
from app.modules.analysis import service as analysis_service
from app.modules.analysis.schemas import AnalysisResult


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisGateway:
    def __init__(self, user: CurrentUser, *, ready: bool = True) -> None:
        self.user = user
        self.case_id = str(uuid4())
        self.document_id = str(uuid4())
        self.passage_id = str(uuid4())
        self.case = {
            "id": self.case_id,
            "external_case_id": "PROP-ANALYSIS-001",
            "case_name": "Rao v Mehta",
            "status": "draft",
            "archived_at": None,
            "created_at": now(),
            "updated_at": now(),
        }
        self.ready = ready
        self.runs: dict[str, dict] = {}
        self.completed_payloads: list[dict] = []

    async def close(self) -> None:
        return None

    async def select(self, table: str, params: dict[str, str], *, single: bool = False):
        if table == "cases":
            rows = [self.case] if params.get("id") == f"eq.{self.case_id}" and self.case["archived_at"] is None else []
        elif table == "documents":
            rows = []
            if self.ready and params.get("case_id") == f"eq.{self.case_id}" and params.get("status") == "eq.ready":
                rows = [{"id": self.document_id, "case_id": self.case_id, "file_name": "evidence.txt", "content_type": "text/plain", "created_at": now()}]
        elif table == "document_passages":
            rows = [{"id": self.passage_id, "document_id": self.document_id, "sequence_number": 1, "page_number": None, "passage_label": "Passage 1", "content": "Buyer Rao paid INR 500000. Possession remains disputed."}]
        elif table == "analysis_runs":
            rows = list(self.runs.values())
            if params.get("case_id"):
                rows = [row for row in rows if row["case_id"] == params["case_id"].removeprefix("eq.")]
            if params.get("status"):
                rows = [row for row in rows if row["status"] == params["status"].removeprefix("eq.")]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            if params.get("limit"):
                rows = rows[: int(params["limit"])]
        else:
            rows = []
        return rows[0] if single and rows else (None if single else rows)

    async def rpc(self, function: str, payload: dict):
        if function == "start_analysis_run_with_activity":
            if any(row["status"] in {"queued", "processing"} for row in self.runs.values()):
                raise SupabaseError(409, {"code": "23505"})
            run_id = str(uuid4())
            context = payload["p_lawyer_context"]
            context = context.strip() if context else None
            run = {"id": run_id, "case_id": self.case_id, "status": "queued", "lawyer_context_snapshot": context, "case_summary": None, "error_message": None, "started_at": None, "completed_at": None, "created_at": now(), "updated_at": now()}
            self.runs[run_id] = run
            self.case["status"] = "processing"
            return [run]
        run = self.runs.get(payload["p_analysis_run_id"])
        if not run:
            return []
        if function == "mark_analysis_run_processing_with_activity":
            if run["status"] != "queued":
                return []
            run["status"] = "processing"
            run["started_at"] = now()
        elif function == "complete_analysis_run_with_outputs":
            if run["status"] != "processing":
                return []
            run["status"] = "completed"
            run["case_summary"] = payload["p_case_summary"]
            run["completed_at"] = now()
            self.case["status"] = "review"
            self.completed_payloads.append(payload)
        elif function == "fail_analysis_run_with_activity":
            if run["status"] not in {"queued", "processing"}:
                return []
            run["status"] = "failed"
            run["error_message"] = payload["p_error_message"]
            run["completed_at"] = now()
            self.case["status"] = "review" if any(item["status"] == "completed" for item in self.runs.values()) else "draft"
        run["updated_at"] = now()
        return [run]


def valid_result(gateway: AnalysisGateway) -> AnalysisResult:
    return AnalysisResult.model_validate({
        "case_summary": "Buyer Rao paid INR 500000 and possession remains disputed.",
        "document_summaries": [{"ref": "doc_1", "document_id": gateway.document_id, "summary": "Payment and possession are recorded."}],
        "case_fields": [], "case_parties": [], "timeline_events": [], "findings": [], "tasks": [],
        "citations": [
            {"target_type": "case_summary", "target_ref": "case_summary", "passage_id": gateway.passage_id, "quote": "Buyer Rao paid INR 500000."},
            {"target_type": "document_summary", "target_ref": "doc_1", "passage_id": gateway.passage_id, "quote": "Possession remains disputed."},
        ],
    })


class FakeGroqClient:
    result: AnalysisResult | None = None
    error: Exception | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def analyze_case(self, prompt):
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result

    async def close(self) -> None:
        return None


def configure(client: TestClient, gateway: AnalysisGateway, settings: Settings, monkeypatch) -> None:
    async def user_override() -> CurrentUser:
        return gateway.user

    async def gateway_override():
        yield gateway

    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    app.dependency_overrides[analysis_router_module.get_settings] = lambda: settings
    monkeypatch.setattr(analysis_service, "SupabaseGateway", lambda *_: gateway)
    monkeypatch.setattr(analysis_service, "GroqClient", FakeGroqClient)


def test_analysis_starts_completes_and_polls_without_context_leak(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user)
    FakeGroqClient.result, FakeGroqClient.error = valid_result(gateway), None
    settings = Settings(supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key="key", groq_model="model")
    with TestClient(app) as client:
        configure(client, gateway, settings, monkeypatch)
        started = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={"lawyer_context": "  Focus on payment.  "})
        assert started.status_code == 202
        assert started.json()["status"] == "queued"
        status_response = client.get(f"/v1/cases/{gateway.case_id}/analysis")
        assert status_response.status_code == 200
        assert status_response.json()["run"]["status"] == "completed"
        assert status_response.json()["has_completed_outputs"] is True
        assert "lawyer_context" not in status_response.text
        assert gateway.completed_payloads[0]["p_case_summary"]
    app.dependency_overrides.clear()


def test_analysis_keeps_grounded_outputs_when_case_summary_is_unsupported(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user)
    result = valid_result(gateway).model_copy(deep=True)
    result.citations[0] = result.citations[0].model_copy(
        update={"quote": "This text is not present in the uploaded evidence."}
    )
    FakeGroqClient.result, FakeGroqClient.error = result, None
    settings = Settings(
        supabase_url="https://supabase.test",
        supabase_anon_key="anon",
        groq_api_key="key",
        groq_model="model",
    )

    with TestClient(app) as client:
        configure(client, gateway, settings, monkeypatch)
        started = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})

        assert started.status_code == 202
        status_response = client.get(f"/v1/cases/{gateway.case_id}/analysis")
        assert status_response.json()["run"]["status"] == "completed"
        payload = gateway.completed_payloads[0]
        assert payload["p_case_summary"] == ""
        assert payload["p_document_summaries"]
        assert all(
            citation["target_type"] != "case_summary"
            for citation in payload["p_citations"]
        )

    app.dependency_overrides.clear()


def test_analysis_status_is_empty_before_first_run(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user)
    settings = Settings(supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key="key", groq_model="model")
    with TestClient(app) as client:
        configure(client, gateway, settings, monkeypatch)
        response = client.get(f"/v1/cases/{gateway.case_id}/analysis")
        assert response.status_code == 200
        assert response.json() == {"run": None, "has_completed_outputs": False}
    app.dependency_overrides.clear()


def test_analysis_rejects_no_ready_evidence_and_missing_configuration(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user, ready=False)
    configured = Settings(supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key="key", groq_model="model")
    with TestClient(app) as client:
        configure(client, gateway, configured, monkeypatch)
        no_evidence = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})
        assert no_evidence.status_code == 422
        assert gateway.runs == {}
        gateway.ready = True
        app.dependency_overrides[analysis_router_module.get_settings] = lambda: Settings(
            supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key=None, groq_model=None
        )
        unconfigured = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})
        assert unconfigured.status_code == 503
    app.dependency_overrides.clear()


def test_analysis_rejects_archived_case_and_oversized_context(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user)
    settings = Settings(supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key="key", groq_model="model")
    with TestClient(app) as client:
        configure(client, gateway, settings, monkeypatch)
        too_long = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={"lawyer_context": "x" * 4001})
        assert too_long.status_code == 422
        assert gateway.runs == {}
        gateway.case["archived_at"] = now()
        archived = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})
        assert archived.status_code == 404
    app.dependency_overrides.clear()


def test_active_run_conflict_and_failed_rerun_preserves_completed_output(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = AnalysisGateway(user)
    settings = Settings(supabase_url="https://supabase.test", supabase_anon_key="anon", groq_api_key="key", groq_model="model")
    completed = {"id": str(uuid4()), "case_id": gateway.case_id, "status": "completed", "lawyer_context_snapshot": None, "case_summary": "Earlier summary", "error_message": None, "started_at": now(), "completed_at": now(), "created_at": "2020-01-01T00:00:00+00:00", "updated_at": now()}
    gateway.runs[completed["id"]] = completed
    FakeGroqClient.result, FakeGroqClient.error = None, GroqTemporaryError()
    with TestClient(app) as client:
        configure(client, gateway, settings, monkeypatch)
        rerun = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})
        assert rerun.status_code == 202
        failed = client.get(f"/v1/cases/{gateway.case_id}/analysis").json()
        assert failed["run"]["status"] == "failed"
        assert failed["has_completed_outputs"] is True
        assert gateway.case["status"] == "review"
        gateway.runs[str(uuid4())] = {**completed, "id": str(uuid4()), "status": "processing", "created_at": now()}
        conflict = client.post(f"/v1/cases/{gateway.case_id}/analysis", json={})
        assert conflict.status_code == 409
    app.dependency_overrides.clear()
