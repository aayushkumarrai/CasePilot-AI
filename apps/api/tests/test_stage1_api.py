from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseError
from app.main import app


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeGateway:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        self.profiles = {
            str(user.id): {
                "id": str(user.id),
                "email": user.email,
                "display_name": "Demo Lawyer",
                "created_at": now(),
            }
        }
        self.cases: dict[str, dict] = {}
        self.activities: list[dict] = []

    async def select(self, table: str, params: dict[str, str], *, single: bool = False):
        if table == "profiles":
            rows = [self.profiles[str(self.user.id)]] if str(self.user.id) in self.profiles else []
        elif table == "cases":
            rows = list(self.cases.values())
            if params.get("archived_at") == "is.null":
                rows = [row for row in rows if row["archived_at"] is None]
            case_filter = params.get("id")
            if case_filter:
                rows = [row for row in rows if row["id"] == case_filter.removeprefix("eq.")]
            rows.sort(key=lambda row: row["updated_at"], reverse=True)
        elif table == "activity_events":
            ids = params.get("case_id", "").removeprefix("in.(").removesuffix(")").split(",")
            rows = [row for row in self.activities if row["case_id"] in ids]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
        else:
            rows = []
        return rows[0] if single and rows else (None if single else rows)

    async def rpc(self, function: str, payload: dict):
        if function == "create_case_with_activity":
            active = [
                row for row in self.cases.values()
                if row["external_case_id"] == payload["p_external_case_id"] and row["archived_at"] is None
            ]
            if active:
                raise SupabaseError(409, {"code": "23505"})
            case = {
                "id": str(uuid4()),
                "external_case_id": payload["p_external_case_id"],
                "case_name": payload["p_case_name"],
                "status": "draft",
                "created_at": now(),
                "updated_at": now(),
                "archived_at": None,
            }
            self.cases[case["id"]] = case
            self._event(case["id"], "case_created", {"case_id": case["external_case_id"]})
            return [case]
        case_id = payload["p_case_id"]
        case = self.cases.get(case_id)
        if not case:
            return []
        if function == "update_case_with_activity":
            if case["archived_at"] is not None:
                return []
            duplicate = [
                row for row in self.cases.values()
                if row["id"] != case_id and row["external_case_id"] == payload["p_external_case_id"] and row["archived_at"] is None
            ]
            if duplicate:
                raise SupabaseError(409, {"code": "23505"})
            case["external_case_id"] = payload["p_external_case_id"]
            case["case_name"] = payload["p_case_name"]
            case["updated_at"] = now()
            self._event(case_id, "case_updated", {"changed_fields": payload["p_changed_fields"]})
        elif function == "archive_case_with_activity":
            if case["archived_at"] is not None:
                return []
            case["archived_at"] = now()
            case["updated_at"] = now()
            self._event(case_id, "case_archived", {})
        elif function == "restore_case_with_activity":
            if case["archived_at"] is None:
                return []
            duplicate = [
                row for row in self.cases.values()
                if row["id"] != case_id and row["external_case_id"] == case["external_case_id"] and row["archived_at"] is None
            ]
            if duplicate:
                raise SupabaseError(409, {"code": "23505"})
            case["archived_at"] = None
            case["updated_at"] = now()
            self._event(case_id, "case_restored", {})
        return [case]

    def _event(self, case_id: str, action: str, details: dict) -> None:
        self.activities.append(
            {"id": str(uuid4()), "case_id": case_id, "action": action, "actor_type": "user", "details": details, "created_at": now()}
        )


@pytest.fixture
def client_and_gateway():
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="test-token")
    gateway = FakeGateway(user)

    async def current_user_override() -> CurrentUser:
        return user

    async def gateway_override():
        yield gateway

    app.dependency_overrides[get_current_user] = current_user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    with TestClient(app) as client:
        yield client, gateway, user
    app.dependency_overrides.clear()


def create_case(client: TestClient, case_id: str = "PROP-001") -> dict:
    response = client.post("/v1/cases", json={"case_id": case_id, "case_name": "Rao v Mehta"})
    assert response.status_code == 201
    return response.json()


def test_health_is_live_without_supabase_configuration() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_rejects_missing_bearer_token() -> None:
    response = TestClient(app).get("/v1/cases")
    assert response.status_code == 401


def test_readiness_requires_supabase_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(supabase_url=None, supabase_anon_key=None))
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503


def test_me_uses_authenticated_profile(client_and_gateway) -> None:
    client, _, user = client_and_gateway
    response = client.get("/v1/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_create_list_and_dashboard(client_and_gateway) -> None:
    client, _, _ = client_and_gateway
    created = create_case(client)
    cases = client.get("/v1/cases")
    dashboard = client.get("/v1/dashboard")
    assert cases.status_code == 200
    assert cases.json()[0]["id"] == created["id"]
    assert dashboard.json()["metrics"]["total_cases"] == 1
    assert dashboard.json()["recent_activity"][0]["action"] == "case_created"


def test_duplicate_active_case_id_returns_conflict(client_and_gateway) -> None:
    client, _, _ = client_and_gateway
    create_case(client)
    duplicate = client.post("/v1/cases", json={"case_id": "PROP-001", "case_name": "Second case"})
    assert duplicate.status_code == 409


def test_update_archive_and_restore_case(client_and_gateway) -> None:
    client, _, _ = client_and_gateway
    created = create_case(client)
    case_id = created["id"]
    update = client.patch(f"/v1/cases/{case_id}", json={"case_id": "PROP-002", "case_name": "Rao v Mehta Updated"})
    assert update.status_code == 200
    assert update.json()["case_id"] == "PROP-002"
    assert client.delete(f"/v1/cases/{case_id}").status_code == 204
    assert client.get("/v1/cases").json() == []
    assert client.get(f"/v1/cases/{case_id}").status_code == 404
    restored = client.post(f"/v1/cases/{case_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_empty_case_update_is_rejected(client_and_gateway) -> None:
    client, _, _ = client_and_gateway
    created = create_case(client)
    response = client.patch(f"/v1/cases/{created['id']}", json={})
    assert response.status_code == 422
