from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class SupabaseError(Exception):
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self.payload = payload
        super().__init__(str(payload))


class SupabaseGateway:
    """Small request-scoped REST client that preserves the caller's JWT for RLS."""

    def __init__(self, base_url: str, anon_key: str, access_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.anon_key = anon_key
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=15)

    async def close(self) -> None:
        await self.client.aclose()

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.anon_key}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        response = await self.client.request(
            method,
            f"{self.base_url}{path}",
            headers=self._headers(prefer=prefer),
            params=params,
            json=json,
        )
        if response.is_error:
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text}
            raise SupabaseError(response.status_code, payload)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def auth_user(self) -> dict[str, Any]:
        return await self._request("GET", "/auth/v1/user")

    async def select(
        self, table: str, params: dict[str, str], *, single: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        payload = await self._request("GET", f"/rest/v1/{table}", params=params)
        if not single:
            return payload
        return payload[0] if payload else None

    async def rpc(self, function: str, payload: dict[str, Any]) -> Any:
        return await self._request(
            "POST", f"/rest/v1/rpc/{function}", json=payload, prefer="return=representation"
        )

    def _storage_path(self, path: str) -> str:
        return quote(path, safe="/")

    def _storage_url(self, signed_path: str) -> str:
        if signed_path.startswith("http"):
            return signed_path
        return f"{self.base_url}/storage/v1{signed_path}"

    async def create_signed_upload_url(self, bucket: str, storage_path: str, expires_in: int = 3600) -> str:
        payload = await self._request(
            "POST",
            f"/storage/v1/object/upload/sign/{bucket}/{self._storage_path(storage_path)}",
            json={"expiresIn": expires_in},
        )
        signed_path = payload.get("url") if isinstance(payload, dict) else None
        if not signed_path:
            raise SupabaseError(502, {"message": "Storage did not return an upload URL"})
        return self._storage_url(signed_path)

    async def create_signed_read_url(self, bucket: str, storage_path: str, expires_in: int = 3600) -> str:
        payload = await self._request(
            "POST",
            f"/storage/v1/object/sign/{bucket}/{self._storage_path(storage_path)}",
            json={"expiresIn": expires_in},
        )
        signed_path = payload.get("signedURL") if isinstance(payload, dict) else None
        if not signed_path:
            raise SupabaseError(502, {"message": "Storage did not return a read URL"})
        return self._storage_url(signed_path)

    async def object_exists(self, bucket: str, storage_path: str) -> bool:
        try:
            await self._request(
                "GET", f"/storage/v1/object/info/{bucket}/{self._storage_path(storage_path)}"
            )
        except SupabaseError as exc:
            if exc.status_code == 404:
                return False
            raise
        return True

    async def download_object(self, bucket: str, storage_path: str) -> bytes:
        response = await self.client.get(
            f"{self.base_url}/storage/v1/object/{bucket}/{self._storage_path(storage_path)}",
            headers=self._headers(),
        )
        if response.is_error:
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text}
            raise SupabaseError(response.status_code, payload)
        return response.content

    async def ready(self) -> None:
        await self._request("GET", "/rest/v1/profiles", params={"select": "id", "limit": "1"})
