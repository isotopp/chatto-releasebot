from __future__ import annotations

import re

from .github import Release

_HEADING = re.compile(r"^#{2,3}\s+(.+?)\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
_SKIPPED_PREFIXES = (
    "api:",
    "authling:",
    "build:",
    "chore:",
    "ci:",
    "deps:",
    "docs:",
    "refactor:",
    "test:",
    "tooling:",
)


def select_user_visible_changes(markdown: str) -> list[str]:
    changes: list[str] = []
    section_is_relevant = False
    for line in markdown.splitlines():
        heading = _HEADING.match(line)
        if heading:
            normalized = heading.group(1).casefold().strip(" ⚠️")
            section_is_relevant = normalized.startswith(
                (
                    "features",
                    "bug fixes",
                    "breaking changes",
                    "performance improvements",
                )
            )
            continue
        if not section_is_relevant:
            continue
        bullet = _BULLET.match(line)
        if not bullet:
            continue
        text = re.sub(r"\s+\(#[0-9]+\)\s*$", "", bullet.group(1)).strip()
        text = re.sub(r"\s+\([0-9a-f]{7,40}\)\s*$", "", text).strip()
        if not text or text.casefold().startswith(_SKIPPED_PREFIXES):
            continue
        changes.append(text)
        if len(changes) == 5:
            break
    return changes or ["No user-visible changes were listed in the release notes."]


def compose_announcement(version: str, release: Release) -> str:
    changes = select_user_visible_changes(release.body)
    if len(changes) == 1 and changes[0].startswith("No user-visible"):
        change_text = changes[0]
    else:
        change_text = "\n".join(f"- {change}" for change in changes)
    return (
        f"Chatto {version} is now running.\n\n"
        f"Notable changes:\n{change_text}\n\n"
        f"Full release notes: {release.url}"
    )
