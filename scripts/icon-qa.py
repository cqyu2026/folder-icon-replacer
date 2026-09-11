#!/usr/bin/env python3
"""Validate final icon PNGs and export thumbnail previews using macOS tools."""
from __future__ import annotations

import argparse
import importlib
import sys
import json
import subprocess
import tempfile
from pathlib import Path


gate = importlib.import_module("portable-icon-gate")


class QaError(RuntimeError):
    pass


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise QaError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result


def build_inspector(skill_dir: Path) -> Path:
    (skill_dir / ".build").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="qa-", dir=skill_dir / ".build")) / "image-inspector"
    run([
        "clang", "-fobjc-arc", "-framework", "Foundation", "-framework", "ImageIO", "-framework", "CoreGraphics",
        str(skill_dir / "macos" / "ImageInspector.m"), "-o", str(output),
    ])
    return output


def inspect(inspector: Path, image: Path) -> dict[str, object]:
    return json.loads(run([str(inspector), str(image)]).stdout)


def validate(info: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if not info.get("is_png"):
        errors.append("not_png")
    if (info.get("width"), info.get("height")) != (1024, 1024):
        errors.append("not_1024_square")
    if not info.get("has_transparent_pixels") or not info.get("has_visible_pixels"):
        errors.append("missing_visible_or_transparent_pixels")
    if any(value != 0 for value in info.get("corner_alpha", [])):
        errors.append("opaque_corner")
    coverage = float(info.get("visible_coverage", 1))
    if coverage < 0.15 or coverage > 0.72:
        errors.append("visible_coverage_out_of_range")
    if bool(info.get("touches_canvas_edge")):
        errors.append("subject_touches_canvas_edge")
    return errors


def export_preview(image: Path, output: Path, size: int) -> Path:
    destination = output / f"{image.stem}-{size}.png"
    output.mkdir(parents=True, exist_ok=True)
    run(["sips", "-s", "format", "png", "-z", str(size), str(size), str(image), "--out", str(destination)])
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a 1024 px transparent final icon.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--preview-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    image = args.image.resolve()
    skill_dir = Path(__file__).resolve().parent.parent

    if not image.is_file():
        print(json.dumps({"status": "failed", "errors": ["image_missing"]}, ensure_ascii=False))
        return 1
    try:
        info = inspect(build_inspector(skill_dir), image)
        errors = validate(info) + gate.assess(image)["errors"]
        previews = gate.previews(image, args.preview_dir) if not errors else []
        report = {"status": "technical_pass" if not errors else "failed", "image": str(image), "inspection": info, "errors": errors, "previews": previews}
    except (OSError, QaError, json.JSONDecodeError) as error:
        report = {"status": "failed", "image": str(image), "errors": [str(error)]}

    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "technical_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
