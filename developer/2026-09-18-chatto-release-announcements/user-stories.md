# Chatto release announcements

## Goal

As members of our Chatto server, we want `#announcements` to show one concise announcement when the Chatto version actually running on our server changes, so we can see the important user-visible changes and open the upstream release notes.

The bot watches the deployed version, not upstream publication alone. Both stable and prerelease Chatto versions are in scope because our server currently runs a prerelease. Independent `authling/v...` releases are out of scope.

## US-1: Detect the deployed Chatto version

As a server operator, I want the bot to identify the version of the running Chatto container, so an upstream release that we have not installed does not produce an announcement.

Acceptance criteria:

- The observed version comes from the running local Chatto container, not a planned Compose image, GitHub's latest release, or a cached browser asset.
- A scheduled check with the same version as the last handled version produces no post.
- On the first check, the bot records the installed version as its baseline without announcing historical releases.
- If the running version cannot be determined or is malformed, the bot reports a useful error and neither posts nor advances its saved version.
- The last handled version survives process restarts.

## US-2: Find and summarize the matching release

As a member, I want the announcement to describe the noteworthy changes in the version we now run, so I can decide whether to read the full notes.

Acceptance criteria:

- For a changed local version, the bot finds the matching `v<version>` release in `chattocorp/chatto`, including alpha and beta versions.
- It ignores unrelated repository releases, including `authling/v...` tags, and never substitutes the newest upstream release for a missing match.
- The announcement includes the deployed version, a direct link to that version's GitHub release, and a short, accurate selection of user-visible changes. Internal tooling and API churn are omitted unless they affect users.
- If the release is unpublished, unavailable, or cannot be fetched, the bot makes no announcement, keeps the version pending, and can try again later.
- When the release notes contain no clear user-visible change, the announcement says so plainly and still links the full notes.

## US-3: Post one announcement in the intended room

As a member, I want one readable root post in `#announcements` for each deployed version change, so the channel is informative without duplicate or fragmented posts.

Acceptance criteria:

- The post is authored by a dedicated Chatto bot account in the configured `#announcements` room and contains the version, selected changes, and release link in one message.
- Repeated checks and ordinary restarts do not repost an already announced version.
- A failed send leaves the version pending for retry. An uncertain send result is reconciled before retrying so a lost HTTP response does not routinely create a duplicate.
- The bot has only the Chatto permissions needed to join, read if reconciliation needs it, and post in that room. Its credential is kept out of Git, logs, and command-line arguments.
- If the bot loses room access or posting permission, the failure is visible to the operator and the saved version does not advance as announced.

## US-4: Install and operate on our server

As the operator of `chatto.koehntopp.de`, I want installation instructions for this deployment, so I can configure the bot through Ansible and verify it safely.

Acceptance criteria:

- The runbook identifies `/srv/chatto/compose/compose.yml`, the rootless `chatto` Podman runtime, and the actual running-version source. It does not instruct manual edits to Ansible-managed files.
- It explains how to create the bot account, give it effective room-scoped permissions and membership, identify the stable room ID for `#announcements`, and provision and rotate the required credential.
- It explains how to install and schedule the check, store its last handled version durably, supply secrets outside the repository, and observe failures.
- It includes a non-posting verification path plus a controlled test for one version change, repeated execution, and a failed delivery.
- It explains how to pause the job or revoke the bot credential without changing the Chatto service.

## Decisions to confirm before tickets

- First run establishes a baseline and does not announce the already running version.
- If an upgrade skips intermediate Chatto releases, the message will summarize the installed release's notes. We should decide whether it must also cover changes from skipped releases.
- The current deployment has MCP disabled. The public bot API is available; an incoming webhook is simpler for posting but has no idempotency key. The ticket plan must choose a practical reconciliation method for uncertain sends.
