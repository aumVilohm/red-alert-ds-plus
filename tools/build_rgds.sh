#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != aarch64 ]; then
    printf '%s\n' 'Run this script in an ARM64 Linux build environment.' >&2
    exit 1
fi
cmake -S "$root/upstream/Vanilla-Conquer" -B "$root/build/arm64" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_VANILLATD=OFF -DBUILD_VANILLARA=ON -DRED_ALERT_DS_PLUS=ON \
    -DBUILD_TESTS=ON -DBUILD_TOOLS=ON
cmake --build "$root/build/arm64" --parallel "${BUILD_JOBS:-4}"
ctest --test-dir "$root/build/arm64" --output-on-failure
