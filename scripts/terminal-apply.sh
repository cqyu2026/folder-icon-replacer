#!/bin/sh
set -eu
[ "$(uname -s)" = Darwin ] || { echo '仅支持 macOS 本机。' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo '缺少 Python 3，请配置后再运行。' >&2; exit 1; }
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$script_dir/icons.py" apply "$@"
