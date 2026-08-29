---
name: mac-folder-icon-replacer
description: Automatically replace the custom icon of one already-confirmed ordinary macOS folder from an image path. Return success when the icon update is verified; on a permission failure, return a ready-to-paste Terminal.app command.
---

# Mac Folder Icon Replacer

## Task Contract

The user provides exactly two inputs:

1. An image path.
2. The full path of an already-confirmed ordinary macOS folder.

The expected result is an updated folder icon. Do not ask for an additional confirmation during the normal path. The user's explicit folder path is the authorization to operate on that folder's icon metadata.

The only intended external mutation is the target folder's custom icon metadata. Never create, delete, rename, move, overwrite, or permission-change ordinary files or subfolders inside the target folder. macOS may create icon-related system metadata such as `Icon\r` or `.DS_Store`.

## Default Image Policy

Use the whole input image as the icon by default. Decode it and normalize it to a PNG in a temporary directory without overwriting the original. Preserve the source image.

Do not pause for subject selection, text classification, candidate numbering, or a composite preview in the default path. Background removal is optional and must be explicitly requested or configured; if used, it must finish without user selection. A failed or ambiguous background-removal result is a failure, not a reason to guess.

## Automatic Workflow

Run the following sequence through the packaged scripts/native tools:

1. Validate that the image is readable and the target is an existing ordinary local folder.
2. Normalize the image to a valid PNG outside the target folder.
3. Snapshot ordinary target contents before the icon update.
4. Use the native `NSWorkspace.setIcon` helper as the primary backend.
5. Read back the folder icon and verify that it changed as a result of this invocation.
6. Snapshot ordinary target contents again and verify that they are unchanged.
7. Return `成功` only when the icon update and contents verification both pass.

The normal entry point is:

```sh
python3 /absolute/path/to/scripts/apply-icon.py /absolute/path/to/image /absolute/path/to/folder
```

Use the actual two user-provided paths. The script owns image normalization, helper setup, icon application, contents verification, and the Terminal handoff output.

Do not run installation self-tests on every normal task. Use `references/install-validation.md` and `scripts/install-self-test.py` only after installation, after a skill update, or when the cached host capability is missing or stale. Building a missing native helper during the task is allowed; it must be built from the packaged source and its result must be checked before use.

## Target Safety Checks

The target must be revalidated immediately before the write. Reject it if it is:

- a file, symbolic link, package, application, disk, mount point, network volume, or special object;
- the root directory, a protected system directory, or a path that changed since input validation;
- inaccessible for icon metadata modification.

The native setter must enforce these checks itself. Do not rely only on Agent instructions or the wrapper, because the helper can be invoked directly.

## Failure and Terminal Handoff

Return exactly one of these high-level statuses:

- `成功`: icon update verified and ordinary contents unchanged.
- `失败`: no safe automatic completion; provide a specific reason.
- `失败-等待Terminal`: the final PNG exists, the target passed safety checks, and only the current process context was denied icon metadata access.
- `失败-状态不确定`: an update may have occurred but the final state cannot be verified. Do not generate a blind retry command.

For `失败-等待Terminal`, output a shell-quoted command that the user can paste into the already signed-in `Terminal.app`:

```sh
sh '/absolute/path/to/scripts/terminal-apply.sh' '/absolute/path/to/final.png' '/absolute/path/to/confirmed/folder'
```

The command must use the actual absolute paths and must not place generated files inside the target folder. Wait for `icon_status=verified` from Terminal before reporting the handoff as successful. A Terminal permission error remains a failure.

Do not output a Terminal command when the image is invalid, the target is unsafe or ambiguous, the final PNG does not exist, ordinary contents changed, or the icon state is uncertain.

## Result Format

Keep the normal report short:

```text
成功
文件夹：/absolute/path/to/folder
图标：已修改并验证
内容：普通文件和子文件夹未变化
方式：NSWorkspace.setIcon
```

For failure, include:

- status;
- specific reason;
- target path;
- final PNG path when one exists;
- whether icon mutation occurred, failed, or is uncertain;
- the Terminal command only for `失败-等待Terminal`.

Never claim success from a process exit code alone. The icon readback and ordinary-content check are required.

## Optional Finder Fallback

Finder/clipboard automation is not part of the normal path. Use it only when the native setter is unavailable or the user explicitly requests Finder. The same target safety checks and final verification still apply. If Finder cannot be controlled, return failure with the generated PNG path rather than claiming completion.

## Installation Validation

Installation validation is a maintenance operation, not a per-task prerequisite. File presence means `installed`; the isolated fixture E2E is what proves `verified` for a host and build. Keep the existing self-test for that purpose, but do not make a normal icon replacement wait for it unless the helper or required capability is unavailable.

After this Skill is installed or updated, the Agent must:

1. Run `preflight` without changing a real user folder.
2. Show the preflight result and explicitly tell the user that installation is not yet `verified`.
3. Ask the user for authorization to run the isolated E2E test on a temporary fixture copy.
4. Run `--stage e2e --authorize-e2e` only after the user explicitly authorizes it.
5. Report `verified` only when that E2E test passes; do not infer verification from file presence, compilation, or preflight alone.

The self-test does not display an authorization dialog by itself. The Agent is responsible for pausing after preflight and requesting this explicit authorization. The authorization applies only to the temporary fixture copy and never to a real user folder.
