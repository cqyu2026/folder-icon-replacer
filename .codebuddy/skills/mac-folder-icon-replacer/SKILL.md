---
name: mac-folder-icon-replacer
description: Replace one user-confirmed macOS folder icon from an input image by creating a transparent PNG and applying it through Finder, while never modifying ordinary files or subfolders inside the target folder.
---

# WorkBuddy Adapter

This is the WorkBuddy workspace discovery entry for the shared skill.

Before acting, load and follow the canonical instructions in:

`mac-folder-icon-replacer/SKILL.md`

Treat that file as authoritative for:

- capability and permission preflight;
- user authorization and confirmation checkpoints;
- JPG/JPEG/PNG input handling and transparent PNG generation;
- multiple-subject extraction and user selection;
- Finder and clipboard safety;
- the rule that ordinary files and subfolders inside the target folder are read-only;
- allowed macOS/Finder metadata such as `Icon` and `.DS_Store`;
- post-operation verification and final status reporting.

If the canonical file cannot be read, stop and report that the Skill is not safely loadable. Do not proceed using this adapter alone.
