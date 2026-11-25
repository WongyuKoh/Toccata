#!/usr/bin/env python3
"""Rebuild the TOCCATA chart from the bundled StepMania 5 SSC and Ogg."""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess

CHART_ID = "mecha-tribe-assault"
CHARTS = Path(__file__).resolve().parents[1] / "toccata_game" / "data" / "charts"
ASSETS = CHARTS / CHART_ID
KEYS = (60, 62, 64, 65)  # left, down, up, right
SSC_SHA256 = "a594bd13b0728ecb2e9eb8e56ddb0e1744c0d2eef80466a42ea299703615e426"
OGG_SHA256 = "6eb052cf8081ebb01d4b30e8db34e9eeca692635e2c1ed3ba7f7bd131c1b65c3"
MIXER_FILE = "mixer.flac"


def original(name: str, digest: str) -> bytes:
    data = (ASSETS / name).read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"원본 SHA-256 불일치: {name}")
    return data


def tags(section: str) -> dict[str, str]:
    return dict(re.findall(r"^#(\w+):([^;]*);", section, flags=re.MULTILINE))


def convert_notes(pattern: str, beat_ms: Fraction) -> list[dict[str, int]]:
    notes = []
    holds = {}
    for bar, measure in enumerate(pattern.split(",")):
        rows = measure.split()
        for index, row in enumerate(rows):
            beat = 4 * bar + Fraction(4 * index, len(rows))
            time_ms = round(beat * beat_ms)
            for finger, (key, symbol) in enumerate(zip(KEYS, row, strict=True), 1):
                if symbol == "0":
                    continue
                if symbol == "3":
                    head = holds.pop(key)
                    head["d"] = time_ms - head["t"]
                    continue
                if symbol not in ("1", "2") or key in holds:
                    raise ValueError(f"{bar + 1}마디의 노트가 잘못됐습니다: {row}")
                note = {"t": time_ms, "k": key, "d": 0, "f": finger}
                notes.append(note)
                if symbol == "2":
                    holds[key] = note
    if holds:
        raise ValueError("끝나지 않은 홀드가 있습니다")
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-audio", action="store_true", help="FFmpeg로 게임 믹서용 FLAC도 갱신")
    args = parser.parse_args()
    ssc = original("Mecha-Tribe Assault.ssc", SSC_SHA256).decode("utf-8")
    original("original.ogg", OGG_SHA256)
    if args.rebuild_audio:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ASSETS / "original.ogg"),
                        "-map_metadata", "-1", "-ac", "1", "-ar", "22050", "-c:a", "flac",
                        "-sample_fmt", "s16", "-compression_level", "8", "-fflags", "+bitexact",
                        str(ASSETS / MIXER_FILE)], check=True)
    # The upstream Ogg granule reports 105 s, shorter than the decoded audio.
    # FLAC's STREAMINFO gives the exact decoded duration even with sound muted.
    with (ASSETS / MIXER_FILE).open("rb") as file:
        header = file.read(42)
    if header[:4] != b"fLaC" or len(header) < 42 or header[4] & 127 != 0:
        raise ValueError("게임용 FLAC에 STREAMINFO 헤더가 없습니다")
    stream_info = int.from_bytes(header[18:26], "big")
    rate = stream_info >> 44
    samples = stream_info & ((1 << 36) - 1)
    if rate != 22050 or samples == 0:
        raise ValueError("게임용 FLAC의 재생 길이 또는 샘플링 주파수가 잘못됐습니다")
    audio_ms = (samples * 1000 + rate - 1) // rate
    header, *sections = ssc.split("#NOTEDATA:;")
    song = tags(header)
    chart, = (
        chart for chart in map(tags, sections)
        if (chart["STEPSTYPE"], chart["DIFFICULTY"], chart["METER"], chart["CREDIT"])
        == ("dance-single", "Medium", "8", "Wyde")
    )
    # This SSC has a single BPM at beat zero and no timing changes for Medium.
    bpm = int(Fraction(song["BPMS"].split("=")[1]))
    beat_ms = Fraction(60_000, bpm)
    phrases = []
    for entry in song["LABELS"].split(","):
        beat, label = entry.split("=")
        phrases.append({"t": round(Fraction(beat.strip()) * beat_ms), "label": label})
    result = {
        "format": 1, "id": CHART_ID, "title": song["TITLE"], "composer": song["ARTIST"],
        "chapter": "free", "step": 5, "tier": "sonata", "level": int(chart["METER"]),
        # StepMania subtracts OFFSET (seconds); TOCCATA adds offset_ms on load.
        "bpm": bpm, "offset_ms": round(-1000 * Fraction(song["OFFSET"])),
        "keys": list(KEYS), "fall_ms": 1500,
        "audio": f"{CHART_ID}/original.ogg", "mixer_audio": f"{CHART_ID}/{MIXER_FILE}", "audio_length_ms": audio_ms,
        "notes": convert_notes(chart["NOTES"], beat_ms), "phrases": phrases,
    }
    output = CHARTS / f"{CHART_ID}.chart.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
