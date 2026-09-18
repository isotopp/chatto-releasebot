# Chatto releasebot operator guide

`chatto-releasebot` is a one-shot job for the existing Chatto deployment. It
reads the version served by `ANNOUNCEMENTS_SERVER_BASE_URL`, looks up that
exact `v<version>` release in `chattocorp/chatto`, and posts one concise root
message in `#announcements` when the deployed version differs from the last
successfully announced version. It accepts stable, alpha, and beta versions.
An upstream release that is not installed does not trigger a post.

The job does not alter Chatto or its deployment. The observed deployment has
this Ansible-managed layout:

```text
/srv/chatto/compose/compose.yml
/srv/chatto/compose/.env
/srv/chatto/config/chatto.toml
/srv/chatto/data/nats/
```

Chatto runs rootless Podman as the `chatto` OS user. Treat `/srv/chatto` and
the running host as read-only; request Ansible changes from the operator.

## Set up the bot in Chatto

Create a dedicated bot account named `announce_bot`, add it to the
`#announcements` channel, and record the stable room ID rather than relying on
the room name. Grant the bot the room-scoped `message.post` permission.

For duplicate reconciliation, also grant a room-scoped read permission:

- use `message.read-interactions` if it covers the bot's own root messages;
- otherwise use `message.read`.

The human owner of the bot must have the effective permission as well. Verify
the bot appears in the room member list and verify the effective grants before
deployment. A missing membership, post grant, or read grant is a configuration
failure; the job will not post around it.

Provision the bot API key through the host's secret mechanism or an ignored
local `.env` file. Keep it out of Git, logs, process arguments, and tickets.
To rotate it, create the replacement key, update the provisioned secret with
mode `0600`, run a dry run, then revoke the old key. Revoking the credential
pauses delivery without changing the Chatto service.

## Configuration

The job reads `.env` from its current directory. If that file is absent, it
reads `~/.chatto-releasebot.env` for the user running the job. If both are
absent, it exits with an error. It reads exactly one file; values from the
other file are not used to fill missing entries. Process environment values
can override values in the selected file. Neither file is deployed by Git:

```dotenv
ANNOUNCEMENTS_SERVER_BASE_URL=https://chatto.koehntopp.de
ANNOUNCEMENTS_GITHUB_BASE_URL=https://api.github.com/repos/chattocorp/chatto
ANNOUNCEMENTS_API_KEY=replace-me
ANNOUNCEMENTS_ROOM_ID=replace-me
ANNOUNCEMENTS_USER_ID=replace-me
ANNOUNCEMENTS_USER_NAME=announce_bot
```

`ANNOUNCEMENTS_SERVER_BASE_URL` is used for live version discovery, room reads,
and message creation. `ANNOUNCEMENTS_GITHUB_BASE_URL` is the GitHub repository
API URL used to look up releases. `ANNOUNCEMENTS_USER_ID` identifies the bot
when checking room history; the username is an operator-side identity check and
is not sent as part of message creation. Never print the API key or copy any
host secret into this repository.

The durable state file is
`~/.local/state/chatto-releasebot/state.json`.
It belongs to the `chatto` OS user and must be writable by that user. The job
uses an adjacent lock file so overlapping invocations cannot both post the
same version.

## Install and schedule

Ansible should deploy this repository for the existing `chatto` OS user. The
planned handoff is:

```sh
uv tool install .
uv tool update-shell
command -v chatto-releasebot
```

Use the absolute path returned by `command -v` in the scheduler. Do not rely
on an interactive shell's `PATH`. For example, after verifying the actual
paths on the host, a roughly daily cron entry can be:

```cron
17 3 * * * cd /srv/chatto/releasebot && /home/chatto/.local/bin/chatto-releasebot >> /home/chatto/.local/state/chatto-releasebot/cron.log 2>&1
```

Adjust `/srv/chatto/releasebot` and the installed command path to the Ansible
checkout and the verified `command -v` result. The scheduler must run as
`chatto`, from the checkout containing the provisioned `.env` or with
`~/.chatto-releasebot.env` in the `chatto` user's home, and with a writable
state directory.

## Verify safely

From the checkout, install locked dependencies and run the non-posting check:

```sh
uv sync
uv run chatto-releasebot --dry-run
```

Dry run discovers the live version and renders the exact release announcement;
it does not read room history, post, or change the state file. A missing
release, invalid version, invalid configuration, or failed discovery is a
visible nonzero failure.

For the controlled first run, confirm the bot membership and effective
permissions, make sure the state file is absent or backed up, and run the
normal command once as `chatto`. Confirm exactly one root post in
`#announcements`. A repeat run with the same deployed version does nothing.

If delivery times out or the response is lost, the attempt remains pending.
The next run reads the room timeline and looks for the bot's ID plus the
release link before retrying. A matching post advances state without another
POST. A complete read with no match permits one retry; a denied, unavailable,
or inconclusive read sends nothing and exits nonzero. A confirmed delivery is
the only event that records the version as announced.

To pause the job, disable its cron entry or scheduler unit. To stop it from
posting immediately, revoke the bot API key; restore the secret and verify a
dry run before resuming. Neither action requires editing the Chatto service or
its Ansible-managed files.

## Local development

Python 3.14 and [uv](https://docs.astral.sh/uv/) are required. Source code is
under `src/`, tests are under `tests/`, and fake HTTP boundaries are used so
automated tests never send a live announcement. Run the local gates with:

```sh
uv run ruff check --fix
uv run ruff format
uv run ty check
uv run pytest
```
