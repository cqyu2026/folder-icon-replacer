---
name: mac-folder-icon-replacer
description: Replace one user-confirmed macOS folder icon from a prepared transparent PNG or a raw image. Validate the installation first, skip background removal for a valid subject-only transparent PNG, separate and number multiple subjects, require approval before icon mutation, and never modify ordinary files or subfolders inside the target folder.
---

# Mac Folder Icon Replacer

## Purpose

Replace the custom icon of one user-confirmed ordinary macOS folder using an input image. The workflow must produce or validate a transparent PNG, prefer the packaged native icon setter over clipboard UI automation, and verify that the folder icon changed without changing ordinary contents inside the folder.

## Scope and Non-goals

This version supports one ordinary folder per run. It does not support apps, system folders, disks, network volumes, special system objects, batch processing, or changes to files and subfolders inside the target folder.

The only intended external mutation is the custom icon metadata of the target folder itself.

## Required Inputs

Require:

1. One readable input image. The input does not need to be PNG or already transparent.
2. One explicitly selected or fully specified ordinary target folder.

Do not infer a target from a vague name, recent-item list, or an ambiguous search result.

Classify the image before processing:

- `prepared-transparent-png`: a real PNG containing visible subject pixels and at least one transparent or semi-transparent pixel. If the user confirms it already contains only the intended subject, skip background removal.
- `raw-image-auto`: JPG/JPEG, WEBP, an opaque PNG, or any image that still contains a background. On macOS 14 or newer, prefer the packaged Apple Vision foreground extractor.
- `image-plus-mask`: an image and a user-supplied mask that can deterministically create the alpha channel.
- `rembg-fallback`: optional only when the native route is unavailable and the user explicitly approves dependency installation. Never install it implicitly during the main workflow.

## Capability and Permission Preflight

Before processing or changing the target, read `references/install-validation.md`. If this Skill version has no valid verification receipt for the current host and Mac, run the packaged `preflight` self-test. Before processing or changing the target, also check whether the current agent can:

- read the input image;
- inspect actual alpha pixels, process a raw background when required, and output PNG with transparency;
- control the macOS desktop or Finder sufficiently to locate the folder, open Get Info, select the top icon, paste, and inspect the result;
- compile and use the packaged native tools, including Apple Vision extraction on macOS 14+ and `NSWorkspace.setIcon` for the primary icon update path;
- access the target folder and modify only its icon metadata;
- request user authorization when a required capability or permission is unavailable.

If a required capability or permission is missing, explain what is missing, why it is needed, and where the workflow will stop. Ask for authorization before any real modification. Never request, use, or rely on write access to files or subfolders inside the target folder.

Before spending time on real-image processing, run the packaged icon-write probe against a copy of the bundled test folder whenever the current host does not have a valid `icon-write-ready` or `verified` receipt. The probe may change only temporary fixture metadata and must report its execution context. If it returns `nsworkspace_rejected_icon_update` or `Operation not permitted`, classify the host as `icon-write-unavailable`; do not present the real task as fully automatable inside WorkBuddy. Explain that the WorkBuddy background process is not an authorized GUI context, then offer the packaged Terminal handoff or Finder manual fallback. A successful image preflight does not imply that a real folder icon can be written.

If the platform cannot perform desktop control, it may complete image processing and stop before Finder modification. Report the incomplete state accurately.

Do not request broad permissions in advance. Run checks that do not mutate external state automatically, explain each missing permission when it is actually needed, and ask before the isolated installation E2E test or any real folder icon update. Verification on one host, Mac, Skill version, or helper build does not transfer to another.

## Safety Boundary

The target folder's ordinary contents are read-only from this workflow's perspective. Do not create, delete, copy, move, rename, write, permission-change, or otherwise modify ordinary files or subfolders inside it. Do not place generated PNGs, intermediate files, logs, caches, or reports inside it. macOS or Finder may generate system metadata required for the custom icon or display state, such as `Icon` or `.DS_Store`; these system-generated metadata changes are allowed and are not considered ordinary file modifications.

If the operation cannot be shown to affect only the target folder's icon metadata, stop.

## User Confirmation Policy

Request confirmation:

- before the first run, showing the input image, target name and full path, detected capabilities, permissions, and safety boundary;
- when multiple subjects or materially different image candidates are extracted;
- after generating the transparent PNG and before entering Finder modification;
- before opening Get Info for the confirmed target;
- when the top icon cannot be reliably identified and the user must select it manually;
- immediately before paste, confirming the target, selected top icon, clipboard content, and that the user has not cancelled.
- when the image contains multiple visually separable subjects, show each subject as a separate extracted candidate and wait for the user to choose one or more of them;
- when text is detected, treat it as annotation or background content, not as a subject, unless the user explicitly requests that text be retained as the icon subject;
- a single clear non-text subject does not require a separate candidate-selection prompt. Never continue after cancellation.

## Workflow

### 1. Receive and Validate the Image

Read one input image. Accept common readable image formats, including JPG/JPEG, PNG, and WEBP when supported. Inspect file contents rather than trusting the extension. A JPG converted to PNG remains opaque unless a mask or segmentation step creates transparency.

For a claimed prepared transparent PNG, verify that it is actually PNG, contains visible pixels, and has at least one pixel with alpha below 255. An RGBA image whose alpha is 255 everywhere is opaque and must not use the skip route. When the prepared PNG is confirmed to contain only the intended subject, record `background_removal=skipped` and continue with normalization.

Stop only when the file cannot be read, is invalid or corrupted, has no recognizable subject after reasonable processing, or the current agent lacks image-processing capability. Do not reject low resolution, complex backgrounds, multiple subjects, small subjects, or complex edges without first attempting optimization.

### 2. Optimize the Image

When needed, attempt suitable improvements such as upscaling, subject enhancement, composition adjustment, cropping for icon display, background treatment, and edge repair. Preserve the original input and never overwrite it.

### 3. Extract Candidate Subjects

If there is one clear non-text subject, keep a single processing path and do not create numbered candidates. If there are multiple reasonably separable non-text subjects, extract every subject independently into its own transparent candidate PNG. Do not return one combined sheet or a single composite candidate when separate extraction is possible. Do not silently merge, delete, or choose subjects when multiple meaningful candidates exist. Treat readable or decorative text as non-subject content by default, even when it is visually prominent; include it only after the user explicitly requests it. Text printed on or inseparable from a selected physical subject is not automatically erased.

For a multi-subject result, use stable two-digit filenames such as `candidate-01.png`, `candidate-02.png`, and `candidate-03.png`. Create `candidates.json` with the same IDs and absolute file paths. The displayed candidate number, filename, preview, description, and manifest entry must refer to the same extracted subject. Keep these files outside the target folder. If the manifest is missing, a listed file is missing, the numbering is inconsistent, or a candidate fails transparent-PNG validation, stop before asking the user to choose.

### 4. Let the User Select a Subject

For multiple subjects, show every independently extracted candidate separately with its filename, number, thumbnail, and a short description. Ask the user to enter one or more candidate numbers, for example `1、3、5`; validate duplicates, out-of-range numbers, and invalid characters, then echo the resolved filenames and descriptions for confirmation. Do not treat a contact sheet alone as sufficient for selection. If interactive selection is supported, allow the user to select candidates directly, but preserve the same number-to-file mapping. If exactly one candidate is selected, continue with that candidate after confirmation. If multiple candidates are selected, first generate a separate composite preview showing the selected subjects and wait for confirmation of layout, scale, and retained elements before generating the final icon PNG. If text was explicitly requested, show it as a separately labeled text candidate or retained layer. Continue only after selection and, for multi-selection, composite-preview confirmation.

### 5. Generate and Validate Transparent PNG

Generate a new PNG without overwriting the original input. Verify that:

- the output is actually PNG;
- it contains an alpha channel and transparent background pixels;
- the intended subject remains present and reasonably intact;
- the result is suitable for display as a small folder icon.

Show the result and output location. Obtain the required confirmation before Finder modification. Keep intermediate files outside the target folder.

### 6. Prepare the Icon Application Backend

Prefer the packaged Objective-C `folder-icon-setter`, which calls the documented AppKit `NSWorkspace.setIcon` API. Build native tools locally with `scripts/build-native-tools.sh` when a compatible executable is not already available. After target and final-image confirmation, invoke:

`folder-icon-setter set-and-verify /absolute/path/to/final.png /absolute/path/to/folder`

Continue only when it exits successfully with `icon_status=verified`. This direct route does not authorize any change beyond the confirmed target folder's custom-icon metadata. After success, skip the Finder clipboard steps and continue with icon and contents verification.

If the setter exits with `nsworkspace_rejected_icon_update` or `Operation not permitted`, report the icon-write failure separately from any directory-content read restriction. Do not retry blindly. The likely boundary is macOS TCC or the host's background-process context, not the PNG. The next action must explicitly identify the required context (signed-in GUI Terminal with access to the target parent folder, or Finder UI) and must not claim that running the same helper inside the blocked WorkBuddy process will fix it.

### 6B. WorkBuddy Terminal Handoff

When the WorkBuddy host-process probe is blocked, keep the generated PNG and provide this packaged wrapper for the user to run in the already signed-in `Terminal.app`:

`/absolute/path/to/skill/scripts/terminal-apply.sh /absolute/path/to/final.png /absolute/path/to/confirmed/folder`

The wrapper validates absolute paths, builds the native helper in the Skill's `.build/` directory if needed, prints `execution_context=Terminal.app` and `scope=folder_icon_metadata_only`, then invokes `folder-icon-setter set-and-verify`. If macOS asks Terminal to access Desktop or another protected folder, the user must approve that exact request. The Skill must wait for the terminal output `icon_status=verified` before reporting the icon update as successful. If the wrapper reports `Operation not permitted` or `nsworkspace_rejected_icon_update`, stop and report the Terminal permission failure; do not repeat the same command in WorkBuddy.

The Terminal handoff does not authorize WorkBuddy to read or write the target folder's ordinary contents. If WorkBuddy cannot perform the before/after contents check, say so explicitly and let Terminal/Finder or the user perform that separate verification. The wrapper never places generated images or intermediate files inside the target folder.

Use the clipboard/Finder UI route only as an explicitly reported fallback when the direct API is unavailable or the user specifically requests the Finder UI workflow. If Finder automation permissions are unavailable, stop at the generated PNG and give the user the manual Finder steps; do not describe that state as an automatic success.

### 6A. Clipboard Fallback Only

Do not rely on a viewer's focus, a simulated copy shortcut, or a file drag as the primary automation path. On macOS, use a native clipboard bridge to clear the general pasteboard and write the selected final PNG as raster image data, exposing a Finder-compatible image representation such as PNG or TIFF. A file URL may be included as auxiliary metadata, but it must never be the only representation.

Invoke the installed bridge with `clipboard-bridge set-and-verify /absolute/path/to/final.png`. Read the pasteboard back before opening or modifying the Finder target. Continue only when the command exits successfully with `clipboard_status=verified`, the pasteboard advertises an image representation, the image can be decoded or rendered, the decoded image matches the selected final PNG by dimensions and a deterministic content comparison, and the pasteboard was written after the current final PNG was generated. If any check fails, clear and rebuild the image clipboard. Do not open Get Info or paste while the clipboard is unverified. Keep the clipboard bridge platform-specific and isolated from the platform-neutral image and safety logic.

### 7. Confirm the Target Folder

Require one user-selected or fully specified ordinary folder. Verify that it exists, remains at the confirmed path, is not an app, file, disk, network volume, system directory, or special object, and is accessible for icon metadata modification.

Show the folder name and full path. Do not continue until the target is confirmed.

### 8. Locate the Target Folder

Locate only the already confirmed folder using its full path or the currently selected Finder object. Do not fall back to ambiguous name matching. If multiple same-named folders cannot be distinguished, stop and request a full path or a new selection.

After locating it, re-check the name, full path, and object type. Do not operate on the folder's contents during locating.

### 9. Open Get Info

This and the following paste steps apply only to the clipboard/Finder UI fallback. The direct `NSWorkspace.setIcon` route skips them.

Open Get Info for the confirmed folder using the available Finder capability. Verify that the window corresponds to the confirmed folder by checking its name, path or parent context, icon, and object type. If it does not match or cannot be confirmed, stop and close the wrong window.

### 10. Select the Top Icon

Select only the small icon below the title bar at the top of the Get Info window. Do not select the larger preview icon. Continue only when a blue outline or another unambiguous selected state is visible.

If the top icon cannot be reliably distinguished or its selected state cannot be verified, stop and ask the user to select it manually.

### 11. Paste the Verified Image

After the top icon is selected, the native clipboard bridge has verified the current final PNG, and the final confirmation is complete, paste only into that icon target. Do not paste into the folder, Finder content area, or another window.

After pasting, verify that the top icon and its preview changed. If the icon remains unchanged, classify the attempt as a failed paste; do not blindly repeat it. First re-check clipboard representation, top-icon selection, window focus, Finder state, and permissions. A second paste is allowed only after the clipboard has been explicitly rebuilt as image data and the target icon has been reselected and verified. If image clipboard verification or Finder state cannot be established, stop as `部分完成` and report that the generated PNG is ready but Finder did not accept the image data.

### 12. Verify the Icon Replacement

Verify that the top icon changed to the current final PNG, not merely that it changed from its prior state. Compare the visible result and, where available, the folder icon metadata or rendered icon against the current PNG. If the icon changed but does not match the current PNG, classify the run as a wrong-image replacement, stop, and offer the explicit recovery path before any further paste. The Get Info window must still refer to the original confirmed folder.

### 13. Verify Folder Contents Were Not Changed

Compare the target folder's ordinary contents before and after the operation. Verify, as supported by the platform, that ordinary item count, names, structure, sizes, modification times, content checksums, and permissions remain unchanged. Separately record and allow system metadata required for the custom icon or Finder display, including `Icon` or `.DS_Store`. Any unexpected change to an ordinary file or subfolder is a failed run.

## Failure, Cancellation, and Recovery

On cancellation, missing authorization, wrong target, Finder failure, uncertain icon selection, failed paste, wrong-image replacement, or incomplete verification, stop immediately. Do not guess, bypass permissions, or claim success. For a failed paste specifically, preserve the generated PNG, report whether the clipboard held verified image data or only a path/file object, and do not claim that the folder icon changed. If an incorrect icon was applied, do not automatically overwrite it again; restoration of the original icon requires an explicit user request and a separately confirmed recovery action.

Retain the original image and generated PNG when available. Do not automatically reset the folder icon or clean up test and intermediate resources. Restoring the original icon requires an explicit user request.

## Platform Capability Fallback

Use platform-neutral capability descriptions. Do not assume that every agent can control Finder, remove backgrounds, inspect alpha transparency, request permissions, or verify file metadata.

If only image processing is available, complete that portion and report that Finder replacement remains incomplete. If desktop control is available but a required permission is not, ask for authorization before modifying anything. If the platform cannot confirm the safety boundary, stop.

## Final Status and Report Format

Use only these status labels: `成功`, `部分完成`, `已取消`, `失败`, `等待授权`, or `等待用户选择`.

Report:

- input image and generated PNG path;
- target folder name and full path;
- completed steps;
- incomplete or failed steps;
- current stopping point and reason;
- icon replacement status;
- contents-protection verification status;
- next action required, if any.

Use `成功` only when the icon update and ordinary-contents protection verification both pass. Report allowed system metadata separately. Never use vague wording such as “probably completed”.

## Installation Self-test

Installation and verification are separate states. File copying alone means `installed`, not `verified`. Read `references/install-validation.md` and run the packaged no-side-effect stage immediately after installation:

`python3 scripts/install-self-test.py --stage preflight --host <host> --host-version <version>`

The preflight validates package integrity, fixture hashes, native compilation, JPG decoding, Apple Vision extraction, candidate numbering, real PNG transparency, and (when extraction succeeds) an icon-write probe against a temporary copy of the bundled fixture. The probe is not a user-folder operation; it may create only allowed system metadata on that temporary copy and must verify ordinary contents remain unchanged. Preflight must report icon-write capability separately from image capability.

If preflight passes, show its report and ask the user before the isolated E2E test. Only after explicit approval run:

`python3 scripts/install-self-test.py --stage e2e --authorize-e2e --host <host> --host-version <version>`

The authorization covers only a temporary copy of the bundled fixture folder. It does not authorize a real user folder, broad macOS permissions, network dependency installation, or Finder UI control.

Use the bundled test resources:

- `tests/skill-test-image.jpg` as the JPG input;
- `tests/icon-replacement-test-folder/` as the ordinary target folder;
- `tests/skill-test-text.txt` and `tests/skill-test-document.docx` as fixed bundled resources whose contents must remain unchanged;
- `tests/icon-replacement-test-folder/test-content.txt` and `tests/icon-replacement-test-folder/nested/nested-content.txt` as target-folder contents that must remain unchanged.

Treat the bundled target fixture as a read-only master. Copy it to a unique temporary directory for E2E testing, record the copy's ordinary names, structure, sizes, modification times, checksums, and permissions, and compare them afterward. Allow only macOS/Finder system metadata required for the icon or display state, such as `Icon` or `.DS_Store`. The installation test passes only if JPG-to-transparent-PNG conversion, icon replacement, target verification, ordinary-contents protection, and final reporting all pass.

Record the Skill version and path, host and host version, macOS version, architecture, execution context, native helper hashes, check results, authorization state, and next action. Preflight reports are temporary; an authorized E2E may write its disclosed verification receipt under the user's Application Support directory. A receipt is valid only for that combination. Use `installation_status=verified` only after the isolated E2E test passes. If image processing succeeds but the icon-write probe is blocked, report `authorization-required` or `partial` with `icon-write-unavailable`; do not misreport the Skill as fully usable or the files as uninstalled.

## Completion Criteria

The task is complete only when a single confirmed ordinary folder has the intended new icon, the original input is preserved, the generated PNG is valid and transparent, no ordinary internal folder content changed, allowed system metadata is reported separately, and the final report matches the verified state.

## macOS Native Clipboard Implementation

The macOS implementation must use the bundled `macos/ClipboardBridge.m` (preferred when only Command Line Tools are available), `macos/ClipboardBridge.swift`, or an equivalent native AppKit bridge for clipboard writes. The bridge must be compiled successfully and independently tested with a real final PNG before it is used by the Finder workflow. A source file that has not compiled, or a bridge that has not passed write-and-read-back verification, is not an available capability. If the selected toolchain is incompatible with the macOS SDK, stop before Finder paste and report the toolchain mismatch.
