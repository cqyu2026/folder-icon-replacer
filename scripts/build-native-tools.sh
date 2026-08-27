#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SKILL_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUTPUT_DIR=${1:-"$SKILL_DIR/.build"}

mkdir -p "$OUTPUT_DIR"

clang -fobjc-arc -framework Foundation -framework AppKit \
  "$SKILL_DIR/macos/ClipboardBridge.m" \
  -o "$OUTPUT_DIR/clipboard-bridge"

clang -fobjc-arc -framework Foundation -framework ImageIO -framework CoreGraphics \
  "$SKILL_DIR/macos/ImageInspector.m" \
  -o "$OUTPUT_DIR/image-inspector"

clang -fobjc-arc -framework Foundation -framework Vision -framework CoreImage -framework CoreGraphics -framework CoreVideo \
  "$SKILL_DIR/macos/ForegroundExtractor.m" \
  -o "$OUTPUT_DIR/foreground-extractor"

clang -fobjc-arc -framework Foundation -framework AppKit \
  "$SKILL_DIR/macos/FolderIconSetter.m" \
  -o "$OUTPUT_DIR/folder-icon-setter"

APP_DIR="$OUTPUT_DIR/foreground-extractor.app"
mkdir -p "$APP_DIR/Contents/MacOS"
cp "$OUTPUT_DIR/foreground-extractor" "$APP_DIR/Contents/MacOS/foreground-extractor"
cp "$SKILL_DIR/macos/ForegroundExtractor-Info.plist" "$APP_DIR/Contents/Info.plist"

printf 'build_status=verified\n'
printf 'output_dir=%s\n' "$OUTPUT_DIR"
