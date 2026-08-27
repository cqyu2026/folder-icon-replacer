# Installation Validation Protocol

An installed Skill is not considered verified until the host-specific installation self-test passes.

## States

- `installed`: package files are present; runtime capabilities are not yet proven.
- `native-ready`: package integrity, fixtures, native compilation, and JPG decoding passed, but Apple Vision must be retried in the signed-in GUI session because the host process cannot access its ANE model.
- `capability-ready`: all `native-ready` checks plus Apple Vision extraction, candidate naming, and transparent PNG validation passed without changing a folder icon.
- `icon-write-ready`: image capability checks passed and `NSWorkspace.setIcon` successfully updated only a temporary fixture copy; this does not authorize a real user folder.
- `icon-write-unavailable`: image capability checks passed but the temporary icon-write probe was rejected by macOS or the host process; automatic folder replacement is not verified.
- `authorization-required`: the next test changes only the icon metadata of a temporary fixture copy and requires explicit user approval.
- `verified`: the isolated end-to-end icon test passed and ordinary fixture contents remained unchanged.
- `partial`: a documented optional capability is unavailable, while a supported degraded route remains.
- `failed`: a required invariant failed; do not claim the Skill is ready.

## Commands

Run the no-user-folder-side-effect stage immediately after installation:

```sh
python3 scripts/install-self-test.py --stage preflight --host codex --host-version <version>
```

Show the resulting report and ask the user before the next command. After explicit approval:

```sh
python3 scripts/install-self-test.py --stage e2e --authorize-e2e --host codex --host-version <version>
```

Replace the host fields for WorkBuddy or another host. Never reuse a verification receipt from another host, Mac, Skill version, or native helper build.

## Authorization Boundary

The `--authorize-e2e` flag authorizes launching the packaged background-only extractor in the signed-in GUI session when the host process cannot access Apple Vision, plus a custom-icon change on a temporary copy of `tests/icon-replacement-test-folder`. It does not authorize changing a user folder, installing network dependencies, enabling broad macOS privacy permissions, or controlling Finder UI.

If the host requires a macOS permission prompt, explain the exact permission and why it is needed before asking the user. Refusal leaves the installation at `authorization-required`, `icon-write-unavailable`, or `partial`; it does not erase the installed files. A WorkBuddy background-process denial must not be fixed by repeating the same command in that process.

## Report Requirements

The JSON report records the Skill version and path, host and host version, macOS version, architecture, execution context, fixture hashes, native helper hashes, completed checks, icon-write probe result, required authorizations, errors, and next action. Preflight reports are temporary by default. An authorized successful E2E writes a durable receipt under `~/Library/Application Support/folder-icon-replacer/verification/`; this receipt write is part of the disclosed E2E authorization.

Only `installation_status=verified` is a complete installation verification result.
