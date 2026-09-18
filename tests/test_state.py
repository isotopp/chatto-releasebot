from pathlib import Path

import pytest

from chatto_releasebot.state import PendingAttempt, State, StateError, StateStore


def test_state_survives_a_new_store_and_keeps_pending_attempt(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)

    with store.locked():
        store.save(State(announced_version="0.4.24"))
        store.save(
            State(
                announced_version="0.4.24",
                pending=PendingAttempt(
                    version="0.5.0-beta.1",
                    release_url="https://github.com/chattocorp/chatto/releases/tag/v0.5.0-beta.1",
                    body="announcement",
                ),
            )
        )

    assert StateStore(path).load() == State(
        announced_version="0.4.24",
        pending=PendingAttempt(
            version="0.5.0-beta.1",
            release_url="https://github.com/chattocorp/chatto/releases/tag/v0.5.0-beta.1",
            body="announcement",
        ),
    )


def test_corrupt_state_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"announced_version": 42}', encoding="utf-8")

    with pytest.raises(StateError, match="corrupt"):
        StateStore(path).load()
