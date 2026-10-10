# Folder Icon Replacer · macOS

输入图片 → 编号 01–09 的九宫格预览 → 用户确认 → 九张独立透明 PNG → 询问是否替换文件夹图标。

有元素时制作手绘记忆图标；无元素时制作同色系文件夹。参考图优先，元素和文件夹风格提示词作为兜底，不绑定生图模型。生图能力来自当前 agent 环境。

```text
folder-icon-replacer/
├── SKILL.md
├── references/
├── assets/
└── scripts/
```

仓库根目录是 Skill 源码。README、LICENSE、VERSION 和 tests 是开发与分发资料；发行包顶层为 folder-icon-replacer，包含完整 Skill 和许可证。复制完整包安装，读取 SKILL.md 开始。

仅 macOS 本机。检查需要 Python 3；替换还需 Apple Command Line Tools 与文件夹权限。agent 无法执行时提供随包脚本的终端命令。

开发验证：`python3 -m unittest discover -s tests -v`。测试输出在 .build/tests/，原生测试只修改该目录内的夹具图标。
