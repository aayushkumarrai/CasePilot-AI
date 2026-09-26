from __future__ import annotations

from typing import Any

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

    async def ready(self) -> None:
        await self._request("GET", "/rest/v1/profiles", params={"select": "id", "limit": "1"})
