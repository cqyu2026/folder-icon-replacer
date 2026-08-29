#!/usr/bin/env python3
"""Apply one image as the custom icon of one confirmed macOS folder."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(reason: str, *, target: Path, image: Path | None = None, command: str | None = None, code: int = 1) -> int:
    print("失败")
    print(f"原因：{reason}")
    print(f"文件夹：{target}")
    if image:
        print(f"最终图片：{image}")
    print("图标：未确认完成")
    if command:
        print("下一步：请将下面命令粘贴到已登录的 Terminal.app 中执行")
        print(command)
    return code


def snapshot(root: Path) -> dict[str, dict[str, object]]:
    allowed = {".DS_Store", "Icon\r"}
    result: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if len(relative.parts) == 1 and relative.name in allowed:
            continue
        info = path.lstat()
        entry: dict[str, object] = {
            "kind": stat.filemode(info.st_mode),
            "mode": stat.S_IMODE(info.st_mode),
            "mtime_ns": info.st_mtime_ns,
            "uid": info.st_uid,
            "gid": info.st_gid,
        }
        if path.is_symlink():
            entry["target"] = os.readlink(path)
        elif path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            entry.update({"size": info.st_size, "sha256": digest.hexdigest()})
        result[str(relative)] = entry
    return result


def terminal_command(skill_dir: Path, image: Path, target: Path) -> str:
    wrapper = skill_dir / "scripts" / "terminal-apply.sh"
    return "sh " + " ".join(shlex.quote(str(value)) for value in (wrapper, image, target))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: apply-icon.py /absolute/path/to/image /absolute/path/to/folder", file=sys.stderr)
        return 2

    image = Path(sys.argv[1]).expanduser()
    target = Path(sys.argv[2]).expanduser()
    skill_dir = Path(__file__).resolve().parent.parent
    if not image.is_absolute() or not target.is_absolute():
        return fail("路径必须是绝对路径", target=target)
    if not image.is_file():
        return fail("输入图片不存在或不可读", target=target)
    if not target.is_dir() or target.is_symlink():
        return fail("目标不是可用的普通文件夹", target=target)

    work_dir = Path(tempfile.mkdtemp(prefix="folder-icon-replacer-"))
    final_image = work_dir / "final.png"
    keep_work_dir = True
    try:
        if shutil.which("sips") is None:
            return fail("macOS sips 不可用，无法标准化图片", target=target)
        converted = subprocess.run(
            ["sips", "-s", "format", "png", str(image), "--out", str(final_image)],
            capture_output=True,
            text=True,
        )
        if converted.returncode != 0 or not final_image.is_file():
            return fail("图片无法转换为 PNG", target=target, image=final_image)

        before = snapshot(target)
        build_dir = skill_dir / ".build"
        setter = build_dir / "folder-icon-setter"
        if not setter.is_file() or not os.access(setter, os.X_OK):
            build = subprocess.run(
                ["/bin/sh", str(skill_dir / "scripts" / "build-native-tools.sh"), str(build_dir)],
                capture_output=True,
                text=True,
            )
            if build.returncode != 0:
                return fail("native 图标工具构建失败", target=target, image=final_image)

        result = subprocess.run(
            [str(setter), "set-and-verify", str(final_image), str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 13:
            return fail(
                "当前进程没有修改文件夹图标的权限",
                target=target,
                image=final_image,
                command=terminal_command(skill_dir, final_image, target),
                code=13,
            )
        if result.returncode != 0:
            reason = result.stderr.strip() or "native 图标工具执行失败"
            return fail(reason, target=target, image=final_image)

        after = snapshot(target)
        if before != after:
            return fail("文件夹普通内容发生变化，结果不安全", target=target, image=final_image, code=15)

        print("成功")
        print(f"文件夹：{target}")
        print("图标：已修改并验证")
        print("内容：普通文件和子文件夹未变化")
        print("方式：NSWorkspace.setIcon")
        keep_work_dir = False
        return 0
    except (OSError, subprocess.SubprocessError) as exc:
        return fail(f"执行异常：{exc}", target=target, image=final_image)
    finally:
        if not keep_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
