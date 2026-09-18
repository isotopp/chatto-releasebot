from __future__ import annotations

import re
from typing import Any

import httpx

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SERVER_DISCOVERY_PATH = "/chatto.api.v1.ServerDiscoveryService/GetServer"


class ChattoError(RuntimeError):
    pass


class ChattoClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=15.0)

    def discover_version(self) -> str:
        try:
            response = self.client.get(self.base_url + SERVER_DISCOVERY_PATH)
        except httpx.HTTPError as exc:
            raise ChattoError("server version discovery request failed") from exc

        if not response.is_success:
            raise ChattoError(
                f"server version discovery returned HTTP {response.status_code}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise ChattoError("server version discovery returned invalid JSON") from exc

        version = (
            payload.get("profile", {}).get("version")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
            raise ChattoError(
                "server version discovery returned no valid profile.version"
            )
        return version
