from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.main import app
from app.modules.documents import service as document_service
from app.modules.documents.parser import extract_passages


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentGateway:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        self.cases: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.passages: dict[str, list[dict]] = {}
        self.objects: dict[str, bytes] = {}

    async def select(self, table: str, params: dict[str, str], *, single: bool = False):
        if table == "cases":
            rows = list(self.cases.values())
            case_id = params.get("id")
            if case_id:
                rows = [row for row in rows if row["id"] == case_id.removeprefix("eq.")]
            if params.get("archived_at") == "is.null":
                rows = [row for row in rows if row["archived_at"] is None]
        elif table == "documents":
            rows = list(self.documents.values())
            if "id" in params:
                rows = [row for row in rows if row["id"] == params["id"].removeprefix("eq.")]
            if "case_id" in params:
                rows = [row for row in rows if row["case_id"] == params["case_id"].removeprefix("eq.")]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
        elif table == "document_passages":
            rows = self.passages.get(params["document_id"].removeprefix("eq."), [])
        else:
            rows = []
        return rows[0] if single and rows else (None if single else rows)

    async def create_signed_upload_url(self, bucket: str, storage_path: str, expires_in: int = 3600) -> str:
        return f"https://storage.example/upload/{storage_path}"

    async def object_exists(self, bucket: str, storage_path: str) -> bool:
        return storage_path in self.objects

    async def download_object(self, bucket: str, storage_path: str) -> bytes:
        return self.objects[storage_path]

    async def create_signed_read_url(self, bucket: str, storage_path: str, expires_in: int = 3600) -> str:
        return f"https://storage.example/read/{storage_path}"

    async def rpc(self, function: str, payload: dict):
        if function == "register_document_with_activity":
            row = {
                "id": str(uuid4()), "case_id": payload["p_case_id"], "file_name": payload["p_file_name"],
                "content_type": payload["p_content_type"], "size_bytes": payload["p_size_bytes"],
                "storage_path": payload["p_storage_path"], "status": payload["p_status"], "error_message": payload["p_error_message"],
                "created_at": now(), "updated_at": now(),
            }
            self.documents[row["id"]] = row
            return [row]
        document = self.documents.get(payload["p_document_id"])
        if not document:
            return []
        if function == "start_document_processing_with_activity":
            if document["status"] not in {"uploaded", "failed"}:
                return []
            document["status"] = "processing"
        elif function == "complete_document_processing_with_activity":
            document["status"] = "ready"
            self.passages[document["id"]] = [
                {"id": str(uuid4()), **passage, "created_at": now()} for passage in payload["p_passages"]
            ]
        elif function == "fail_document_processing_with_activity":
            document["status"] = "failed"
            document["error_message"] = payload["p_error_message"]
        document["updated_at"] = now()
        return [document]


def create_case(gateway: DocumentGateway) -> dict:
    row = {"id": str(uuid4()), "external_case_id": "PROP-002", "case_name": "Rao v Mehta", "status": "draft", "created_at": now(), "updated_at": now(), "archived_at": None}
    gateway.cases[row["id"]] = row
    return row


def test_document_upload_registration_and_passage_reading(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="test-token")
    gateway = DocumentGateway(user)
    case = create_case(gateway)

    async def fake_process(document_id: str, access_token: str, settings, already_processing: bool = False) -> None:
        if already_processing:
            document = gateway.documents[document_id]
        else:
            started = await gateway.rpc(
                "start_document_processing_with_activity",
                {"p_document_id": document_id, "p_action": "document_processing_started"},
            )
            document = started[0]
        passages = extract_passages(gateway.objects[document["storage_path"]], document["content_type"])
        await gateway.rpc(
            "complete_document_processing_with_activity",
            {"p_document_id": document_id, "p_passages": [passage.__dict__ for passage in passages]},
        )

    monkeypatch.setattr(document_service, "process_document", fake_process)

    async def user_override(): return user
    async def gateway_override(): yield gateway
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    try:
        with TestClient(app) as client:
            upload = client.post(f"/v1/cases/{case['id']}/documents/upload-url", json={"file_name": "evidence.txt", "content_type": "text/plain", "size_bytes": 15})
            assert upload.status_code == 200
            storage_path = upload.json()["storage_path"]
            gateway.objects[storage_path] = b"Payment receipt\n\nPossession pending"
            registered = client.post(f"/v1/cases/{case['id']}/documents", json={"file_name": "evidence.txt", "content_type": "text/plain", "size_bytes": 15, "storage_path": storage_path})
            assert registered.status_code == 201
            assert registered.json()["status"] == "uploaded"
            detail = client.get(f"/v1/documents/{registered.json()['id']}")
            assert detail.status_code == 200
            assert detail.json()["status"] == "ready"
            assert detail.json()["passages"][0]["passage_label"] == "Passage 1"
    finally:
        app.dependency_overrides.clear()


def test_failed_document_retry_returns_processing(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="test-token")
    gateway = DocumentGateway(user)
    case = create_case(gateway)
    document_id = str(uuid4())
    storage_path = f"{user.id}/{case['id']}/retry.txt"
    gateway.objects[storage_path] = b"Recovered evidence"
    gateway.documents[document_id] = {
        "id": document_id, "case_id": case["id"], "file_name": "retry.txt", "content_type": "text/plain",
        "size_bytes": 18, "storage_path": storage_path, "status": "failed", "error_message": "Temporary parsing failure",
        "created_at": now(), "updated_at": now(),
    }

    async def fake_process(document_id: str, access_token: str, settings, already_processing: bool = False) -> None:
        document = gateway.documents[document_id]
        passages = extract_passages(gateway.objects[document["storage_path"]], document["content_type"])
        await gateway.rpc("complete_document_processing_with_activity", {"p_document_id": document_id, "p_passages": [passage.__dict__ for passage in passages]})

    monkeypatch.setattr(document_service, "process_document", fake_process)
    async def user_override(): return user
    async def gateway_override(): yield gateway
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    try:
        with TestClient(app) as client:
            response = client.post(f"/v1/documents/{document_id}/retry")
            assert response.status_code == 202
            assert response.json()["status"] == "processing"
            assert client.get(f"/v1/documents/{document_id}").json()["status"] == "ready"
    finally:
        app.dependency_overrides.clear()


def test_unsupported_document_is_visible_without_storage_upload() -> None:
    user = CurrentUser(id=uuid4(), email="lawyer@example.com", access_token="test-token")
    gateway = DocumentGateway(user)
    case = create_case(gateway)

    async def user_override(): return user
    async def gateway_override(): yield gateway
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_user_gateway] = gateway_override
    try:
        with TestClient(app) as client:
            response = client.post(f"/v1/cases/{case['id']}/documents", json={"file_name": "photo.jpg", "content_type": "image/jpeg", "size_bytes": 10, "storage_path": None})
            assert response.status_code == 201
            assert response.json()["status"] == "unsupported"
            assert "Supported formats" in response.json()["error_message"]
    finally:
        app.dependency_overrides.clear()
