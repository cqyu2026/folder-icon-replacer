# WorkBuddy Compatibility Test

## Status

图片处理已验证；WorkBuddy 后台进程的真实文件夹图标写入仍需单独验证。

## Environment Check (2026-08-26)

- WorkBuddy 已安装：`/Applications/WorkBuddy.app`
- 检测到版本：`5.3.11`
- Bundle ID：`com.workbuddy.workbuddy`
- 未发现 `workbuddy` 或 `wb` 命令行入口。
- 初次仅在应用包内查找 Skill 入口，未发现结果；这不是有效的兼容性否定依据。
- 应用检查时未运行。
- 官方文档显示 WorkBuddy/CodeBuddy 支持 `SKILL.md`，工作区 Skill 路径为 `.codebuddy/skills/<skill-name>/SKILL.md`，并支持在设置页通过“导入 Skill”导入网络获取的 Skill。
- 结论：已确认存在可复核的加载方案，但尚未在本机 WorkBuddy 中实际导入和运行，因此仍未验证端到端兼容性。
- 既有实测显示 WorkBuddy 临时安装 `rembg` 时受 NumPy/PyPI 网络与 SSL 问题阻断；1.1.0 已取消主流程中的隐式依赖安装。
- 1.1.0 适配入口使用 `${CODEBUDDY_SKILL_DIR}/../../../SKILL.md`，已在项目布局中完成路径解析检查。

## Root Cause of Earlier Blocker

此前只检查了 `/Applications/WorkBuddy.app` 的应用包和本地命令行入口，忽略了 WorkBuddy 的工作区目录和设置页导入机制。应用包中没有 Skill 文件并不能推出 WorkBuddy 不支持 Skill。

## Officially Supported Loading Paths to Test

1. 通过 WorkBuddy 设置页的“导入 Skill”导入该 Skill 文件夹或压缩包。
2. 在测试工作区内放置 `.codebuddy/skills/mac-folder-icon-replacer/SKILL.md`，从该工作区启动任务。

加载后先运行：

`python3 scripts/install-self-test.py --stage preflight --host workbuddy --host-version 5.3.11`

展示 JSON 报告并获得用户明确授权后，才运行带 `--authorize-e2e` 的隔离端到端测试。

重点检查报告中的 `checks.icon_write`：

- `verified` 表示当前 WorkBuddy 进程对临时夹具具备 `NSWorkspace.setIcon` 写入能力。
- `blocked` 或 `nsworkspace_rejected_icon_update` 表示图片能力可用，但后台进程不能自动写真实文件夹图标；应切换到登录 GUI Terminal 或 Finder 手动粘贴。
- 不能因为 Apple Vision 和透明 PNG 验证通过，就把 WorkBuddy 标记为完整自动化可用。

## Required Evidence

完成统一验收项后，补充：

- WorkBuddy 版本或运行环境
- macOS 版本
- Skill 加载方式
- 图像处理能力及输出文件路径
- Finder、剪贴板和辅助功能权限结果
- 目标文件夹图标更新证据
- 普通文件和嵌套目录变更前后对比
- 失败项、人工介入点和最终兼容性结论
