from chatto_releasebot.formatting import (
    compose_announcement,
    select_user_visible_changes,
)
from chatto_releasebot.github import Release


def test_announcement_keeps_user_changes_and_excludes_internal_entries() -> None:
    release = Release(
        tag="v0.5.0-beta.1",
        url="https://github.com/chattocorp/chatto/releases/tag/v0.5.0-beta.1",
        body=(
            "### Features\n\n"
            "* improve mobile room navigation\n"
            "* add voice calls\n\n"
            "### Bug Fixes\n\n"
            "* api: patch internal room state\n\n"
            "### Refactoring\n\n"
            "* refactor event storage"
        ),
    )

    body = compose_announcement("0.5.0-beta.1", release)

    assert "improve mobile room navigation" in body
    assert "add voice calls" in body
    assert "internal room state" not in body
    assert body.count("\n- ") == 2
    assert release.url in body


def test_internal_only_release_gets_plain_fallback() -> None:
    changes = select_user_visible_changes(
        "### Bug Fixes\n\n* api: patch internal room state\n* tooling: update CI"
    )

    assert changes == ["No user-visible changes were listed in the release notes."]
