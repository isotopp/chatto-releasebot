from pathlib import Path

import pytest

from chatto_releasebot import run_once
from chatto_releasebot.chatto import ChattoError, DeliveryUncertain
from chatto_releasebot.config import Config
from chatto_releasebot.github import Release
from chatto_releasebot.state import StateStore


class FakeChatto:
    def __init__(self, version: str = "0.5.0-beta.1") -> None:
        self.version = version
        self.reads = 0
        self.posts: list[str] = []
        self.history_has_announcement = False
        self.uncertain = False
        self.read_error = False

    def discover_version(self) -> str:
        return self.version

    def room_has_announcement(
        self, room_id: str, api_key: str, user_id: str, release_url: str
    ) -> bool:
        self.reads += 1
        if self.read_error:
            raise ChattoError("room timeline read failed")
        return self.history_has_announcement

    def create_message(self, room_id: str, body: str, api_key: str) -> None:
        self.posts.append(body)
        if self.uncertain:
            raise DeliveryUncertain("message delivery response was not received")


class FakeGitHub:
    def __init__(self) -> None:
        self.lookups = 0

    def get_release(self, version: str) -> Release:
        self.lookups += 1
        return Release(
            tag=f"v{version}",
            url=f"https://release.example/v{version}",
            body="### Features\n\n* improve calls",
        )


def config_for(path: Path) -> Config:
    return Config(
        server_base_url="https://chatto.example",
        api_key="bot-key",
        room_id="room-1",
        user_id="bot-1",
        user_name="announce_bot",
        state_path=path,
    )


def test_first_run_posts_once_second_run_posts_nothing_and_dry_run_writes_nothing(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    config = config_for(state_path)
    chatto = FakeChatto()
    github = FakeGitHub()

    first = run_once(config, chatto=chatto, github=github)
    second = run_once(config, chatto=chatto, github=github)
    dry_path = tmp_path / "dry-run.json"
    dry = run_once(config_for(dry_path), chatto=chatto, github=github, dry_run=True)

    assert "0.5.0-beta.1" in first
    assert "Already announced" in second
    assert "improve calls" in dry
    assert len(chatto.posts) == 1
    assert not dry_path.exists()
    assert not dry_path.with_name("dry-run.json.lock").exists()


def test_uncertain_post_is_reconciled_without_a_second_post(tmp_path: Path) -> None:
    config = config_for(tmp_path / "state.json")
    chatto = FakeChatto()
    chatto.uncertain = True
    github = FakeGitHub()

    with pytest.raises(DeliveryUncertain):
        run_once(config, chatto=chatto, github=github)

    assert StateStore(config.state_path).load().pending is not None
    chatto.uncertain = False
    chatto.history_has_announcement = True

    result = run_once(config, chatto=chatto, github=github)

    assert "reconciled" in result
    assert len(chatto.posts) == 1
    state = StateStore(config.state_path).load()
    assert state.announced_version == "0.5.0-beta.1"
    assert state.pending is None


def test_room_read_failure_sends_nothing(tmp_path: Path) -> None:
    config = config_for(tmp_path / "state.json")
    chatto = FakeChatto()
    chatto.read_error = True

    with pytest.raises(ChattoError):
        run_once(config, chatto=chatto, github=FakeGitHub())

    assert chatto.posts == []
    assert not config.state_path.exists()
