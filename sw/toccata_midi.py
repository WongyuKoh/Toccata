#!/usr/bin/env python3
"""Toccata USB-MIDI diagnostics, a single FluidSynth engine, and offline tests."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import islice
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = Path(__file__).with_name("midi.example.json")
VIRTUAL_INPUTS = ("system", "midi through", "midithrough", "pipewire", "toccata synth")


class MidiError(Exception):
    """An actionable configuration or setup error."""


class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum


@dataclass(frozen=True)
class Config:
    fluidsynth: str = "fluidsynth"
    soundfont: str = "/usr/share/sounds/sf2/TimGM6mb.sf2"
    audio_device: str = "hw:CARD=Device,DEV=0"
    sample_rate: int = 48000
    gain: float = 0.2
    polyphony: int = 256
    period_size: int = 128
    periods: int = 3


def load_config(path=None, root=REPO_ROOT):
    root = Path(root).resolve()
    candidate = Path(path).expanduser() if path else root / "config/midi.json"
    if path is None and not candidate.exists():
        candidate = EXAMPLE_CONFIG
    try:
        values = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MidiError(f"MIDI 설정을 읽을 수 없습니다: {candidate}: {exc}") from exc
    if not isinstance(values, dict):
        raise MidiError("MIDI 설정은 JSON 객체여야 합니다.")
    unknown = set(values) - set(Config.__dataclass_fields__)
    if unknown:
        raise MidiError("알 수 없는 MIDI 설정: " + ", ".join(sorted(unknown)))
    config = Config(**values)
    for key in ("fluidsynth", "soundfont", "audio_device"):
        value = getattr(config, key)
        if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
            raise MidiError(f"{key}: 비어 있지 않은 문자열이어야 합니다.")
    if not re.fullmatch(r"hw:CARD=[A-Za-z0-9_]+,DEV=[0-9]+", config.audio_device):
        raise MidiError("audio_device는 hw:CARD=Device,DEV=0 형태의 고정 ALSA 카드 ID를 사용하세요.")
    for key, low, high in (
        ("sample_rate", 8000, 96000), ("polyphony", 1, 4096),
        ("period_size", 64, 8192), ("periods", 2, 16),
    ):
        value = getattr(config, key)
        if type(value) is not int or not low <= value <= high:
            raise MidiError(f"{key}: {low}~{high} 사이 정수여야 합니다.")
    if config.period_size & (config.period_size - 1):
        raise MidiError("period_size는 64~8192 사이 2의 거듭제곱이어야 합니다.")
    if (type(config.gain) not in (int, float) or not math.isfinite(config.gain)
            or not 0 < config.gain <= 1):
        raise MidiError("gain은 0보다 크고 1 이하인 유한한 수여야 합니다.")
    sf = Path(config.soundfont).expanduser()
    if not sf.is_absolute():
        sf = root / sf
    return Config(**{**config.__dict__, "soundfont": str(sf.resolve())})


def require_file(path, label):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise MidiError(f"{label} 파일이 없습니다: {path}")
    if not os.access(path, os.R_OK):
        raise MidiError(f"{label} 파일을 읽을 수 없습니다: {path}")
    return path


def fluidsynth_binary(config):
    binary = shutil.which(config.fluidsynth)
    if not binary:
        raise MidiError("FluidSynth 실행 파일이 없습니다. sudo apt install fluidsynth 를 실행하세요.")
    return binary


def alsa_playback_devices():
    binary = shutil.which("aplay")
    if not binary:
        raise MidiError("aplay가 없습니다. sudo apt install alsa-utils 를 실행하세요.")
    result = subprocess.run(
        [binary, "-l"], capture_output=True, text=True, timeout=5,
        env={**os.environ, "LC_ALL": "C"}, check=False,
    )
    return {
        f"hw:CARD={card},DEV={device}"
        for card, device in re.findall(
            r"^card \d+: (\S+) \[.*?\], device (\d+):", result.stdout, re.MULTILINE
        )
    }


def synth_argv(config):
    """One MIDI merger: ALSA FluidSynth autoconnect. No shell or TCP server."""
    return [
        fluidsynth_binary(config), "-i", "-a", "alsa", "-m", "alsa_seq",
        "-r", str(config.sample_rate), "-g", str(config.gain),
        "-o", f"audio.alsa.device={config.audio_device}",
        "-o", f"audio.period-size={config.period_size}",
        "-o", f"audio.periods={config.periods}",
        "-o", f"synth.polyphony={config.polyphony}",
        "-o", "midi.autoconnect=1", "-o", "midi.alsa_seq.id=Toccata synth",
        str(require_file(config.soundfont, "SoundFont")),
    ]


def render_argv(config, midi_path, output):
    sf = require_file(config.soundfont, "SoundFont")
    midi = require_file(midi_path, "MIDI")
    output = Path(output).expanduser().resolve()
    if output in (midi, sf):
        raise MidiError("WAV 출력 경로는 MIDI/SoundFont 입력 파일과 달라야 합니다.")
    if not output.parent.is_dir():
        raise MidiError(f"WAV 출력 폴더가 없습니다: {output.parent}")
    return [
        fluidsynth_binary(config), "-ni", "-F", str(output), "-T", "wav",
        "-r", str(config.sample_rate), "-g", str(config.gain), str(sf), str(midi),
    ]


def load_mido():
    try:
        import mido
    except ImportError as exc:
        raise MidiError(
            "Mido가 없습니다. 프로젝트 .venv에서 pip install -r sw/requirements-midi.txt 를 실행하세요."
        ) from exc
    return mido


def midi_backend():
    mido = load_mido()
    name = "mido.backends.rtmidi/LINUX_ALSA" if sys.platform.startswith("linux") else "mido.backends.rtmidi"
    try:
        backend = mido.Backend(name, load=True)
    except ImportError as exc:
        raise MidiError(
            "python-rtmidi가 없습니다. 프로젝트 .venv에서 pip install -r sw/requirements-midi.txt 를 실행하세요."
        ) from exc
    return backend


def selected_input_names(names, selectors=()):
    if selectors:
        return [name for name in names if any(s.casefold() in name.casefold() for s in selectors)]
    return [name for name in names if not any(v in name.casefold() for v in VIRTUAL_INPUTS)]


def monitor(backend, selectors=(), duration=None, *, clock=time.monotonic, sleep=time.sleep, emit=print):
    """Observe input ports only; never opens an output or forwards a message."""
    opened = {}
    start = clock()
    next_scan = start
    waiting = False
    try:
        while duration is None or clock() - start < duration:
            now = clock()
            if now >= next_scan:
                names = selected_input_names(backend.get_input_names(), selectors)
                next_scan = now + 1.0
                for name in list(opened):
                    if name not in names or opened[name].closed:
                        opened.pop(name).close()
                        emit(f"분리: {name}", flush=True)
                for name in names:
                    if name not in opened:
                        try:
                            opened[name] = backend.open_input(name)
                            emit(f"연결: {name}", flush=True)
                        except (OSError, RuntimeError) as exc:
                            emit(f"입력 연결 대기: {name}: {exc}", flush=True)
                if not opened and not waiting:
                    emit("USB-MIDI 입력을 기다립니다. 장치를 연결하면 자동으로 다시 찾습니다.", flush=True)
                waiting = not opened
            for name, port in list(opened.items()):
                try:
                    for message in islice(port.iter_pending(), 256):
                        emit(f"{clock() - start:9.3f}s [{name}] {message}", flush=True)
                except (OSError, RuntimeError) as exc:
                    opened.pop(name).close()
                    emit(f"분리: {name}: {exc}", flush=True)
            remaining = 0.02 if duration is None else min(0.02, max(0, duration - (clock() - start)))
            if remaining:
                sleep(remaining)
    finally:
        for port in opened.values():
            port.close()


def write_demo(output, mido=None):
    """Create a 2.5-second SMF with note releases and sustain, without device I/O."""
    mido = mido or load_mido()
    output = Path(output).expanduser().resolve()
    if not output.parent.is_dir():
        raise MidiError(f"MIDI 출력 폴더가 없습니다: {output.parent}")
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(mido.Message("program_change", program=0, time=0))
    track.append(mido.Message("control_change", control=64, value=0, time=0))
    for note in (60, 64, 67):
        track.append(mido.Message("note_on", note=note, velocity=72, time=0))
        track.append(mido.Message("note_off", note=note, velocity=32, time=480))
    track.append(mido.Message("control_change", control=64, value=127, time=0))
    for note in (60, 64, 67):
        track.append(mido.Message("note_on", note=note, velocity=64, time=0))
    for index, note in enumerate((60, 64, 67)):
        track.append(mido.Message("note_off", note=note, velocity=32, time=480 if index == 0 else 0))
    track.append(mido.Message("control_change", control=64, value=0, time=480))
    track.append(mido.MetaMessage("end_of_track", time=0))
    midi.save(str(output))
    return output


def positive_duration(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("duration은 0보다 큰 유한한 초 단위 값이어야 합니다.")
    return number


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="MIDI JSON 설정 (기본: config/midi.json 또는 sw/midi.example.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="MIDI 입출력 포트 이름 조회")
    watcher = commands.add_parser("monitor", help="MIDI 입력 관찰; 장치 재연결 자동 감지, 출력 없음")
    watcher.add_argument("--input", action="append", default=[], help="입력 이름 부분 문자열; 여러 번 지정 가능")
    watcher.add_argument("--duration", type=positive_duration, help="관찰 시간(초), 생략하면 계속 실행")
    synth = commands.add_parser("synth", help="ALSA 직결 FluidSynth 한 개 실행")
    synth.add_argument("--dry-run", action="store_true", help="실행 인수만 확인; 오디오/MIDI 장치를 열지 않음")
    render = commands.add_parser("render", help="MIDI 파일을 오프라인 WAV로 변환 (장치 출력 없음)")
    render.add_argument("midi", help="입력 .mid 파일")
    render.add_argument("--output", required=True, help="출력 .wav 파일")
    demo = commands.add_parser("demo", help="음표·서스테인 테스트 MIDI 파일 생성 (장치 출력 없음)")
    demo.add_argument("--output", required=True, help="출력 .mid 파일")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    previous = signal.getsignal(signal.SIGTERM)
    def stop(signum, _frame):
        raise Interrupted(signum)
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.command == "demo":
            print(f"MIDI 생성: {write_demo(args.output)}")
        elif args.command in ("list", "monitor"):
            backend = midi_backend()
            if args.command == "list":
                for label, names in (("입력", backend.get_input_names()), ("출력", backend.get_output_names())):
                    print(f"{label}:")
                    for name in names:
                        print(f"  {name}")
                    if not names:
                        print("  (없음)")
            else:
                if any(not name.strip() for name in args.input):
                    raise MidiError("--input은 비어 있지 않은 이름 부분 문자열이어야 합니다.")
                monitor(backend, args.input, args.duration)
        else:
            config = load_config(args.config)
            if args.command == "synth":
                command = synth_argv(config)
                if args.dry_run:
                    print("장치 검사·실행 생략: " + shlex.join(command))
                    return 0
                available = alsa_playback_devices()
                if config.audio_device not in available:
                    choices = ", ".join(sorted(available)) or "없음"
                    raise MidiError(
                        f"설정한 USB 오디오 장치를 찾을 수 없습니다: {config.audio_device}. "
                        f"USB 오디오를 연결하고 config/midi.json을 수정하세요. 사용 가능: {choices}"
                    )
            else:
                command = render_argv(config, args.midi, args.output)
            print("실행: " + shlex.join(command), flush=True)
            # Replacing this process leaves no orphan synth on Ctrl+C/systemd stop.
            os.execv(command[0], command)
        return 0
    except KeyboardInterrupt:
        return 130
    except Interrupted:
        # A systemd stop is a normal shutdown; monitor() has closed its inputs.
        return 0
    except (MidiError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
