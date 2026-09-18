from pathlib import Path

import pytest

from chatto_releasebot.config import Config, ConfigError


@pytest.fixture(autouse=True)
def clear_announcement_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ANNOUNCEMENTS_SERVER_BASE_URL",
        "ANNOUNCEMENTS_API_KEY",
        "ANNOUNCEMENTS_ROOM_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def _configuration(room_id: str) -> str:
    return (
        "ANNOUNCEMENTS_SERVER_BASE_URL=https://chatto.example\n"
        "ANNOUNCEMENTS_API_KEY=test-key\n"
        f"ANNOUNCEMENTS_ROOM_ID={room_id}\n"
    )


def test_current_directory_file_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".chatto-releasebot.env").write_text(_configuration("home-room"))
    (tmp_path / ".env").write_text(_configuration("local-room"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    assert Config.from_env().room_id == "local-room"


def test_home_file_is_used_when_current_directory_has_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".chatto-releasebot.env").write_text(_configuration("home-room"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    assert Config.from_env().room_id == "home-room"


def test_missing_files_fail_with_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(ConfigError, match=r"\.env.*\.chatto-releasebot\.env"):
        Config.from_env()


def test_local_file_is_not_completed_from_home_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".chatto-releasebot.env").write_text(_configuration("home-room"))
    (tmp_path / ".env").write_text("ANNOUNCEMENTS_ROOM_ID=local-room\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(ConfigError, match="ANNOUNCEMENTS_SERVER_BASE_URL"):
        Config.from_env()
