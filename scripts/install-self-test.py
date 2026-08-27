#!/usr/bin/env python3
"""Deterministic post-install validation for mac-folder-icon-replacer."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


EXIT_FAILED = 1
EXIT_AUTHORIZATION_REQUIRED = 3
ALLOWED_METADATA = {".DS_Store", "Icon\r"}


class ValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown command failure"
        raise ValidationError(f"command failed ({result.returncode}): {' '.join(command)}: {stderr}")
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc


def inspect_image(inspector: Path, image: Path) -> dict[str, Any]:
    result = run([str(inspector), str(image.resolve())])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"image inspector returned invalid JSON for {image}") from exc


def validate_candidates(inspector: Path, candidate_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = read_json(candidate_dir / "candidates.json")
    candidates = manifest.get("candidates", [])
    if not candidates:
        raise ValidationError("Apple Vision produced no candidate files")
    candidate_checks: list[dict[str, Any]] = []
    for candidate in candidates:
        path = Path(candidate["path"])
        if path.name != f"candidate-{int(candidate['id']):02d}.png":
            raise ValidationError("candidate number and filename mapping is inconsistent")
        info = inspect_image(inspector, path)
        if not info.get("is_png") or not info.get("has_transparent_pixels") or not info.get("has_visible_pixels"):
            raise ValidationError(f"candidate is not a valid transparent PNG: {path.name}")
        candidate_checks.append({"id": candidate["id"], "path": str(path), "image": info})
    return manifest, candidate_checks


def verify_fixtures(skill_dir: Path) -> dict[str, Any]:
    tests_dir = skill_dir / "tests"
    manifest_path = tests_dir / "manifest.json"
    manifest = read_json(manifest_path)
    verified: list[dict[str, str]] = []
    for relative, expected_hash in manifest.get("files", {}).items():
        path = tests_dir / relative
        if not path.is_file():
            raise ValidationError(f"missing fixture: {relative}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise ValidationError(f"fixture hash mismatch: {relative}")
        verified.append({"path": relative, "sha256": actual_hash})
    return {
        "manifest": str(manifest_path),
        "fixture_version": manifest.get("fixture_version"),
        "verified_files": verified,
    }


def snapshot_ordinary_contents(root: Path) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ALLOWED_METADATA for part in relative.parts):
            continue
        info = path.lstat()
        entry: dict[str, Any] = {
            "kind": "directory" if path.is_dir() else "file",
            "mode": stat.S_IMODE(info.st_mode),
            "mtime_ns": info.st_mtime_ns,
        }
        if path.is_file():
            entry["size"] = info.st_size
            entry["sha256"] = sha256(path)
        snapshot[str(relative)] = entry
    return snapshot


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return cleaned or "unknown"


def report_path_from_arg(value: str | None, args: argparse.Namespace, skill_dir: Path) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    if args.stage == "e2e" and args.authorize_e2e:
        version_path = skill_dir / "VERSION"
        version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "unknown"
        filename = "-".join([
            safe_component(args.host),
            safe_component(version),
            safe_component(platform.machine()),
        ]) + ".json"
        return Path.home() / "Library" / "Application Support" / "folder-icon-replacer" / "verification" / filename
    return Path(tempfile.gettempdir()) / f"folder-icon-replacer-verification-{uuid.uuid4().hex}.json"


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def base_report(args: argparse.Namespace, skill_dir: Path) -> dict[str, Any]:
    version_path = skill_dir / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "unknown"
    return {
        "schema_version": 1,
        "skill": "mac-folder-icon-replacer",
        "skill_version": version,
        "skill_path": str(skill_dir),
        "host": args.host,
        "host_version": args.host_version,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "system": {
            "platform": platform.system(),
            "macos_version": platform.mac_ver()[0],
            "architecture": platform.machine(),
        },
        "requested_stage": args.stage,
        "installation_status": "failed",
        "completed_level": "none",
        "checks": {},
        "required_authorizations": [],
        "errors": [],
    }


def run_preflight(skill_dir: Path, work_dir: Path, report: dict[str, Any]) -> dict[str, Path]:
    if platform.system() != "Darwin":
        raise ValidationError("this skill requires macOS")
    required_paths = [
        skill_dir / "SKILL.md",
        skill_dir / "VERSION",
        skill_dir / "scripts" / "build-native-tools.sh",
        skill_dir / "macos" / "ImageInspector.m",
        skill_dir / "macos" / "ForegroundExtractor.m",
        skill_dir / "macos" / "ForegroundExtractor-Info.plist",
        skill_dir / "macos" / "FolderIconSetter.m",
        skill_dir / "tests" / "manifest.json",
    ]
    missing = [str(path.relative_to(skill_dir)) for path in required_paths if not path.is_file()]
    if missing:
        raise ValidationError(f"package is incomplete: {', '.join(missing)}")

    report["checks"]["package"] = {"status": "verified", "required_files": len(required_paths)}
    report["checks"]["fixtures"] = {"status": "verified", **verify_fixtures(skill_dir)}

    clang = shutil.which("clang")
    if not clang:
        raise ValidationError("Apple Command Line Tools clang is unavailable")
    report["checks"]["toolchain"] = {"status": "verified", "clang": clang}

    bin_dir = work_dir / "bin"
    build = run(["/bin/sh", str(skill_dir / "scripts" / "build-native-tools.sh"), str(bin_dir)])
    expected_tools = {
        "clipboard_bridge": bin_dir / "clipboard-bridge",
        "image_inspector": bin_dir / "image-inspector",
        "foreground_extractor": bin_dir / "foreground-extractor",
        "folder_icon_setter": bin_dir / "folder-icon-setter",
    }
    for path in expected_tools.values():
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValidationError(f"native tool was not built: {path.name}")
    extractor_app = bin_dir / "foreground-extractor.app"
    extractor_app_binary = extractor_app / "Contents" / "MacOS" / "foreground-extractor"
    if not extractor_app_binary.is_file() or not os.access(extractor_app_binary, os.X_OK):
        raise ValidationError("foreground extractor app bundle was not built")
    report["checks"]["native_build"] = {
        "status": "verified",
        "stdout": build.stdout.strip(),
        "tools": {name: {"path": str(path), "sha256": sha256(path)} for name, path in expected_tools.items()},
        "gui_helper": {"path": str(extractor_app), "sha256": sha256(extractor_app_binary)},
    }

    input_image = skill_dir / "tests" / "skill-test-image.jpg"
    source_info = inspect_image(expected_tools["image_inspector"], input_image)
    if source_info.get("is_png") or source_info.get("has_transparent_pixels"):
        raise ValidationError("the JPG test input is unexpectedly transparent or encoded as PNG")
    report["checks"]["jpg_input"] = {"status": "verified", **source_info}

    candidate_dir = work_dir / "candidates"
    try:
        extraction = run([
            str(expected_tools["foreground_extractor"]),
            "extract",
            str(input_image.resolve()),
            str(candidate_dir.resolve()),
        ])
        manifest, candidate_checks = validate_candidates(expected_tools["image_inspector"], candidate_dir)
        report["checks"]["foreground_extraction"] = {
            "status": "verified",
            "execution_context": "host-process",
            "stdout": extraction.stdout.strip(),
            "backend": manifest.get("backend"),
            "manifest": str(candidate_dir / "candidates.json"),
            "candidates": candidate_checks,
        }
        report["completed_level"] = "capability-ready"
    except ValidationError as exc:
        if "ANECF" not in str(exc) and "ANE model" not in str(exc):
            raise
        report["checks"]["foreground_extraction"] = {
            "status": "deferred",
            "execution_context": "host-process",
            "reason": "Apple Vision subject lifting is unavailable in this host process; retry in the signed-in GUI session during authorized E2E.",
            "detail": str(exc),
            "gui_helper": str(extractor_app),
        }
        report["completed_level"] = "native-ready"
    report["installation_status"] = "authorization-required"
    report["required_authorizations"] = [
        {
            "id": "isolated-e2e-icon-test",
            "reason": "If needed, run Apple Vision in the signed-in GUI session, then set and verify a custom icon only on a temporary fixture copy.",
            "scope": "temporary fixture copy; no user folder",
            "required_flag": "--authorize-e2e",
        }
    ]
    return expected_tools


def run_e2e(
    skill_dir: Path,
    work_dir: Path,
    report: dict[str, Any],
    tools: dict[str, Path],
) -> None:
    fixture_source = skill_dir / "tests" / "icon-replacement-test-folder"
    fixture_copy = work_dir / "e2e" / "icon-replacement-test-folder"
    fixture_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture_source, fixture_copy, copy_function=shutil.copy2)

    before = snapshot_ordinary_contents(fixture_copy)
    foreground_check = report["checks"]["foreground_extraction"]
    if foreground_check.get("status") != "verified":
        input_image = skill_dir / "tests" / "skill-test-image.jpg"
        candidate_dir = work_dir / "candidates-gui"
        extractor_app = work_dir / "bin" / "foreground-extractor.app"
        run([
            "/usr/bin/open",
            "-W",
            "-n",
            str(extractor_app),
            "--args",
            "extract",
            str(input_image.resolve()),
            str(candidate_dir.resolve()),
        ])
        manifest, candidate_checks = validate_candidates(tools["image_inspector"], candidate_dir)
        report["checks"]["foreground_extraction"] = {
            "status": "verified",
            "execution_context": "signed-in-gui-session",
            "backend": manifest.get("backend"),
            "manifest": str(candidate_dir / "candidates.json"),
            "candidates": candidate_checks,
        }
    candidates = report["checks"]["foreground_extraction"]["candidates"]
    selected = Path(candidates[0]["path"])
    icon_result = run([
        str(tools["folder_icon_setter"]),
        "set-and-verify",
        str(selected.resolve()),
        str(fixture_copy.resolve()),
    ])
    after = snapshot_ordinary_contents(fixture_copy)
    if before != after:
        raise ValidationError("ordinary fixture contents changed during icon replacement")

    generated_metadata = sorted(
        str(path.relative_to(fixture_copy))
        for path in fixture_copy.rglob("*")
        if path.name in ALLOWED_METADATA
    )
    report["checks"]["isolated_e2e"] = {
        "status": "verified",
        "target": str(fixture_copy),
        "selected_candidate": str(selected),
        "icon_setter_output": icon_result.stdout.strip(),
        "ordinary_contents_unchanged": True,
        "ordinary_entries": len(before),
        "allowed_system_metadata": generated_metadata,
    }
    report["required_authorizations"] = []
    report["completed_level"] = "verified"
    report["installation_status"] = "verified"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a mac-folder-icon-replacer installation.")
    parser.add_argument("--stage", choices=("preflight", "e2e"), default="preflight")
    parser.add_argument("--authorize-e2e", action="store_true", help="Authorize icon mutation on a temporary fixture copy only.")
    parser.add_argument("--host", default="unknown")
    parser.add_argument("--host-version", default="unknown")
    parser.add_argument("--report")
    parser.add_argument("--keep-workdir", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    report_path = report_path_from_arg(args.report, args, skill_dir)
    work_dir = Path(tempfile.mkdtemp(prefix="folder-icon-replacer-self-test-"))
    report = base_report(args, skill_dir)
    exit_code = EXIT_FAILED
    preserve_workdir = True

    try:
        tools = run_preflight(skill_dir, work_dir, report)
        if args.stage == "e2e":
            if not args.authorize_e2e:
                report["installation_status"] = "authorization-required"
                report["next_action"] = "Ask the user, then rerun with --stage e2e --authorize-e2e."
                exit_code = EXIT_AUTHORIZATION_REQUIRED
            else:
                run_e2e(skill_dir, work_dir, report, tools)
                report["next_action"] = "Installation verification is complete for this host and Mac."
                exit_code = 0
                preserve_workdir = args.keep_workdir
        else:
            report["next_action"] = "Ask the user before running the isolated e2e icon test."
            exit_code = 0
    except ValidationError as exc:
        report["errors"].append(str(exc))
        report["installation_status"] = "failed"
        report["next_action"] = "Resolve the reported failure and rerun the same stage."
        exit_code = EXIT_FAILED
    except Exception as exc:  # Defensive reporting for unexpected host failures.
        report["errors"].append(f"unexpected error: {type(exc).__name__}: {exc}")
        report["installation_status"] = "failed"
        report["next_action"] = "Inspect the report and preserve the work directory for diagnosis."
        exit_code = EXIT_FAILED

    report["work_directory"] = str(work_dir) if preserve_workdir else None
    write_report(report_path, report)
    if not preserve_workdir:
        shutil.rmtree(work_dir)
    print(f"installation_status={report['installation_status']}")
    print(f"completed_level={report['completed_level']}")
    print(f"report={report_path}")
    if preserve_workdir:
        print(f"work_directory={work_dir}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
