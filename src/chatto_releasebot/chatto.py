from __future__ import annotations

import re
from typing import Any

import httpx

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
CONNECT_PATH = "/api/connect"
SERVER_DISCOVERY_PATH = "/chatto.discovery.v1.ServerDiscoveryService/GetServer"


class ChattoError(RuntimeError):
    pass


class DeliveryUncertain(ChattoError):
    pass


class ChattoClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=15.0)

    def discover_version(self) -> str:
        try:
            response = self.client.post(
                self.base_url + CONNECT_PATH + SERVER_DISCOVERY_PATH, json={}
            )
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

    def create_message(self, room_id: str, body: str, api_key: str) -> None:
        try:
            response = self.client.post(
                self.base_url
                + CONNECT_PATH
                + "/chatto.api.v1.MessageService/CreateMessage",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"roomId": room_id, "body": body},
            )
        except httpx.HTTPError as exc:
            raise DeliveryUncertain(
                "message delivery response was not received"
            ) from exc

        if not response.is_success:
            raise ChattoError(f"message delivery returned HTTP {response.status_code}")

        try:
            confirmation: Any = response.json()
        except ValueError as exc:
            raise DeliveryUncertain(
                "message delivery confirmation was invalid"
            ) from exc
        message = (
            confirmation.get("message") if isinstance(confirmation, dict) else None
        )
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("id"), str)
            or not message["id"]
        ):
            raise DeliveryUncertain("message delivery confirmation was missing")

    def room_has_announcement(
        self, room_id: str, api_key: str, user_id: str, release_url: str
    ) -> bool:
        before: str | None = None
        while True:
            payload: dict[str, Any] = {"roomId": room_id, "limit": 100}
            if before:
                payload["before"] = before
            try:
                response = self.client.post(
                    self.base_url
                    + CONNECT_PATH
                    + "/chatto.api.v1.RoomService/GetRoomEvents",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise ChattoError("room timeline read request failed") from exc
            if not response.is_success:
                raise ChattoError(
                    f"room timeline read returned HTTP {response.status_code}"
                )
            try:
                response_payload: Any = response.json()
            except ValueError as exc:
                raise ChattoError("room timeline read returned invalid JSON") from exc
            if not isinstance(response_payload, dict):
                raise ChattoError("room timeline read returned an invalid object")
            page = response_payload.get("page", response_payload)
            if not isinstance(page, dict) or not isinstance(
                page.get("events", []), list
            ):
                raise ChattoError("room timeline read returned an invalid page")
            if any(
                _event_matches(event, user_id, release_url) for event in page["events"]
            ):
                return True

            has_older = page.get("hasOlder", page.get("has_older", False))
            if not has_older:
                return False
            next_before = page.get("startCursor", page.get("start_cursor"))
            if (
                not isinstance(next_before, str)
                or not next_before
                or next_before == before
            ):
                raise ChattoError("room timeline read returned no usable older cursor")
            before = next_before


def _event_matches(event: object, user_id: str, release_url: str) -> bool:
    if not isinstance(event, dict):
        return False
    actor_id = event.get("actorId", event.get("actor_id"))
    message_posted = event.get("messagePosted", event.get("message_posted"))
    message = (
        message_posted.get("message") if isinstance(message_posted, dict) else None
    )
    if not isinstance(message, dict):
        message = event.get("message")
    if not isinstance(message, dict):
        return False
    actor_id = actor_id or message.get("actorId", message.get("actor_id"))
    body = message.get("body")
    return actor_id == user_id and isinstance(body, str) and release_url in body
