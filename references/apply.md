# macOS 替换与终端兜底

用户已给出 01–09 编号与文件夹绝对路径后，使用对应已检查 PNG 的实际位置：

```sh
/bin/sh /absolute/skill/scripts/terminal-apply.sh /absolute/output/icons/03.png /absolute/target-folder
```

agent 与用户终端使用同一入口。Python 3 检查 PNG，Apple Command Line Tools 的 clang 编译原生 NSWorkspace 写入器并读回。构建输出在 Skill 内 .build/；源码或安装位置变化会重建。发行包不带二进制。

仅支持普通本地文件夹，拒绝 App/package、符号链接路径、挂载点和受保护系统路径，不遍历内容。写入验证 PNG 哈希与目标身份。

成功状态为 icon_status=verified 或 already_selected。permission_denied 可在用户 Terminal 重试同一命令。uncertain 表示写入可能已发生但读回未确认，请用户检查 Finder，不自动重试或回滚。

## 可复制命令

agent 无法执行时提供真实路径的命令，不保留占位符。可用：

```sh
python3 /absolute/skill/scripts/icons.py command /absolute/output/icons/03.png /absolute/target-folder
```

返回安全引用的终端命令，支持中文、空格、单引号。无法运行命令生成器时，逐个路径用 shell 单引号包围，内部单引号转义为 `'"'"'`。必须调用随包脚本，不假设未知工具存在。

缺少 Python 3 或 Command Line Tools 时报告缺项，用户同意配置后再运行；不隐式安装。PNG 检查失败先修复，终端不会绕过。提供命令不等于已替换；以用户执行后的真实结果为准。

恢复默认图标：Finder 选中文件夹，Command-I，选中简介顶部小图标后按 Delete。
