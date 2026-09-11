#!/usr/bin/env python3
"""Promote only explicitly approved candidates into final-pack."""
from __future__ import annotations

import argparse
import importlib
import sys
import json
import shutil
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
gate = importlib.import_module("portable-icon-gate")


def qualify(root: Path, route: str, source: str, selected: str | None = None) -> dict[str, object]:
    source_dir = root / "source-pack"
    final_dir = root / "final-pack"
    rejected_dir = source_dir / "rejected"
    final_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    decisions = json.loads((source_dir / "visual-qa.json").read_text(encoding="utf-8"))
    icons = []
    for item in decisions["icons"]:
        if Path(item["file"]).name != item["file"]:
            raise ValueError("candidate must be a plain filename")
        candidate = source_dir / "generations" / item["file"]
        destination = final_dir / item["file"]
        review = Path(str(candidate) + ".review.json")
        qa = gate.assess(candidate, review)
        approved = qa["status"] == "passed" and item.get("visual_qa") == "passed"
        if approved:
            # Publish only the exact bytes whose image and review hashes passed QA.
            image_data, review_data = candidate.read_bytes(), review.read_bytes()
            approved = (gate.hashlib.sha256(image_data).hexdigest() == qa["sha256"] and
                        gate.hashlib.sha256(review_data).hexdigest() == qa["review_sha256"])
            if not approved:
                qa["errors"].append("candidate_or_review_changed_after_qa")
            else:
                with tempfile.TemporaryDirectory(prefix="qualified-", dir=source_dir) as temp:
                    staged = Path(temp) / candidate.name
                    staged_review = Path(temp) / (candidate.name + ".review.json")
                    staged.write_bytes(image_data)
                    staged_review.write_bytes(review_data)
                    checked = gate.assess(staged, staged_review)
                    approved = checked["status"] == "passed" and checked["sha256"] == qa["sha256"] and checked.get("review_sha256") == qa["review_sha256"]
                    if approved:
                        staged_review.replace(Path(str(destination) + ".review.json"))
                        staged.replace(destination)
                    else:
                        qa["errors"].append("staged_bytes_changed_after_qa")
        if not approved:
            destination.unlink(missing_ok=True)
            Path(str(destination) + ".review.json").unlink(missing_ok=True)
            shutil.copy2(candidate, rejected_dir / item["file"])
        icons.append({**item, "final_qualification": "passed" if approved else "rejected",
                      "rejection_reason": None if approved else item.get("rejection_reason") or "; ".join(qa["errors"]) or "visual_qa_failed"})
    manifest = {"schema_version": 2, "route": route, "input": source,
                "selected_icon": selected, "anchor": decisions.get("anchor"),
                "icons": icons, "wallpaper": decisions.get("wallpaper"),
                "pack_qa": "passed" if all(i["final_qualification"] == "passed" for i in icons) else "failed"}
    (final_dir / "manifest.md").write_text("# Material Pack Manifest\n\n```json\n" +
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--route", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--selected")
    args = parser.parse_args()
    result = qualify(args.root.resolve(), args.route, args.source, args.selected)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pack_qa"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
