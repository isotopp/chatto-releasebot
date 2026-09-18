from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StateError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingAttempt:
    version: str
    release_url: str
    body: str


@dataclass(frozen=True)
class State:
    announced_version: str | None = None
    pending: PendingAttempt | None = None


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_name(path.name + ".lock")

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def load(self) -> State:
        if not self.path.exists():
            return State()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"state file is corrupt: {self.path}") from exc
        return _state_from_json(payload)

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new_path = self.path.with_suffix(".new")
        try:
            new_path.write_text(
                json.dumps(_state_to_json(state), sort_keys=True) + "\n",
                encoding="utf-8",
            )
            new_path.replace(self.path)
        except OSError as exc:
            raise StateError(f"could not write state file: {self.path}") from exc


def _state_to_json(state: State) -> dict[str, Any]:
    return {
        "announced_version": state.announced_version,
        "pending": (
            {
                "version": state.pending.version,
                "release_url": state.pending.release_url,
                "body": state.pending.body,
            }
            if state.pending
            else None
        ),
    }


def _state_from_json(payload: object) -> State:
    if not isinstance(payload, dict):
        raise StateError("state file is corrupt: expected an object")
    announced_version = payload.get("announced_version")
    if announced_version is not None and not isinstance(announced_version, str):
        raise StateError("state file is corrupt: announced_version must be a string")

    pending_payload = payload.get("pending")
    if pending_payload is None:
        return State(announced_version=announced_version)
    if not isinstance(pending_payload, dict):
        raise StateError("state file is corrupt: pending must be an object")
    version = pending_payload.get("version")
    release_url = pending_payload.get("release_url")
    body = pending_payload.get("body")
    if not all(
        isinstance(value, str) and value for value in (version, release_url, body)
    ):
        raise StateError(
            "state file is corrupt: pending fields must be non-empty strings"
        )
    return State(
        announced_version=announced_version,
        pending=PendingAttempt(version=version, release_url=release_url, body=body),
    )
