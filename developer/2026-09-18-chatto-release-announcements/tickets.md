# Chatto releasebot tickets

Plan for [the committed user stories](user-stories.md). Implement in order. Each code ticket starts with one failing behavior check, then the smallest change that passes it. Run `uv run ruff check --fix`, `uv run ruff format`, `uv run ty check`, and `uv run pytest` and commit each completed ticket before starting the next.

The application is a one-shot `chatto-releasebot` command. Ansible deployment and scheduling are outside this epic. No ticket sends a live announcement during automated tests.

## 1. Read the running server version

**Stories:** US-1. **Public interface:** Chatto's unauthenticated `ServerDiscoveryService.GetServer` at `ANNOUNCEMENTS_SERVER_BASE_URL`.

- Use the configured Chatto server URL for discovery, room reads, and posting. Return the live response's `profile.version` as the candidate version. Do not use GitHub's latest release, the Compose image reference, or browser assets.
- Reject a missing, empty, or malformed version and report the failed discovery request without exposing credentials.
- First failing check: a fake discovery response with `profile.version: "0.5.0-beta.1"` yields that version; a response without it fails without producing a version.

## 2. Resolve the exact upstream release

**Stories:** US-2. **Public interface:** GitHub's `GET /repos/chattocorp/chatto/releases/tags/v<version>` response.

- Accept the exact `v<version>` Chatto release, including alpha and beta, and return its release URL and Markdown body. Never substitute a newer stable release or an `authling/v...` tag.
- Treat a missing, draft, mismatched, or unavailable release as pending; it must not lead to a post or state change.
- First failing check: `0.5.0-beta.1` resolves to its exact release; a 404 or wrong tag cannot yield an announcement.

## 3. Compose one user-facing announcement

**Stories:** US-2, US-3. **Public interface:** one message body for the matched release.

- Include the deployed version, direct release link, and at most five short bullets drawn from that release's user-visible features, fixes, or relevant breaking changes. Make no claims absent from the release notes.
- Exclude internal API, refactoring, and tooling entries unless they clearly affect users. If no user-visible entry remains, say so plainly and keep the link.
- Use only the newly installed release's notes when an upgrade skips versions.
- First failing check: a representative `0.5.0-beta.1` body includes call or mobile UI changes, excludes the internal room-patch change, and renders as one message; an internal-only body gets the fallback.

## 4. Authenticate and post as the configured bot

**Stories:** US-3. **Public interface:** local `.env` values and Chatto `MessageService.CreateMessage`.

- Read `ANNOUNCEMENTS_SERVER_BASE_URL`, `ANNOUNCEMENTS_API_KEY`, and `ANNOUNCEMENTS_ROOM_ID` without printing the key. Missing or invalid values cause an actionable failure before any POST. The supplied user ID and name may be used for an identity check but are not required for message creation.
- Send one root text message to the configured room with the bot API key. A confirmed CreateMessage response counts as success; authentication, permission, or transport errors do not.
- First failing check: a fake Chatto transport sees one authenticated CreateMessage for the configured room and body, while a denied response yields no success result and no leaked credential.

## 5. Persist the last announced version

**Stories:** US-1, US-3. **Public interface:** a durable state file owned by the job's `chatto` OS user.

- Use `$XDG_STATE_HOME/chatto-releasebot/state.json` when set, otherwise `~/.local/state/chatto-releasebot/state.json`; tests can supply a temporary path.
- A missing file means the current version needs an announcement; a matching saved version means no post is needed. A different saved version, including a downgrade, is pending.
- Record a pending attempt before sending, then record a version as announced only after confirmed delivery. A pending attempt survives a crash so the next run knows to reconcile it. Use a replacement that cannot leave partly written state, and refuse corrupt state rather than silently starting over.
- Prevent overlapping invocations on this host from both deciding to post the same change.
- First failing check: a temporary state file survives a new process read, and a crash after recording an attempted version leaves the previous announced version plus a pending attempt.

## 6. Reconcile an uncertain post before retrying

**Stories:** US-3. **Public interface:** Chatto `RoomService.GetRoomEvents` plus the bot's room-read permission.

- Before any post, confirm the bot can read the room timeline for later reconciliation. After a timeout or lost CreateMessage response, do not immediately repeat the POST. On the next run, use the pending attempt to inspect visible room events for the bot's release announcement, identified with `ANNOUNCEMENTS_USER_ID` and the release link.
- If the matching announcement is found, record that version without another post. If a complete read shows it was not posted, retry. If reading is denied, unavailable, or inconclusive, fail visibly and do not risk a duplicate.
- Keep rollback behavior: an older version announced before a newer one does not suppress a new announcement when the server returns to that older version.
- First failing check: a simulated accepted post with a lost response is recovered from room history without a second POST; a read failure sends nothing.
- **Operator prerequisite:** verify a room-scoped read grant sufficient for `GetRoomEvents` (`message.read-interactions` if it covers the bot's own roots, otherwise `message.read`). Its human owner must also have the effective permission.

## 7. Wire the one-shot command and dry run

**Stories:** US-1, US-2, US-3. **Public interface:** `chatto-releasebot` and `chatto-releasebot --dry-run`.

- A normal run checks the live version, ignores an unchanged version, fetches and formats the exact release for a changed version, records a pending attempt, posts once, then records success. A previous pending attempt is reconciled before any retry.
- A dry run shows the observed version and proposed message without posting or changing the state file. It fails visibly if version discovery or release lookup fails.
- Missing release, invalid configuration, denied permission, and failed delivery exit nonzero and leave the last-announced version unchanged. Output never includes the bot key.
- First failing check: with fake HTTP boundaries and a temporary state path, first run posts once, second run posts nothing, and dry run writes nothing.

## 8. Write the operator and developer guides

**Stories:** US-4. **Public interface:** `README.md` for server admins and `AGENTS.md` for human and agent developers.

- Make `README.md` the server admin guide: explain what the bot does and when it posts; how to create its account, add it to `#announcements`, grant the required post and room-read permissions, and verify those grants before deployment. Document `ANNOUNCEMENTS_SERVER_BASE_URL` and the other required configuration, plus secret provision and rotation without exposing `.env` values.
- In `README.md`, document the observed `/srv/chatto` layout and `chatto` OS user, live version discovery, the planned Ansible handoff using `uv tool install .` and `uv tool update-shell`, a scheduler command independent of an interactive shell path, a persistent writable state location, and roughly daily execution. Explain dry-run verification, one controlled first-run post, repeat-run behavior, failed-delivery handling, pausing the schedule, and revoking the credential.
- Make the first half of `AGENTS.md` a guide for human and agent developers: repository layout, local setup, external API and state boundaries, test approach without live posts, and the four local commit gates. Make its latter half a clearly marked set of guardrails for agentic developers only, including secret handling, read-only access to the Ansible-managed host, and approval before a live announcement.
- Check: a server admin can follow `README.md` without reading `AGENTS.md`; the documented local commands pass a non-posting dry run; developer instructions and agent-only guardrails are visibly separated in `AGENTS.md`; paths and permission names match the committed findings. Do not change the Ansible-managed host in this ticket.

## Approval boundary

Approve this ticket and behavior plan before `tickets.md` is committed or implementation begins, as required by the specialization workflow. The only known external prerequisite is an effective room-read permission for ticket 6; the bot currently has a confirmed `message.post` grant, but its API key and effective permissions have not been tested.
