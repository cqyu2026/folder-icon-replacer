# mac-folder-icon-replacer

为一个已经由用户确认的 macOS 普通文件夹设置自定义图标。它支持两条路线：使用已验证的透明 PNG，或在具备 Apple Vision 与 ImageIO 的 Mac 上，从 JPEG 中提取主体后再审查。

这个 Skill 的目标是安全地写入 **一个** 文件夹的图标元数据。它不会读取、枚举、修改或校验目标文件夹中的普通文件和子文件夹；不会批量改图标；不会处理 App、其他 package、符号链接、挂载点、非本地卷和受保护路径。

## 安装

下载或克隆完整目录，不要只复制 `SKILL.md`。安装目录根部应包含：

```text
mac-folder-icon-replacer/
├── SKILL.md
├── scripts/
├── macos/
├── references/
├── compatibility/
└── tests/
```

各宿主的发现方式见[安装与能力条件](compatibility/platform-install.md)：

- **Codex**：按项目或用户级 Skill 目录安装，更新后新开任务确认读取新版根目录。
- **DeepSeek Harness**：放入项目 `.dsh/skills/mac-folder-icon-replacer/` 或配置的全局 Skills 根；更新后建议新建会话并显式调用。
- **WorkBuddy**：通过“技能 → 添加技能 → 上传技能”导入完整包，并在“已安装”中启用；更新后新建任务，避免旧会话继续使用旧指令。

不要分发或提交 `.build/`、运行审计、缓存、`__pycache__`、旧宿主适配目录或用户图片。

## 先做安装验证

在已安装目录中运行。便携回归只需要 Python 3 和标准库，不会碰真实用户文件夹：

```sh
python3 tests/test_portable_icon_gate.py
python3 tests/test_pack_route.py
python3 tests/test_pack_qualification.py
python3 tests/test_route_pack_fixtures.py
python3 tests/test_mvp_builder_guard.py
python3 scripts/install-self-test.py --stage preflight
```

在具备 macOS、Apple Command Line Tools 且允许修改临时夹具图标的环境中，再运行：

```sh
python3 tests/test_native_gate.py
python3 scripts/install-self-test.py --stage e2e --authorize-e2e
```

`native-ready` 只表示原生写入器能够编译；只有 `verified` 才表示临时夹具的图标写入、读回和内容未变检查都通过。

## 使用透明 PNG 设置图标

准备条件：用户已确认一张本地图片和一个绝对路径的普通文件夹。PNG 必须是 8-bit RGBA、非交错、边长不超过 2048 px，并且确实含有透明区域。

先处理到目标文件夹外的新目录：

```sh
python3 scripts/prepare-icon.py /绝对路径/输入.png /绝对路径/新建暂存目录
```

随后检查生成的预览：在浅色、深色和棋盘背景下分别看 1024、128、64 px 尺寸。确认主体内部没有背景残留、边缘没有杂色、主体完整、缩小后仍清晰，才按[质量门规则](references/quality-gate.md)为当前 PNG 写入 SHA-256 绑定的 `.review.json`。

最后重新运行门禁并写入：

```sh
python3 scripts/portable-icon-gate.py /绝对路径/已审查.png --require-review
python3 scripts/apply-icon.py /绝对路径/已审查.png /绝对路径/普通文件夹
```

成功必须出现 `icon_status=verified` 或 `already_selected`。如果宿主后台进程没有桌面目录权限，只能对**同一张已审查 PNG** 使用 `scripts/terminal-apply.sh` 在登录用户的 Terminal.app 中重试；不能绕过质量门，也不能改用原始 JPEG。

## 使用 JPEG

JPEG 只能在具备 macOS 本地 Vision/ImageIO 能力的环境处理：

```sh
python3 scripts/prepare-icon.py /绝对路径/输入.jpg /绝对路径/新建暂存目录
```

提取成功只会得到候选和预览，**不代表合格，也不会自动写入**。如果本机没有可用的原生提取能力，Skill 会拒绝 JPEG，并要求提供已经验证的透明 PNG 或转到支持该能力的 Mac；它不会安装 Pillow、rembg、模型或其他第三方依赖来替代原生流程。

## 质量门与人工审查

门禁会检查 PNG CRC、透明边界、可见像素覆盖率、连通区域中的近似矩形残留、孤立像素和审查记录哈希。技术通过不足以交付或写入。

覆盖率范围仅用于识别不透明背景和残留：**它不是视觉设计规范**，不要求也不偏好圆形图标。除非用户明确要求并且当前图像工具确实能生成、预览结果，否则不得擅自增加圆形裁切、蒙版、边框、圆角或其他构图处理。

用户选中了文件名、目标文件夹或要求“继续”也不等于审查通过。代理只能在实际看过当前候选预览后填写审查记录；不能代替用户自动勾选 `background_removed`、`edges_clean`、`subject_intact` 或 `previews_reviewed`。

## 壁纸配套图标包

只有用户明确要求时才使用[素材包流程](references/material-pack.md)。每个候选都要独立通过同一套 PNG 门禁和视觉审查；`qualify-pack.py` 只会把合格 PNG 和审查记录晋级到 `final-pack/`。

`scripts/build-mvp-pack.py` 仅用于包内固定夹具的回归测试。它要求 `--fixture-only`，并会拒绝任何包外用户图片，绝不能用于生成用户交付物。没有已可用且适合任务的图像生成或编辑能力时，应报告限制，不能自行安装依赖或临时编写裁切、蒙版和渲染流程。

## 常见问题

**为什么透明 PNG 仍然不能写入？** 透明通道不等于背景干净。请看主体内部、孔洞和边缘的预览；缺少审查记录、记录过期或图片在审查后被修改，都会被拒绝。

**为什么 JPEG 被拒绝？** 当前宿主没有能实际执行 Vision/ImageIO 的 macOS 能力，或提取结果未通过质量门。请提供已审查透明 PNG，不要降低检查阈值。

**如何恢复默认文件夹图标？** 在 Finder 选中文件夹，按 Command-I，选中简介窗口顶部的小图标后按 Delete。

## 兼容性与边界

详细状态见[兼容矩阵](compatibility/compatibility-matrix.md)。Windows/Linux 上的宿主可以运行 PNG 的便携验证，但不能设置远端 Mac 的 Finder 图标。实际写入必须由同一台 Mac 的本地 `NSWorkspace` 权限完成。

本项目采用 Python 标准库和现有 Apple 原生框架；不需要第三方 Python 包。
