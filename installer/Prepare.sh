#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys, ctypes, zlib; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
    printf '%s\n' 'Install Python 3.9 or newer, then run this script again.' >&2
    exit 1
fi
exec python3 "$base/prepare.py" "$@"
