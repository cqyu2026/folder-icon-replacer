# 三端安装与能力条件

核对日期：2026-09-08。安装支持与真实宿主端到端验证分开记录；本次未在 DeepSeek Harness / WorkBuddy 客户端内完成安装与写入验收。

安装单位是完整 `mac-folder-icon-replacer/` 文件夹。根部必须直接包含 `SKILL.md`，以及 `scripts/`、`macos/`、`references/`、`compatibility/`、`tests/`；`agents/openai.yaml` 是可选 Codex UI 元数据，其他宿主不需要解析它。不要只下载 SKILL.md，不依赖作者项目或作者绝对路径。不分发 `.build/`、`.cross-platform-audit/`、历史运行输出、`__pycache__` 或开发工作区适配器 `.codebuddy/`。编译工具须在安装位置重建。

| 宿主 | 安装/发现方式 | 更新后确认 |
|---|---|---|
| Codex | 项目 `.agents/skills/mac-folder-icon-replacer/SKILL.md`；用户 `$HOME/.agents/skills/mac-folder-icon-replacer/SKILL.md`。本机既有 `~/.codex/skills` 属于原有安装，勿为了本任务改它。 | 官方说明自动检测；不出现时重启 Codex。新任务确认读取的是新版根 SKILL.md。 |
| DeepSeek Harness | 项目根 `.dsh/skills/mac-folder-icon-replacer/SKILL.md`；全局 `<dshHome>/skills/mac-folder-icon-replacer/SKILL.md`，实际 dshHome 以配置为准。也支持项目 `.agents/skills` 和配置的自定义根。 | 当前官方实现有 watcher 与逐步目录更新，不能声称一律只在启动读取。安装/替换后建议新会话并显式调用，确认加载最新正文及资源。 |
| WorkBuddy | **技能 → 添加技能 → 上传技能**，按当前界面选择本地技能包，导入后确认“已安装”中启用。若当前界面提供技能目录配置，使用其显示的实际目录。 | 官方说明导入后自动配置、启用状态立即生效。为排除任务中旧正文，更新后新建任务并明确调用本 Skill。 |

DeepSeek 的项目根是向上最近的 `.git` 目录；无 `.git` 时是会话 cwd，不能把任意子包当项目根。Skill 是指令包，不使用 `dsh plugin add` 安装。本地目录包不会递归搜索任意深度的 `SKILL.md`。

WorkBuddy 官方资料确认上传技能包，但未说明一个可跨版本保证的磁盘根或精确压缩包层级。遵循当前文件选择器接受的格式，并检查导入后资源完整。**不提供猜测的 `~/.workbuddy/...`、`.codebuddy/...` 安装命令或假定存在的 CLI。** 原有 `.codebuddy` 开发入口仅供老工作区定位主文件，不是可独立安装的 Skill。

## 能力预检与安全降级

1. 先确认命令执行、文件读取和 Python 3；无 Python 时不要尝试下面的脚本，也不要偷偷安装依赖。此时无法自动验证或写入，应要求透明 PNG 并转到有验证能力的环境。
2. 有 Python 时运行 `python3 scripts/install-self-test.py --stage preflight`，再运行 `python3 tests/test_portable_icon_gate.py`。`portable-only` 表示只具备 PNG 安全验证路线；`native-ready` 仅证明写入器可编译。
3. JPEG 要求 Mac、Apple Command Line Tools、Vision（macOS 14+）、CoreImage/ImageIO 可实际运行；`prepare-icon.py` 会构建并执行现有提取器和规范化器。构建/模型/处理任一失败即停止，提供透明 PNG 建议。无需 rembg、Pillow、NumPy 或下载模型依赖。
4. 预览必须由能看图的宿主或实际审查者检查。不能因为安装了 Skill 就假定有视觉模型。PNG 有 alpha 并不能代替残留与边缘审查。
5. 只有 Mac 本地且质量门、普通文件夹边界和 NSWorkspace 权限满足时才能完成图标写入。Windows/Linux 上的 DeepSeek 或 WorkBuddy 可以检查 PNG，不承诺设置远端 Mac 图标。

## 核对来源

- [OpenAI：Build skills](https://learn.chatgpt.com/docs/build-skills)：文件夹结构、项目/用户根、自动检测与重启建议。
- [DeepSeek 官方 Skills 子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)：local discovery priority、目录包、项目根、watcher、session catalog。
- [WorkBuddy 官方技能指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)：上传本地技能包、自动配置、启用/关闭。
