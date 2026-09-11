#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
output_dir=${1:-"$skill_dir/.build"}
mkdir -p "$output_dir"
clang -fobjc-arc -framework Foundation -framework AppKit "$skill_dir/macos/FolderIconSetter.m" -o "$output_dir/folder-icon-setter"
printf 'build_status=verified\noutput_dir=%s\n' "$output_dir"
