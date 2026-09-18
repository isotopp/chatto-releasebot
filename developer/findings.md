# Chatto releasebot discovery

Observed 2026-09-18. This is an exploration record; no bot or deployment changes were made.

## Local project

- Python scaffold in `src/chatto_releasebot/__init__.py`; `pyproject.toml` requires Python 3.14 and has no runtime dependencies.
- `README.md` is empty. The scaffold is untracked in Git as of this inspection.

## Chatto deployment

- Public server: <https://chatto.koehntopp.de/> (HTTP 200).
- SSH: `ssh -i ~/.ssh/codex root@kvm` resolves to `kvm.koehntopp.de`.
- Deployment directory on this host is `/srv/chatto`, not `/home/chatto`. Treat it as read-only: Ansible manages it.
- Compose file: `/srv/chatto/compose/compose.yml`; environment file: `/srv/chatto/compose/.env`; application config: `/srv/chatto/config/chatto.toml`.
- Rootless Podman runs as UID 9000 (`chatto`), with containers `compose_chatto_1`, `compose_nats_1`, and `compose_livekit_1`. For read-only inspection as root: `runuser -u chatto -- env XDG_RUNTIME_DIR=/run/user/9000 podman ps`.
- Running Chatto image reports version `0.5.0-beta.1`; container started 2026-09-18 07:12 UTC. Compose pins the image by digest. NATS and LiveKit are separate services.
- `webserver.url` is `https://chatto.koehntopp.de`. No `[mcp]` section is present in `chatto.toml`, so MCP is not enabled. Do not expose or copy values from `.env`, `chatto.toml`, or `secrets/` into this repository.
- Chatto config, backups, and the backup passphrase are mounted into the container from `/srv/chatto`; the config and passphrase mounts are read-only. NATS data lives under `/srv/chatto/data/nats`.

## Upstream release source

- Repository: <https://github.com/chattocorp/chatto>.
- Releases: <https://github.com/chattocorp/chatto/releases>; JSON feed: <https://api.github.com/repos/chattocorp/chatto/releases>.
- Release objects provide `tag_name`, `html_url`, `published_at`, `prerelease`, and Markdown `body`. Recent notes contain `Features`, `Bug Fixes`, and sometimes `BREAKING CHANGES` and other internal changes.
- As observed, `v0.5.0-beta.1` was published 2026-09-17; `v0.4.24` is the latest stable release. Alpha/beta and stable releases coexist.
- The same repository also publishes independent `authling/v...` releases. Filter for Chatto tags beginning `v`; do not use the GitHub `releases/latest` endpoint if prereleases matter.
- Release notes are generated from conventional commits and contain many API, tooling, and internal items. A concise announcement needs a deliberate user-visible selection; always link the full release.

## Integration documentation

- Development docs: <https://dev-docs.chatto.run/>. These pages describe `main` and may be ahead of the deployed image.
- Bot accounts: <https://dev-docs.chatto.run/guides/integrations/bot-accounts/>.
- MCP: <https://dev-docs.chatto.run/guides/integrations/mcp/>.
- API reference is linked from the development docs, including `BotService`, `MessageService`, `PermissionService`, and `RoomService`.
- An incoming webhook can post one JSON text message: `POST /webhooks/incoming/<credential>` with a room ID in the URL or JSON. It accepts `text`, `body`, or `message`; success is HTTP 200 with `ok`. A webhook can be bound to one channel room when created.
- The bot must be a member of the target room and have effective `message.post`. Bot permissions are explicit, limited by the human owner's current permissions. Its owner must also be allowed to post there. Creating/joining it may require `room.join` or room management authority.
- Incoming webhooks have no idempotency key. A lost response followed by a retry can duplicate a message. MCP `post_message` is also non-idempotent.
- Bot API keys authorize normal ConnectRPC calls with `Authorization: Bearer cht_BK_...`; MCP can use a bot key when enabled. Neither is needed just to send one scheduled webhook message.
- MCP exposes `post_message`, room listing, and message reading, but is currently disabled on this deployment. Enabling it would require an Ansible-managed config change and a restart.

## Refined requirement

The releasebot should inspect the version actually running on the local Chatto server. It should announce when that deployed version changes, provided that the matching GitHub release is available. A new upstream release alone is not an announcement trigger. The running image's `org.opencontainers.image.version` label gives a verified local version source without enabling MCP.

## Implementation inputs still needed

1. Identify the announcements channel by stable room ID, and provide a bot-owned incoming webhook bound to it (or a bot API key if readback and reconciliation are required). Do not commit the credential.
2. Create a dedicated bot such as `release_bot`, join it to the announcements room, and grant only effective `message.post` there. Its human owner needs matching posting authority. A bot manager can create the webhook in Server Admin → Bots.
3. Choose where the polling job runs and where it persists the last announced local version. Deployment changes must go through Ansible.
4. Decide whether the first run announces the already deployed version and how to summarize upgrades that skip intermediate releases. A conservative default is to establish the current version as the baseline, then announce subsequent changes.

## Minimal likely approach

On a schedule, read the running Chatto image's version label and compare it with the last handled local version. If it changed, fetch the matching `v<version>` Chatto release, select user-visible changes, and send one message with its release URL to a room-bound incoming webhook. Persist the handled version to avoid routine repeats. Treat an uncertain webhook response as a separate reconciliation decision because the endpoint provides no idempotency key.
