#!/usr/bin/env python3
"""Choose the smallest material-pack route from explicit visual inventory."""
from __future__ import annotations

import argparse
import json


def plan(anchor_count: int, requested_count: int, force_folder_semantics: bool = False) -> dict[str, object]:
    if anchor_count < 0 or requested_count < 1:
        raise ValueError("anchor_count must be >= 0 and requested_count must be >= 1")
    if force_folder_semantics or anchor_count == 0:
        mode = "folder_semantic"
        reason = "no usable anchor" if anchor_count == 0 else "user selected folder semantics"
    elif anchor_count >= requested_count:
        mode = "independent_elements"
        reason = "usable anchors cover requested icon count"
    else:
        mode = "anchor_narrative"
        reason = "anchors are insufficient; reuse one anchor with distinct poses and action parts"
    return {
        "mode": mode,
        "requested_count": requested_count,
        "anchor_count": anchor_count,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a wallpaper-folder icon pack route.")
    parser.add_argument("--anchors", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--folder-semantics", action="store_true")
    args = parser.parse_args()
    try:
        result = plan(args.anchors, args.count, args.folder_semantics)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
