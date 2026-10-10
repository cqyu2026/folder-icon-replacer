# 检查与交付

所有文件放在用户指定输出目录：

```text
output/
  preview.png          # 已确认且编号 01–09
  design.md            # 九个主题与共同风格
  icons/01.png … 09.png
  checks/              # 检查报告与预览
```

检查每张 PNG 并生成尺寸预览：

```sh
python3 /absolute/skill/scripts/icons.py check /absolute/output/icons/01.png --previews /absolute/output/checks/01
```

依赖 Python 3 与 macOS 自带 sips。验证 PNG 字节、CRC、8-bit RGBA、非交错、尺寸上限、真实 alpha、四边透明及孤立单像素。旧覆盖率、矩形背景规则和审查 sidecar 不再使用。

实际查看 1024、128、64 px 在浅色、深色、棋盘背景下的九张预览，检查：
- 主体完整，与已确认总览的对应编号一致。
- 无源图背景、文字、水印、编号、白边或明显色边。
- 无多余杂点；手绘细节缩小后不变成脏点。
- 小尺寸轮廓与区别性细节可辨。

修复失败图后重检，不自动把浅色像素当背景，以免损坏白色主体和颗粒。九张规格和视觉大小应协调。全部通过后交付文件与编号总览，再询问是否替换。
