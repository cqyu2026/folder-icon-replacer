---
name: mac-folder-icon-replacer
description: Set one confirmed ordinary macOS folder's custom icon from a verified transparent PNG, or extract a JPEG subject using available macOS tools. Also supports explicitly requested matching icon packs. Reject background residue before delivery or application.
---

# Mac Folder Icon Replacer

Use the installed directory containing this file as the package root. All linked scripts and resources are relative to it; do not assume a project checkout, a host-specific environment variable, or a particular agent tool name. Read [platform installation](compatibility/platform-install.md) when installing or diagnosing discovery.

## Scope and capabilities

Use one readable local image and one user-confirmed absolute ordinary folder path. If the user has not chosen direct image use or a material pack, ask for that choice once. An existing choice or explicit direct replacement request is sufficient. Do not infer a folder from a suggested icon meaning. Never read, enumerate, or write the target's ordinary contents. Reject App bundles, other packages, protected paths, symlinks, mount points, and nonlocal volumes.

Detect file access, a command runner, Python 3, preview viewing, host OS, and native build availability independently. Skill loading does not supply these capabilities. If Python is present, run [scripts/install-self-test.py](scripts/install-self-test.py) with `--stage preflight`; native-ready proves compilation only. Actual extraction must succeed to establish Vision availability.

- With Python but without local macOS extraction: accept only a PNG that passes the portable gate and actual preview review. Reject JPEG and request a transparent PNG or a Mac with the bundled Vision/ImageIO pipeline.
- Without Python, file access, or a way to view previews: stop automatic processing and application. Ask for an already verified transparent PNG and completion in an environment that can run the gate. A filename, claimed transparency, or checkerboard screenshot is not evidence.
- macOS writes require Python 3, the packaged native sources, working Apple Command Line Tools and NSWorkspace permission. Other operating systems can validate PNGs but cannot set a remote Mac's Finder metadata.
- Do not install dependencies implicitly or substitute an unverified image tool when native extraction fails.

## Prepare and review — mandatory for both routes

Run [scripts/prepare-icon.py](scripts/prepare-icon.py) with the absolute input path and a **new staging directory outside the target**. This preserves the original, uses existing Vision extraction and ImageIO normalization for JPEG on capable Macs, rejects JPEG elsewhere, quarantines technical failures, and exports review previews. A PNG fallback must be 8-bit RGBA, noninterlaced, at most 2048 px per side; unsupported encodings are rejected, never presumed safe.

Read [references/quality-gate.md](references/quality-gate.md). Real alpha, bounded coverage, transparent canvas edges, connected-component/color rectangle checks, isolated edge pixels and visual review are all mandatory. **Technical pass alone cannot authorize output or application.** Review the source alongside the candidate on light, dark and checker backgrounds at 1024, 128 and 64 px. Inspect the white folder's interior as well as its silhouette: no purple rectangle, source-colored pixels, text or unwanted composition may remain. Check subject integrity and color fringes. When uncertain, reject or leave quarantined; do not select, offer as final, apply, or provide a manual application command.

After actually viewing the previews, record the review described in the reference at `<candidate.png>.review.json`, bound to that candidate's SHA-256. Do not fabricate or auto-fill visual approval from technical scores. A user selecting a filename, target folder, or proposed concept does not by itself approve the review fields. A user who can view the previews may perform the review when the agent cannot; otherwise stop. Run [scripts/portable-icon-gate.py](scripts/portable-icon-gate.py) on the candidate with `--require-review`; only `status=passed` is eligible for delivery/application. Any modification invalidates the review and requires checking again. Even a small background patch below the automatic detector threshold must be rejected in the actual preview review; a technical pass cannot substitute for explicit visual approval.

## Material pack

Only when requested, read [references/material-pack.md](references/material-pack.md). Use the same mandatory candidate gate. The deterministic MVP builder is a test fixture generator, not a general image-generation capability. It may only run with its explicit fixture-only switch and may never be used with user photos or as a source of deliverable artwork. If no approved image-generation or image-editing capability is available, report that limitation; do not install a dependency, write an ad-hoc crop/mask pipeline, or substitute an unverified image tool.

The 15–72% visible-coverage check detects opaque backdrops and background residue. It is not an art direction, and it does not require or prefer circles, circular crops, masks, rounded rectangles, or any other shape. Preserve the user's explicitly requested composition. Do not add a crop, mask, frame, or shape treatment unless the user expressly asks for it and the current image tool can produce and preview it.

Also review all icons with the wallpaper for consistent palette, medium, contours, texture, lighting and abstraction at native size and 64 px. Record `visual_qa` in `source-pack/visual-qa.json`; run [scripts/qualify-pack.py](scripts/qualify-pack.py) to copy only approved files and their review sidecars into `final-pack/`. Failed candidates go to `source-pack/rejected/`. Show only qualified icons as selectable; then obtain one icon selection and one absolute target path.

## Apply

State the qualified image, confirmed target and icon-metadata-only scope before writing. Existing authorization remains valid. Run:

```sh
python3 /absolute/installed/skill/scripts/apply-icon.py /absolute/approved.png /absolute/ordinary-folder
```

The adjacent `approved.png.review.json` is required. Both wrapper and native writer enforce the shared gate and bind the actual loaded bytes to its approved SHA-256. Promotion revalidates staged byte snapshots before atomic publication. A source/review change after QA must stop or quarantine the candidate. Never use an old cached writer, bypass QA via Finder/clipboard, edit checks to force acceptance, or apply the original JPEG. Rebuild after moving/updating an installation; compiled tools are local build products, not portable package resources.

Success requires NSWorkspace write and readback; `already_selected` is also a successful no-change result. Permission denial permits Finder manual steps **only for the same qualified PNG**. Uncertain readback/identity means stop without retry/rollback. Report that internal contents were not read or integrity-verified.

## Validation

Use [references/install-validation.md](references/install-validation.md) and packaged fixtures only. Temporary icon writes are isolated from real user targets. Never mistake test fixture attestations or historical host records for approval of a user's candidate.
