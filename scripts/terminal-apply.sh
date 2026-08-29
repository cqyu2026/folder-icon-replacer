#!/bin/sh
set -eu

usage() {
  echo "usage: terminal-apply.sh /absolute/path/to/final.png /absolute/path/to/folder" >&2
  exit 2
}

[ "$#" -eq 2 ] || usage

image_path=$1
folder_path=$2
case "$image_path" in /*) ;; *) echo "error=image_path_must_be_absolute" >&2; exit 2 ;; esac
case "$folder_path" in /*) ;; *) echo "error=folder_path_must_be_absolute" >&2; exit 2 ;; esac

[ -f "$image_path" ] || { echo "error=image_not_found" >&2; exit 2; }
[ -d "$folder_path" ] || { echo "error=folder_not_found_or_not_directory" >&2; exit 2; }

skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
setter_path=${FOLDER_ICON_REPLACER_SETTER:-"$skill_dir/.build/folder-icon-setter"}

if [ ! -x "$setter_path" ]; then
  mkdir -p "$skill_dir/.build"
  /bin/sh "$skill_dir/scripts/build-native-tools.sh" "$skill_dir/.build" >&2
fi

if [ ! -x "$setter_path" ]; then
  echo "error=folder_icon_setter_unavailable" >&2
  exit 1
fi

echo "execution_context=Terminal.app"
echo "target=$folder_path"
echo "image=$image_path"
echo "scope=folder_icon_metadata_only"
exec "$setter_path" set-and-verify "$image_path" "$folder_path"
