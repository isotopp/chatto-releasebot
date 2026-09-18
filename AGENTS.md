# Developer guide

## Repository layout

- `src/chatto_releasebot/` contains the one-shot command, Chatto ConnectRPC
  client, GitHub release lookup, formatter, configuration, and state store.
- `tests/` contains behavior checks using fake HTTP and in-memory boundaries;
  no automated test posts to a live Chatto server.
- `developer/` contains the approved user stories, findings, and ticket plan.
- `README.md` is the server-admin installation and operations guide.

## Local setup

Use Python 3.14 and uv. Install the locked dependencies with `uv sync`. For
local integration checks, provision an ignored `.env` in the current directory
or `~/.chatto-releasebot.env` with fake or explicitly approved development
values; never commit it. The loader selects the current directory file first
and reads only one file. `chatto-releasebot --dry-run`
discovers the configured server version and renders a message without posting
or changing state.

The external boundaries are deliberate:

- the live Chatto server is the source of `profile.version` through the
  unauthenticated `ServerDiscoveryService.GetServer` response;
- GitHub's exact `v<version>` release supplies the release URL and Markdown
  notes;
- the configured Chatto API key is used for `MessageService.CreateMessage` and
  `RoomService.GetRoomEvents` in the configured room;
- durable job state belongs in
  `$XDG_STATE_HOME/chatto-releasebot/state.json`, falling back to
  `~/.local/state/chatto-releasebot/state.json`.

Use fake HTTP transports and temporary state paths in tests. A normal run must
record a pending attempt before sending and record the version only after a
confirmed response. A lost response is reconciled from room history before a
retry.

Before committing code, run all four local gates and review automatic changes:

```sh
uv run ruff check --fix
uv run ruff format
uv run ty check
uv run pytest
```

## Agent-only guardrails

The following rules apply to coding agents and automation operating in this
repository:

- Keep credentials in local secret storage or environment variables. Never
  commit `.env` files, bot keys, webhook URLs, room credentials, or host
  configuration secrets. Do not print secret values in test output or errors.
- Treat the Chatto host as read-only. Its deployment is managed by Ansible;
  document required host changes for the operator instead of applying them
  over SSH. In particular, do not edit `/srv/chatto/compose/compose.yml`,
  `/srv/chatto/compose/.env`, or `/srv/chatto/config/chatto.toml` directly.
- Automated tests must not send a live announcement. Use fake HTTP boundaries,
  dry-run mode, and temporary state files.
- Do not run a normal command against the configured live server, create a
  live post, rotate or revoke a production credential, or change effective
  Chatto permissions without explicit operator approval for that action.
