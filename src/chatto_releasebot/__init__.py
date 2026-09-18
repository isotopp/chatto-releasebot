from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from .chatto import ChattoClient, ChattoError
from .config import Config, ConfigError
from .formatting import compose_announcement
from .github import GitHubReleaseClient, ReleasePending
from .state import PendingAttempt, State, StateError, StateStore


def run_once(
    config: Config,
    *,
    chatto: Any | None = None,
    github: Any | None = None,
    state_store: StateStore | None = None,
    dry_run: bool = False,
) -> str:
    chatto = chatto or ChattoClient(config.server_base_url)
    github = github or GitHubReleaseClient()
    state_store = state_store or StateStore(config.state_path)

    if dry_run:
        state = state_store.load()
        observed_version = chatto.discover_version()
        if state.announced_version == observed_version and state.pending is None:
            return f"Observed version: {observed_version}\nAlready announced."
        release = github.get_release(observed_version)
        return (
            f"Observed version: {observed_version}\n\n"
            f"{compose_announcement(observed_version, release)}"
        )

    with state_store.locked():
        state = state_store.load()
        observed_version = chatto.discover_version()

        if state.pending is not None:
            user_id = _require_reconciliation_identity(config)
            pending = state.pending
            if chatto.room_has_announcement(
                config.room_id, config.api_key, user_id, pending.release_url
            ):
                state = State(announced_version=pending.version)
                state_store.save(state)
                if pending.version == observed_version:
                    return f"Observed version: {observed_version}\nPending post reconciled."
            else:
                chatto.create_message(config.room_id, pending.body, config.api_key)
                state_store.save(State(announced_version=pending.version))
                return f"Observed version: {observed_version}\nPending post delivered."

        if state.announced_version == observed_version:
            return f"Observed version: {observed_version}\nAlready announced."

        release = github.get_release(observed_version)
        body = compose_announcement(observed_version, release)
        user_id = _require_reconciliation_identity(config)
        if chatto.room_has_announcement(
            config.room_id, config.api_key, user_id, release.url
        ):
            state_store.save(State(announced_version=observed_version))
            return f"Observed version: {observed_version}\nExisting post reconciled."

        state_store.save(
            State(
                announced_version=state.announced_version,
                pending=PendingAttempt(
                    version=observed_version,
                    release_url=release.url,
                    body=body,
                ),
            )
        )
        chatto.create_message(config.room_id, body, config.api_key)
        state_store.save(State(announced_version=observed_version))
        return f"Observed version: {observed_version}\nAnnouncement posted.\n\n{body}"


def _require_reconciliation_identity(config: Config) -> str:
    if not config.user_id:
        raise ChattoError(
            "ANNOUNCEMENTS_USER_ID is required to verify room timeline access"
        )
    return config.user_id


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chatto-releasebot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the proposed post without changing state",
    )
    args = parser.parse_args(argv)
    try:
        config = Config.from_env()
        print(run_once(config, dry_run=args.dry_run))
    except (ConfigError, ChattoError, ReleasePending, StateError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
