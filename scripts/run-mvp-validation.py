#!/usr/bin/env python3
"""Run the two approved MVP routes against copied packaged fixtures only."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import sys
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


def execute(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = ["# mac-folder-icon-replacer MVP 验证报告", ""]
    for name, route in report["routes"].items():
        lines.extend([
            f"## {name}", "",
            f"- 输入：`{route['input']}`",
            f"- 目标：`{route['target']}`",
            f"- 图标：`{route['icon']}`",
            f"- 写入状态：`{route['status']}`",
            f"- 图标读回：`{route['icon_readback']}`",
            f"- 夹具普通内容未变化：`{route['fixture_contents_unchanged']}`",
            f"- 输出：`{route['output']}`", "",
        ])
    lines.extend(["## 安全拒绝检查", ""])
    for name, check in report["safety_checks"].items():
        lines.append(f"- {name}：`{'通过' if check['passed'] else '失败'}`")
    lines.append("")
    lines.extend(["## 已知限制", "", "- 生产替换流程不读取或验证目标文件夹内部内容；内容检查仅存在于本隔离测试夹具。", "- 素材包为视觉 DNA MVP，验证路由、QA 与应用衔接，不代表通用 AI 图像生成质量。", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate direct-image and material-pack MVP routes.")
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(skill_dir / "tests"))
    from png_fixtures import fixture, approve_fixture
    import importlib
    qualify = importlib.import_module("qualify-pack")
    fixture_source = skill_dir / "tests" / "icon-replacement-test-folder"
    jpg = skill_dir / "tests" / "skill-test-image.jpg"
    transparent_png = args.runtime.resolve() / "synthetic-transparent.png"
    runtime = args.runtime.resolve()
    output = args.output.resolve()
    pack = output / "generated-pack"

    for path in (runtime, output):
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing MVP path: {path}")

    runtime.mkdir(parents=True)
    fixture(transparent_png, size=1024)
    approve_fixture(transparent_png)
    output.mkdir(parents=True)
    direct_target = runtime / "direct-target"
    pack_target = runtime / "pack-target"
    shutil.copytree(fixture_source, direct_target, copy_function=shutil.copy2)
    shutil.copytree(fixture_source, pack_target, copy_function=shutil.copy2)
    direct_before = snapshot(direct_target)
    pack_before = snapshot(pack_target)

    direct = execute([sys.executable, str(skill_dir / "scripts" / "apply-icon.py"), str(transparent_png), str(direct_target)])
    pack_build = execute([sys.executable, str(skill_dir / "scripts" / "build-mvp-pack.py"), str(jpg), str(pack), "--fixture-only"])
    if pack_build.returncode:
        raise SystemExit(pack_build.stderr.strip() or pack_build.stdout.strip())
    qa_results: list[dict[str, object]] = []
    for icon in sorted((pack / "source-pack" / "generations").glob("icon-*.png")):
        qa = execute([sys.executable, str(skill_dir / "scripts" / "icon-qa.py"), str(icon), "--preview-dir", str(pack / "source-pack" / "previews"), "--report", str(pack / "source-pack" / "qa" / f"{icon.stem}.json")])
        qa_results.append({"icon": str(icon), "returncode": qa.returncode, "stdout": qa.stdout, "stderr": qa.stderr})
    # Only the fixed synthetic MVP drawings use test attestations.
    decisions = {"icons": []}
    for icon in sorted((pack / "source-pack" / "generations").glob("icon-*.png")):
        approve_fixture(icon)
        decisions["icons"].append({"file": icon.name, "visual_qa": "passed"})
    (pack / "source-pack" / "visual-qa.json").write_text(json.dumps(decisions))
    qualification = qualify.qualify(pack, "anchor_narrative", str(jpg))
    eligible = sorted((pack / "final-pack").glob("icon-*.png"))
    if not eligible: raise SystemExit("all synthetic pack candidates rejected")
    selected = eligible[0]
    packed = execute([sys.executable, str(skill_dir / "scripts" / "apply-icon.py"), str(selected), str(pack_target)])
    symlink_target = runtime / "symlink-target"
    symlink_target.symlink_to(direct_target, target_is_directory=True)
    symlink = execute([sys.executable, str(skill_dir / "scripts" / "apply-icon.py"), str(transparent_png), str(symlink_target)])
    protected = execute([sys.executable, str(skill_dir / "scripts" / "apply-icon.py"), str(transparent_png), "/System"])
    unreadable = execute([sys.executable, str(skill_dir / "scripts" / "apply-icon.py"), str(skill_dir / "tests" / "skill-test-text.txt"), str(direct_target)])
    safety_checks = {
        "失败候选隔离": {"passed": all(not (pack / "final-pack" / i["file"]).exists() for i in qualification["icons"] if i["final_qualification"] == "rejected"), "output": json.dumps(qualification)},
        "软链接目标": {"passed": symlink.returncode != 0 and "target_path_contains_symbolic_link" in symlink.stdout, "output": symlink.stdout.strip()},
        "受保护路径": {"passed": protected.returncode != 0 and "target_not_allowed" in protected.stdout, "output": protected.stdout.strip()},
        "不可解码图片": {"passed": unreadable.returncode != 0 and "requires_verified_transparent_png" in unreadable.stdout, "output": unreadable.stdout.strip()},
    }

    report: dict[str, object] = {
        "routes": {
            "透明 PNG 直接使用": {
                "input": str(transparent_png), "target": str(direct_target), "icon": str(transparent_png),
                "status": "passed" if direct.returncode == 0 else "failed", "icon_readback": "verified" if "icon_status=verified" in direct.stdout else "not_verified",
                "fixture_contents_unchanged": snapshot(direct_target) == direct_before,
                "output": direct.stdout.strip() or direct.stderr.strip(),
            },
            "JPG 素材包应用": {
                "input": str(jpg), "target": str(pack_target), "icon": str(selected),
                "status": "passed" if packed.returncode == 0 else "failed", "icon_readback": "verified" if "icon_status=verified" in packed.stdout else "not_verified",
                "fixture_contents_unchanged": snapshot(pack_target) == pack_before,
                "output": packed.stdout.strip() or packed.stderr.strip(),
                "pack": str(pack), "qa": qa_results,
            },
        },
        "safety_checks": safety_checks,
    }
    write_markdown(output / "mvp-report.md", report)
    (output / "mvp-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    routes_passed = all(route["status"] == "passed" and route["fixture_contents_unchanged"] for route in report["routes"].values())
    return 0 if routes_passed and all(check["passed"] for check in safety_checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
