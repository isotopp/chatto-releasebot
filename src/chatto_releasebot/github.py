from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class ReleasePending(RuntimeError):
    pass


@dataclass(frozen=True)
class Release:
    tag: str
    url: str
    body: str


class GitHubReleaseClient:
    def __init__(
        self,
        repository_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.client = client or httpx.Client(timeout=15.0)
        self.repository_url = repository_url.rstrip("/")

    def get_release(self, version: str) -> Release:
        tag = f"v{version}"
        try:
            response = self.client.get(
                f"{self.repository_url}/releases/tags/{tag}",
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "chatto-releasebot",
                },
            )
        except httpx.HTTPError as exc:
            raise ReleasePending(
                "matching GitHub release could not be fetched"
            ) from exc

        if not response.is_success:
            raise ReleasePending(
                f"matching GitHub release returned HTTP {response.status_code}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise ReleasePending(
                "matching GitHub release returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ReleasePending("matching GitHub release returned an invalid object")
        if payload.get("tag_name") != tag or payload.get("draft") is True:
            raise ReleasePending("matching GitHub release is missing or not published")

        url = payload.get("html_url")
        body = payload.get("body", "")
        if not isinstance(url, str) or not url or not isinstance(body, str):
            raise ReleasePending("matching GitHub release is missing its URL or notes")
        return Release(tag=tag, url=url, body=body)
