from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


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
    ) -> Config:
        if values is None:
            if not load_dotenv("./.env") and not load_dotenv(
                Path("~/.chatto-releasebot.env").expanduser()
            ):
                raise ConfigError("environment variables not found")
            environment = os.environ
        else:
            environment = values

        required = (
            "ANNOUNCEMENTS_SERVER_BASE_URL",
            "ANNOUNCEMENTS_API_KEY",
            "ANNOUNCEMENTS_ROOM_ID",
        )
        missing = [name for name in required if not environment.get(name, "").strip()]
        if missing:
            raise ConfigError(f"missing required configuration: {', '.join(missing)}")

        server_url = environment["ANNOUNCEMENTS_SERVER_BASE_URL"].strip().rstrip("/")
        parsed = urlsplit(server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("ANNOUNCEMENTS_SERVER_BASE_URL must be an HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ConfigError(
                "ANNOUNCEMENTS_SERVER_BASE_URL must not contain credentials"
            )

        return cls(
            server_base_url=server_url,
            api_key=environment["ANNOUNCEMENTS_API_KEY"].strip(),
            room_id=environment["ANNOUNCEMENTS_ROOM_ID"].strip(),
            user_id=environment.get("ANNOUNCEMENTS_USER_ID") or None,
            user_name=environment.get("ANNOUNCEMENTS_USER_NAME") or None,
            state_path=Path("~/.local/state/chatto-releasebot/state.json").expanduser(),
        )
