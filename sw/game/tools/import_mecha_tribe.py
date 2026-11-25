#!/usr/bin/env python3
"""Rebuild the TOCCATA chart from the bundled StepMania 5 SSC and Ogg."""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re

CHART_ID = "mecha-tribe-assault"
CHARTS = Path(__file__).resolve().parents[1] / "toccata_game" / "data" / "charts"
ASSETS = CHARTS / CHART_ID
KEYS = (60, 62, 64, 65)  # left, down, up, right
SSC_SHA256 = "a594bd13b0728ecb2e9eb8e56ddb0e1744c0d2eef80466a42ea299703615e426"
OGG_SHA256 = "6eb052cf8081ebb01d4b30e8db34e9eeca692635e2c1ed3ba7f7bd131c1b65c3"
AUDIO_LENGTH_MS = 105_000  # The pinned Ogg contains 4,630,500 samples at 44,100 Hz.


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
    ssc = original("Mecha-Tribe Assault.ssc", SSC_SHA256).decode("utf-8")
    original("original.ogg", OGG_SHA256)
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
        "audio": f"{CHART_ID}/original.ogg", "audio_length_ms": AUDIO_LENGTH_MS,
        "notes": convert_notes(chart["NOTES"], beat_ms), "phrases": phrases,
    }
    output = CHARTS / f"{CHART_ID}.chart.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
