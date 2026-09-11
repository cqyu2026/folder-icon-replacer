#!/usr/bin/env python3
"""Validate the current narrow icon-writing installation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ALLOWED_METADATA = {".DS_Store", "Icon\r"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ALLOWED_METADATA for part in relative.parts):
            continue
        info = path.lstat()
        entry: dict[str, object] = {"mode": stat.S_IMODE(info.st_mode), "kind": "directory" if path.is_dir() else "file"}
        if path.is_file():
            entry["sha256"] = sha256(path)
        result[str(relative)] = entry
    return result


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def fixture_hashes(skill_dir: Path) -> list[str]:
    manifest = json.loads((skill_dir / "tests" / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    for relative, expected in manifest["files"].items():
        path = skill_dir / "tests" / relative
        if not path.is_file() or sha256(path) != expected:
            errors.append(relative)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate current mac-folder-icon-replacer installation.")
    parser.add_argument("--stage", choices=("preflight", "e2e"), default="preflight")
    parser.add_argument("--authorize-e2e", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    report_path = args.report or skill_dir / ".build" / "install-report.json"
    report: dict[str, object] = {"stage": args.stage, "status": "failed", "checks": {}}

    errors = fixture_hashes(skill_dir)
    report["checks"]["fixtures"] = {"passed": not errors, "errors": errors}
    report["capabilities"] = {"python": sys.version.split()[0], "host_os": sys.platform,
        "clang": shutil.which("clang"), "sips": shutil.which("sips"),
        "macos_version": platform.mac_ver()[0], "visual_review": "must_be_confirmed_in_host"}
    (skill_dir / ".build").mkdir(exist_ok=True)
    if sys.platform != "darwin" or not shutil.which("clang"):
        report["status"] = "portable-only"
        report["next_action"] = "只接受经过 portable QA 和预览审查的透明 PNG；JPEG 需要支持 Vision/ImageIO 的 Mac。当前不能自动写入 macOS 图标。"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    build_dir = Path(tempfile.mkdtemp(prefix="install-", dir=skill_dir / ".build")) / "bin"
    build = run(["/bin/sh", str(skill_dir / "scripts" / "build-icon-setter.sh"), str(build_dir)])
    setter = build_dir / "folder-icon-setter"
    report["checks"]["native_build"] = {"passed": build.returncode == 0 and setter.is_file(), "output": build.stdout.strip() or build.stderr.strip()}
    syntax = run([sys.executable, "-m", "py_compile", str(skill_dir / "scripts" / "apply-icon.py"), str(skill_dir / "scripts" / "icon-qa.py")])
    report["checks"]["python"] = {"passed": syntax.returncode == 0, "output": syntax.stderr.strip()}

    if not all(check["passed"] for check in report["checks"].values()):
        report["status"] = "failed"
    elif args.stage == "preflight":
        report["status"] = "native-ready"
        report["next_action"] = "Run e2e with --authorize-e2e to change only a temporary fixture copy."
    elif not args.authorize_e2e:
        report["status"] = "authorization-required"
    else:
        work_dir = Path(tempfile.mkdtemp(prefix=".folder-icon-replacer-e2e-", dir=skill_dir))
        target = work_dir / "icon-replacement-test-folder"
        shutil.copytree(skill_dir / "tests" / "icon-replacement-test-folder", target, copy_function=shutil.copy2)
        before = snapshot(target)
        sys.path.insert(0, str(skill_dir / "tests"))
        from png_fixtures import fixture, approve_fixture
        image = fixture(work_dir / "synthetic.png", size=1024)
        approve_fixture(image)
        write = run([str(setter), "set-and-verify", str(image), str(target)])
        unchanged = snapshot(target) == before
        report["checks"]["isolated_icon_write"] = {
            "passed": write.returncode == 0 and "icon_status=verified" in write.stdout and unchanged,
            "icon_readback": "icon_status=verified" in write.stdout,
            "fixture_contents_unchanged": unchanged,
            "output": write.stdout.strip() or write.stderr.strip(),
        }
        report["status"] = "verified" if report["checks"]["isolated_icon_write"]["passed"] else "failed"
        shutil.rmtree(work_dir)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"native-ready", "verified"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
