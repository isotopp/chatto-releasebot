# Chatto releasebot

This project will announce a Chatto release in `#announcements` when the version running on our server changes. Each post will link to the matching [Chatto release](https://github.com/chattocorp/chatto/releases) and summarize user-visible changes. The bot is currently a scaffold; the behavior is specified in [user stories](developer/2026-09-18-chatto-release-announcements/user-stories.md).

## Local development

Python 3.14 and [uv](https://docs.astral.sh/uv/) are required. Install the locked dependencies with `uv sync`, then run the local commit gates:

```sh
uv run ruff check --fix
uv run ruff format
uv run ty check
uv run pytest
```

Source code belongs in `src/`; tests belong in `tests/`. The runtime dependencies are `httpx` and `python-dotenv`. Ruff, ty, and pytest are development dependencies.

## Deployment notes

The local Chatto service at <https://chatto.koehntopp.de/> is managed by Ansible. Do not edit its configuration directly on the host. See [discovery notes](developer/findings.md) for the observed layout and integration constraints. Installation instructions will be added with the bot implementation.
