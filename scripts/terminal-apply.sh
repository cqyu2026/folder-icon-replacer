#!/bin/sh
set -eu
skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v python3 >/dev/null 2>&1 || { echo "需要 Python 3 执行质量门；请在具备验证能力的 Mac 上运行。" >&2; exit 1; }
exec python3 "$skill_dir/scripts/apply-icon.py" "$@"
