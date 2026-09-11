#!/usr/bin/env python3
"""Set a custom icon without accessing the target's internal contents."""
import importlib, os, subprocess, sys
gate = importlib.import_module("portable-icon-gate")
from pathlib import Path

def fail(reason, target):
    print(f"失败\n原因：{reason}\n目标：{target}\n图标：未确认完成\n内部内容：未读取、未写入、未执行完整性验证")
    return 1
def main():
    if len(sys.argv) != 3:
        print("usage: apply-icon.py /absolute/path/to/ready-image /absolute/path/to/folder", file=sys.stderr); return 2
    image, target = Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser()
    if not image.is_absolute() or not target.is_absolute(): return fail("路径必须是绝对路径", target)
    if not image.is_file(): return fail("输入图片不存在或不可读", target)
    qa = gate.assess(image, Path(str(image) + ".review.json"))
    if qa["status"] != "passed": return fail("质量门拒绝：" + "; ".join(qa["errors"]), target)
    if sys.platform != "darwin": return fail("当前主机不能写入 macOS 文件夹图标；请在 Mac 上使用已验证 PNG", target)
    try: info = os.lstat(target)
    except OSError as error: return fail(f"目标不可访问：{error.strerror or error}", target)
    if not os.path.isdir(target): return fail("目标不是普通文件夹", target)
    skill = Path(__file__).resolve().parent.parent; build = skill / ".build"; setter = build / "folder-icon-setter"
    if not setter.is_file() or not os.access(setter, os.X_OK) or setter.stat().st_mtime < (skill / "macos" / "FolderIconSetter.m").stat().st_mtime:
        made = subprocess.run(["/bin/sh", str(skill / "scripts" / "build-icon-setter.sh"), str(build)], text=True, capture_output=True)
        if made.returncode: return fail("原生图标工具构建失败", target)
    result = subprocess.run([str(setter), "set-and-verify", str(image), str(target), str(info.st_dev), str(info.st_ino), qa["sha256"]], text=True, capture_output=True)
    if result.returncode == 0:
        print(f"成功\n目标：{target}\n{result.stdout.strip()}\n内部内容：未读取、未写入、未执行完整性验证\n恢复默认图标：Finder 显示简介中选中顶部小图标后按 Delete。")
        return 0
    if result.returncode == 13:
        print(f"失败\n原因：当前进程没有修改图标元数据的权限\n目标：{target}\n下一步：请在 Finder 中选中目标，按 Command + I，选中顶部小图标后粘贴准备好的图片。")
        return 13
    if result.returncode == 14:
        print(f"不确定\n原因：{result.stderr.strip() or '图标写入后无法确认'}\n目标：{target}\n图标：未确认完成\n内部内容：未读取、未写入、未执行完整性验证")
        return 14
    return fail(result.stderr.strip() or "原生图标工具执行失败", target)
if __name__ == "__main__": raise SystemExit(main())
