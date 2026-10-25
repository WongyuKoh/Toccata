#!/bin/sh
# Install project-local Python dependencies; system packages remain explicit.
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$(id -u)" -eq 0 ]; then
    echo "일반 사용자 계정에서 실행하세요. venv와 프로젝트 파일을 root로 만들지 않습니다." >&2
    exit 1
fi
if ! command -v fluidsynth >/dev/null 2>&1; then
    echo "FluidSynth가 없습니다. Raspberry Pi에서 다음 명령을 먼저 실행하세요:" >&2
    echo "sudo apt-get install --no-install-recommends fluidsynth alsa-utils timgm6mb-soundfont libasound2-dev python3-venv" >&2
    exit 1
fi
python3 -m venv "$project_dir/.venv"
"$project_dir/.venv/bin/python" -m pip install -r "$project_dir/sw/requirements-midi.txt"
mkdir -p "$project_dir/config" "$project_dir/data" "$project_dir/logs"
if [ ! -e "$project_dir/config/midi.json" ]; then
    cp "$project_dir/sw/midi.example.json" "$project_dir/config/midi.json"
fi
if command -v pi-project >/dev/null 2>&1; then
    "$project_dir/.venv/bin/python" - "$project_dir" <<'PYTHON'
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
manifest = root / 'project.json'
if not manifest.exists():
    manifest.write_text(json.dumps({
        'version': 1, 'command': ['python3', 'sw/toccata_midi.py', 'monitor'],
        'working_directory': '.', 'env_file': None, 'environment': {},
        'autostart': False,
    }, ensure_ascii=False, indent=2) + '\n')
    manifest.chmod(0o600)
PYTHON
fi
printf '%s\n' "MIDI 환경 설치 완료. ./sw/toccata-midi list 로 장치를 확인하세요."
