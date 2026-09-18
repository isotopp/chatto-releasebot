# Chatto releasebot discovery

Observed 2026-09-18. This is an exploration record; no bot or deployment changes were made.

## Local project

- Python scaffold in `src/chatto_releasebot/__init__.py`; `pyproject.toml` requires Python 3.14. Runtime dependencies are `httpx` and `python-dotenv`; Ruff, ty, and pytest are development dependencies.
- `README.md` documents local setup and commit gates. The scaffold is tracked in Git.

## Chatto deployment

- Public server: <https://chatto.koehntopp.de/> (HTTP 200).
- SSH: `ssh -i ~/.ssh/codex root@kvm` resolves to `kvm.koehntopp.de`.
- Deployment directory on this host is `/srv/chatto`. Treat it as read-only: Ansible manages it.
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
- Bot API keys authorize normal ConnectRPC calls with `Authorization: Bearer cht_BK_...`; MCP can use a bot key when enabled. The supplied bot API key is intended for posting through the public API and, with sufficient permission, reading messages for duplicate reconciliation. Its validity and permissions have not yet been tested. An incoming webhook remains an alternative.
- MCP exposes `post_message`, room listing, and message reading, but is currently disabled on this deployment. Enabling it would require an Ansible-managed config change and a restart.
- The public `ServerDiscoveryService.GetServer` response includes `profile.version`. A read-only call to the live server returned `0.5.0-beta.1`, matching the running image label. This is the simplest source for the deployed version; see the [ConnectRPC overview](https://dev-docs.chatto.run/reference/connectrpc-api/).
- `RoomService.GetRoomEvents` can read recent room timeline events but requires room membership and `message.read` (or an applicable interaction grant). It is a possible way to reconcile an uncertain message post.

## Refined requirement

The releasebot should inspect the version actually running on the local Chatto server. It should announce when that deployed version differs from the last announced version in a state file, provided that the matching GitHub release is available. If the state file does not exist, announce the current version. A new upstream release alone is not an announcement trigger. The live server's public discovery `profile.version` is the authoritative runtime version source. The job will run as an unprivileged OS user.

## Local bot configuration supplied

- A repository-local `.env` is present and ignored by Git. `python-dotenv` confirmed non-empty values for `ANNOUNCEMENTS_ROOM_ID`, `ANNOUNCEMENTS_API_KEY`, `ANNOUNCEMENTS_USER_ID`, and `ANNOUNCEMENTS_USER_NAME`. The bot username is `announce_bot`. `ANNOUNCEMENTS_SERVER_BASE_URL=https://chatto.koehntopp.de` was added later; this URL is public and should be used for discovery, room reads, and posting. Do not print or commit the credential or IDs.
- The room ID and bot API key are available for local development. The operator has set up `announce_bot`, confirmed it appears in the `#announcements` member list, and granted it `message.post`. API-key validity, effective posting permission, and `message.read` have not yet been tested.

## Deployment plan and remaining checks

1. Verify the supplied API key and the bot's effective `message.post` permission in `#announcements`. Confirm `message.read` if duplicate reconciliation requires it; the human owner must have corresponding authority.
2. Ansible will deploy this Git repository for the existing `chatto` OS user. The installation plan uses `uv tool install .` and `uv tool update-shell`; the scheduled invocation must resolve the installed command. The job is expected to run about once a day, likely via cron.
3. An upgrade that skips intermediate releases includes only the newly installed version's release-note items.
4. Applying the deployment is out of scope for this repository. Installation instructions should document the Ansible handoff, the persistent state file, and secure provisioning of `.env` values that are ignored by Git.

## Minimal likely approach

On a schedule under the `chatto` OS user, read the live Chatto server's public version and compare it with the last announced version in a file. A missing file calls for an announcement. Fetch the matching `v<version>` Chatto release, select user-visible changes from that release, and post one message with its release URL using the supplied bot API key. Record the version only after confirming the post. An uncertain response needs reconciliation before retrying because message posting is not idempotent.
