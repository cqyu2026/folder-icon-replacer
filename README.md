# mac-folder-icon-replacer

A macOS skill for replacing one user-confirmed folder icon from either a prepared transparent PNG or a raw image.

## Behavior

- A valid subject-only transparent PNG skips background removal.
- A raw JPG/JPEG/PNG is processed with Apple Vision on macOS 14 or later.
- Multiple detected subjects are exported as individually numbered `candidate-01.png`, `candidate-02.png`, and so on. The user chooses by number before any icon is changed.
- Visible text is treated as annotation by default, not as an icon subject.
- Icon mutation uses native `NSWorkspace.setIcon` first. Finder/clipboard automation is only a fallback.
- If a WorkBuddy background process is blocked by macOS, `scripts/terminal-apply.sh` hands the same verified operation to the signed-in `Terminal.app` context.
- Ordinary files and subfolders inside the target folder are never modified.

## Installation validation

The package includes a self-test. Installation has two levels:

1. `preflight` checks package integrity, JPG support, native tool compilation, the local runtime, and—when image extraction is available—icon writing on a temporary fixture copy. It has no user-folder side effects.
2. `e2e` requires explicit authorization because it runs Apple Vision and changes only the icon metadata of a temporary copy of the bundled test folder. It verifies that ordinary contents are unchanged and writes a durable receipt under `~/Library/Application Support/folder-icon-replacer/verification/`.

From the installed skill directory:

```sh
python3 scripts/install-self-test.py --stage preflight
python3 scripts/install-self-test.py --stage e2e --authorize-e2e
```

For a real WorkBuddy task whose icon-write probe is blocked, run the generated `scripts/terminal-apply.sh` command in Terminal.app and return the output containing `icon_status=verified`.

If the host blocks Apple Vision during preflight, the result is `authorization-required` with `native-ready`; the authorized E2E run must be performed in the host's approved execution context.

## Requirements

- macOS 14 or later for automatic foreground extraction.
- Apple Command Line Tools for compiling the native helpers during validation.
- A user confirmation before changing a real folder icon.

The package intentionally contains no user-specific paths, local reports, or project-context files.
