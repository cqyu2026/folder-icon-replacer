#!/usr/bin/env python3
"""Create deterministic synthetic fixtures; never process user artwork."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ICONS = [
    ("sun-pedestal", "工作", "red circle above yellow pedestal"),
    ("sun-orbit", "项目", "red circle with yellow orbit"),
    ("pedestal-sun", "素材", "yellow pedestal carrying red circle"),
    ("sun-marker", "下载", "red circle with yellow marker"),
    ("sun-stack", "归档", "stacked red circles on yellow base"),
]


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")


def svg_for(index: int) -> str:
    drawings = [
        '<circle cx="512" cy="430" r="235" fill="#E74538"/><rect x="390" y="625" width="244" height="185" rx="18" fill="#F9C23B"/>',
        '<circle cx="512" cy="480" r="220" fill="#E74538"/><path d="M270 540C315 745 690 755 760 490" fill="none" stroke="#F9C23B" stroke-width="70" stroke-linecap="round"/>',
        '<rect x="315" y="585" width="394" height="205" rx="28" fill="#F9C23B"/><circle cx="512" cy="425" r="210" fill="#E74538"/>',
        '<circle cx="485" cy="470" r="230" fill="#E74538"/><path d="M682 285h102v102H682z" fill="#F9C23B"/><path d="M720 320v64M688 352h64" stroke="#2E6CB4" stroke-width="18" stroke-linecap="round"/>',
        '<rect x="315" y="650" width="394" height="150" rx="24" fill="#F9C23B"/><circle cx="435" cy="465" r="170" fill="#E74538"/><circle cx="600" cy="465" r="170" fill="#D83B31"/>',
    ][index]
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><g>{drawings}</g></svg>'


def wallpaper_svg() -> str:
    return '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><rect width="1920" height="1080" fill="#2E6CB4"/><circle cx="1330" cy="465" r="285" fill="#E74538"/><rect x="1180" y="705" width="300" height="220" rx="24" fill="#F9C23B"/></svg>'


def rasterize(svg: Path, output: Path, width: int, height: int) -> None:
    run(["sips", "-s", "format", "png", "-z", str(height), str(width), str(svg), "--out", str(output)])


def qa_icon(skill_dir: Path, icon: Path, root: Path) -> dict[str, object]:
    result = subprocess.run([
        sys.executable, str(skill_dir / "scripts" / "icon-qa.py"), str(icon),
        "--preview-dir", str(root / "source-pack" / "previews"),
        "--report", str(root / "source-pack" / "qa" / f"{icon.stem}.json"),
    ], text=True, capture_output=True, check=False)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic MVP material pack.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fixture-only", action="store_true", help="required acknowledgement that this is test-fixture generation")
    args = parser.parse_args()
    source = args.source.resolve()
    root = args.output.resolve()
    if not args.fixture_only:
        raise SystemExit("build-mvp-pack.py only creates test fixtures; use --fixture-only for packaged validation, never user artwork")
    fixture_source = (Path(__file__).resolve().parent.parent / "tests" / "skill-test-image.jpg").resolve()
    if source != fixture_source:
        raise SystemExit("build-mvp-pack.py only accepts the packaged tests/skill-test-image.jpg fixture")
    if not source.is_file():
        raise SystemExit("source image is missing")
    if root.exists():
        raise SystemExit(f"output already exists: {root}")

    final = root / "final-pack"
    generations = root / "source-pack" / "generations"
    final.mkdir(parents=True)
    generations.mkdir(parents=True)
    skill_dir = Path(__file__).resolve().parent.parent
    shutil.copy2(source, generations / source.name)

    wallpaper_source = generations / "wallpaper.svg"
    wallpaper_source.write_text(wallpaper_svg(), encoding="utf-8")
    rasterize(wallpaper_source, final / "final-wallpaper.png", 1920, 1080)

    icons: list[dict[str, str]] = []
    for index, (slug, meaning, signature) in enumerate(ICONS, start=1):
        svg = generations / f"icon-{index:02d}-{slug}.svg"
        svg.write_text(svg_for(index - 1), encoding="utf-8")
        icon = generations / f"icon-{index:02d}.png"
        rasterize(svg, icon, 1024, 1024)
        qa = qa_icon(skill_dir, icon, root)
        icons.append({"file": icon.name, "meaning": meaning, "concept_signature": signature, "technical_qa": qa["status"]})

    manifest = {
        "schema_version": 1,
        "source_image": source.name,
        "mode": "visual-dna",
        "wallpaper": "final-wallpaper.png",
        "icons": icons,
        "note": "Suggested meanings are design labels and do not identify real folders.",
    }
    (root / "source-pack" / "manifest.md").write_text(
        "# MVP Material Pack\n\n```json\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "awaiting_visual_review", "pack": str(root), "icons": icons}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
