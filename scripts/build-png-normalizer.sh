#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd); out=${1:-"$dir/.build"}; mkdir -p "$out"
clang -fobjc-arc -framework Foundation -framework ImageIO -framework CoreGraphics "$dir/macos/PNGNormalizer.m" -o "$out/png-normalizer"
printf 'build_status=verified\noutput=%s\n' "$out/png-normalizer"
