Before each application below, complete `quality-gate.md` and keep the matching PNG review sidecar. No manual or permission test may bypass a failed gate.

# macOS 手动边界验证清单

以下步骤只使用新建的临时空文件夹或可卸载卷，不使用真实工作目录。每项记录命令输出、退出码和是否发生写入。

## 权限拒绝

1. 新建临时空文件夹 `mkdir /tmp/icon-permission-target`。
2. 用 Finder“显示简介”取消当前用户写入权限，或在专用测试用户下运行。
3. 执行 `python3 scripts/apply-icon.py /absolute/icon.png /absolute/icon-permission-target`。
4. 预期：退出码 13，报告 `permission_denied`，不重试。

## 挂载点

1. 创建并挂载一个专用、可卸载的磁盘映像。
2. 直接把挂载目录作为目标执行替换。
3. 预期：报告 `target_is_mount_point`，不写入。
4. 验证完成后卸载并删除该测试映像。

## 非本地卷

1. 连接专用测试网络卷或其他非本地文件系统。
2. 在卷内创建空目标文件夹并执行替换。
3. 预期：报告 `target_is_not_local_volume`，不写入。

## 读回不确定与写后身份变化

需要测试构建提供受控 NSWorkspace stub，或在专用测试分支中注入模拟返回：

- 读回返回空图标：预期退出码 14、`icon_status=uncertain`、不重试。
- 写入后替换目标目录的 device/inode：预期退出码 14、`target_identity_changed_after_write`、不重试。

## 视觉整包 QA

将壁纸、全部图标和 64 px 预览并排查看，逐项记录媒介、调色板、轮廓、纹理、光影和抽象程度。任一项失败必须写入 `source-pack/visual-qa.json`，运行 `qualify-pack.py`，确认失败候选只存在于 `source-pack/rejected/`。
