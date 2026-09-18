from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    server_base_url: str
    api_key: str
    room_id: str
    user_id: str | None
    user_name: str | None
    state_path: Path

    @classmethod
    def from_env(
        cls,
        values: Mapping[str, str] | None = None,
        state_path: Path | None = None,
    ) -> Config:
        if values is None:
            file_values = {
                key: value
                for key, value in dotenv_values().items()
                if value is not None
            }
            environment = dict(file_values)
            environment.update(os.environ)
        else:
            environment = dict(values)

        required = {
            "ANNOUNCEMENTS_SERVER_BASE_URL": environment.get(
                "ANNOUNCEMENTS_SERVER_BASE_URL", ""
            ),
            "ANNOUNCEMENTS_API_KEY": environment.get("ANNOUNCEMENTS_API_KEY", ""),
            "ANNOUNCEMENTS_ROOM_ID": environment.get("ANNOUNCEMENTS_ROOM_ID", ""),
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ConfigError(f"missing required configuration: {', '.join(missing)}")

        server_url = required["ANNOUNCEMENTS_SERVER_BASE_URL"].strip().rstrip("/")
        parsed = urlsplit(server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("ANNOUNCEMENTS_SERVER_BASE_URL must be an HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ConfigError(
                "ANNOUNCEMENTS_SERVER_BASE_URL must not contain credentials"
            )

        return cls(
            server_base_url=server_url,
            api_key=required["ANNOUNCEMENTS_API_KEY"].strip(),
            room_id=required["ANNOUNCEMENTS_ROOM_ID"].strip(),
            user_id=environment.get("ANNOUNCEMENTS_USER_ID") or None,
            user_name=environment.get("ANNOUNCEMENTS_USER_NAME") or None,
            state_path=state_path or default_state_path(environment),
        )


def default_state_path(values: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if values is None else values
    explicit = environment.get("CHATTO_RELEASEBOT_STATE_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    state_home = environment.get("XDG_STATE_HOME", "").strip()
    if state_home:
        return Path(state_home).expanduser() / "chatto-releasebot" / "state.json"
    home = Path(environment.get("HOME", str(Path.home()))).expanduser()
    return home / ".local" / "state" / "chatto-releasebot" / "state.json"
