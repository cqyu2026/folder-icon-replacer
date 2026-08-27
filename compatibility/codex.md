# Codex Compatibility Test

## Status

版本 1.1.0：已验证。安装副本完成授权后的隔离 E2E，并生成宿主绑定 JSON 凭据。

## 1.1.0 Preflight Scope

- 固定测试资源 SHA-256 校验通过
- Objective-C 原生工具编译通过
- JPG 解码和不透明状态校验通过
- WorkBuddy/Codex 共用自检脚本可运行
- 未授权调用 E2E 时正确停止为 `authorization-required`
- 当前 Codex 宿主进程无法加载 Apple Vision ANE subject-lifting 模型；已设计为经授权后在登录 GUI 会话重试
- 授权后的非受限安装验证中，Apple Vision 生成透明候选，`NSWorkspace.setIcon` 更新临时夹具副本图标，普通内容保持不变
- 凭据：`~/Library/Application Support/folder-icon-replacer/verification/codex-1.1.0-arm64.json`

## Historical Verified Scope

- JPG 转透明 PNG
- Finder 目标文件夹选择和“显示简介”流程
- 顶部图标粘贴替换
- 图标更新验证
- 普通文件与嵌套目录内容保护
- 允许并单独记录 Finder 系统元数据变化

## Notes

1.1.0 Codex 结果不得扩展解释为 WorkBuddy 或另一台 Mac 已兼容；它们必须各自运行相同验证协议。
