#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v pi-project >/dev/null 2>&1; then
    echo "라즈베리파이의 pi-project 관리 도구가 필요합니다. 먼저 ./sw/setup-midi.sh로 환경을 설치하세요." >&2
    exit 1
fi
exec pi-project start -- "$(basename -- "$project_dir")"
