from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseError
from app.main import app


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowGateway:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        self.case_id = str(uuid4())
        self.field_id = str(uuid4())
        self.party_id = str(uuid4())
        self.ai_task_id = str(uuid4())
        self.field = {"id": self.field_id, "field_key": "payment", "label": "Payment", "value": "INR 500000", "reviewed_value": None, "status": "pending", "reviewed_at": None}
        self.party = {"id": self.party_id, "name": "Rao", "role": "Buyer", "reviewed_name": None, "reviewed_role": None, "status": "pending", "reviewed_at": None}
        self.ai_task = {"id": self.ai_task_id, "title": "Request receipt", "description": "Request the payment receipt.", "status": "proposed", "updated_at": now()}
        self.manual_tasks: dict[str, dict] = {}
        self.activities: list[dict] = []

    async def close(self) -> None:
        return None

    async def select(self, table: str, params: dict[str, str], *, single: bool = False):
        record_id = params.get("id", "").removeprefix("eq.")
        rows: list[dict] = []
        if table == "manual_tasks":
            rows = list(self.manual_tasks.values())
            if record_id:
                rows = [task for task in rows if task["id"] == record_id]
        elif table == "tasks" and record_id == self.ai_task_id:
            rows = [self.ai_task]
        return rows[0] if single and rows else (None if single else rows)

    def event(self, action: str, task_id: str) -> None:
        self.activities.append({"action": action, "details": {"task_id": task_id}})

    async def rpc(self, function: str, payload: dict):
        if function == "review_case_field_with_activity":
            if payload["p_case_id"] != self.case_id or payload["p_field_id"] != self.field_id:
                return []
            action = payload["p_action"]
            if self.field["status"] == "rejected" or (action == "confirm" and self.field["status"] != "pending"):
                raise SupabaseError(400, {"code": "22023", "message": "Invalid field review action"})
            if action == "edit":
                self.field["reviewed_value"] = payload["p_reviewed_value"].strip()
                self.field["status"] = "confirmed"
            elif action == "confirm":
                self.field["status"] = "confirmed"
            else:
                self.field["status"] = "rejected"
            self.field["reviewed_at"] = now()
            self.activities.append({"action": f"field_{'edited' if action == 'edit' else action + 'ed'}", "details": {"field_id": self.field_id}})
            return [self.field]
        if function == "review_case_party_with_activity":
            if payload["p_case_id"] != self.case_id or payload["p_party_id"] != self.party_id:
                return []
            action = payload["p_action"]
            if action == "edit":
                self.party["reviewed_name"] = payload["p_reviewed_name"] or self.party["reviewed_name"]
                self.party["reviewed_role"] = payload["p_reviewed_role"] or self.party["reviewed_role"]
                self.party["status"] = "confirmed"
            elif action == "confirm":
                self.party["status"] = "confirmed"
            else:
                self.party["status"] = "rejected"
            self.party["reviewed_at"] = now()
            return [self.party]
        if function == "create_manual_task_with_activity":
            if payload["p_case_id"] != self.case_id:
                return []
            task = {"id": str(uuid4()), "case_id": self.case_id, "title": payload["p_title"], "description": payload["p_description"], "status": "proposed", "created_at": now(), "updated_at": now()}
            self.manual_tasks[task["id"]] = task
            self.event("manual_task_created", task["id"])
            return [task]
        if function == "update_manual_task_with_activity":
            task = self.manual_tasks.get(payload["p_task_id"])
            if not task:
                return []
            new_status = payload.get("p_new_status")
            if new_status:
                allowed = {("proposed", "approved"): "task_approved", ("proposed", "rejected"): "task_rejected", ("approved", "done"): "task_completed"}
                action = allowed.get((task["status"], new_status))
                if not action:
                    raise SupabaseError(400, {"code": "22023", "message": "Invalid task status transition"})
                task["status"] = new_status
                self.event(action, task["id"])
            else:
                if task["status"] not in {"proposed", "approved"}:
                    raise SupabaseError(400, {"code": "22023", "message": "Only open manual tasks can be edited"})
                task["title"] = payload.get("p_title") or task["title"]
                task["description"] = payload.get("p_description") or task["description"]
                self.event("manual_task_updated", task["id"])
            task["updated_at"] = now()
            return [task]
        if function == "transition_ai_task_with_activity":
            if payload["p_task_id"] != self.ai_task_id:
                return []
            new_status = payload["p_new_status"]
            allowed = {("proposed", "approved"): "task_approved", ("proposed", "rejected"): "task_rejected", ("approved", "done"): "task_completed"}
            action = allowed.get((self.ai_task["status"], new_status))
            if not action:
                raise SupabaseError(400, {"code": "22023", "message": "Invalid task status transition"})
            self.ai_task["status"] = new_status
            self.ai_task["updated_at"] = now()
            self.event(action, self.ai_task_id)
            return [self.ai_task]
        raise AssertionError(function)


def configured_client():
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="token")
    gateway = WorkflowGateway(user)

    async def current_user() -> CurrentUser:
        return user

    async def current_gateway():
        yield gateway

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_user_gateway] = current_gateway
    return TestClient(app), gateway


def test_field_and_party_review_preserve_ai_suggestions() -> None:
    client, gateway = configured_client()
    try:
        edited = client.patch(f"/v1/cases/{gateway.case_id}/fields/{gateway.field_id}", json={"action": "edit", "value": "INR 475000"})
        assert edited.status_code == 200
        assert edited.json()["suggested_value"] == "INR 500000"
        assert edited.json()["reviewed_value"] == "INR 475000"
        assert edited.json()["value"] == "INR 475000"
        party = client.patch(f"/v1/cases/{gateway.case_id}/parties/{gateway.party_id}", json={"action": "edit", "role": "Purchaser"})
        assert party.status_code == 200
        assert party.json()["suggested_role"] == "Buyer"
        assert party.json()["role"] == "Purchaser"
        rejected = client.patch(f"/v1/cases/{gateway.case_id}/fields/{gateway.field_id}", json={"action": "reject"})
        assert rejected.status_code == 200
        terminal = client.patch(f"/v1/cases/{gateway.case_id}/fields/{gateway.field_id}", json={"action": "edit", "value": "INR 400000"})
        assert terminal.status_code == 422
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_manual_tasks_and_ai_status_transitions() -> None:
    client, gateway = configured_client()
    try:
        created = client.post(f"/v1/cases/{gateway.case_id}/tasks", json={"title": "Call buyer", "description": "Clarify possession date."})
        assert created.status_code == 201 and created.json()["source"] == "manual"
        task_id = created.json()["id"]
        edited = client.patch(f"/v1/tasks/{task_id}", json={"title": "Call buyer representative"})
        assert edited.status_code == 200 and edited.json()["title"] == "Call buyer representative"
        approved = client.patch(f"/v1/tasks/{task_id}", json={"status": "approved"})
        assert approved.status_code == 200 and approved.json()["status"] == "approved"
        completed = client.patch(f"/v1/tasks/{task_id}", json={"status": "done"})
        assert completed.status_code == 200 and completed.json()["status"] == "done"
        invalid = client.patch(f"/v1/tasks/{task_id}", json={"status": "approved"})
        assert invalid.status_code == 422
        ai_edit = client.patch(f"/v1/tasks/{gateway.ai_task_id}", json={"title": "Rewrite AI task"})
        assert ai_edit.status_code == 422
        ai_approved = client.patch(f"/v1/tasks/{gateway.ai_task_id}", json={"status": "approved"})
        assert ai_approved.status_code == 200 and ai_approved.json()["source"] == "ai"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_workflow_rejects_missing_or_unowned_records() -> None:
    client, gateway = configured_client()
    try:
        missing = client.patch(f"/v1/cases/{gateway.case_id}/fields/{uuid4()}", json={"action": "confirm"})
        assert missing.status_code == 404
        invalid_payload = client.post(f"/v1/cases/{gateway.case_id}/tasks", json={"title": " ", "description": "x"})
        assert invalid_payload.status_code == 422
        unknown_task = client.patch(f"/v1/tasks/{uuid4()}", json={"status": "approved"})
        assert unknown_task.status_code == 404
    finally:
        client.close()
        app.dependency_overrides.clear()
