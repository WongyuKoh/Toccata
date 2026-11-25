#!/usr/bin/env python3
"""Rebuild both TOCCATA charts from the bundled StepMania 5 SSC and Ogg."""
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
PIANO_ID = f"{CHART_ID}-piano-hard"
PIANO_KEYS = (60, 63, 67, 70)  # C4, Eb4, G4, Bb4 in SSC lane order
PIANO_FINGERS = (4, 2, 1, 3)
# SSC beats from zero. At each selected onset, sound the note(s) in the row.
# The spaces between these entries leave the original track alone.
PIANO_TOUCH_BEATS = {
    16, 16.5, 18.5, 20.5, 32, 32.5, 34.5, 38.5,  # Verse 1: two calls and replies
    49.5, 50.5, 56, 57.5, 60.5, 64, 64.5, 66.5,  # Verse 2: offbeat fifths
    80, 83.5, 91.5, 96, 97.5, 101.5,  # Verse 3: echo the two-hand hits
    112, 120, 121, 122, 128, 135, 136,  # Verse 4: C/G, swap the held voice
    144, 145.5, 147, 147.5, 150, 152, 153.5, 156,  # Verse 5A: answer bass with treble
    161.5, 162, 163.5, 165, 168, 171.5,  # Verse 5B: sustain the replies
    179, 180, 183, 187, 187.5, 192, 195.5, 199,  # Verse 6: punctuate the fast runs
    208, 212, 214, 217.5, 228, 230, 232, 234, 236,  # Verse 7: Bb to the G pedal
    242, 244, 250, 256, 257, 261,  # Verse 8: return to C/G
    273.5, 275, 276, 283, 293, 294, 298,  # Verse 9: treble Bb recedes to bass C
}
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


def convert_notes(pattern: str, beat_ms: Fraction, *, piano: bool = False) -> list[dict]:
    notes = []
    holds = {}
    keys = PIANO_KEYS if piano else KEYS
    fingers = PIANO_FINGERS if piano else (1, 2, 3, 4)
    for bar, measure in enumerate(pattern.split(",")):
        rows = measure.split()
        for index, row in enumerate(rows):
            beat = 4 * bar + Fraction(4 * index, len(rows))
            time_ms = round(beat * beat_ms)
            for key, symbol, finger in zip(keys, row, fingers, strict=True):
                if symbol == "0" or (piano and symbol == "M"):
                    continue
                if symbol == "3":
                    head = holds.pop(key)
                    head["d"] = time_ms - head["t"]
                    continue
                if symbol not in ("1", "2") or key in holds:
                    raise ValueError(f"{bar + 1}마디의 노트가 잘못됐습니다: {row}")
                note: dict = {"t": time_ms, "k": key, "d": 0, "f": finger}
                if piano:
                    note["h"] = "L" if key < 65 else "R"
                    if beat in PIANO_TOUCH_BEATS:
                        note["touch"] = "p" if note["h"] == "L" else "f"
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
    # Both Wyde charts use the global timing, a single BPM at beat zero.
    bpm = int(Fraction(song["BPMS"].split("=")[1]))
    beat_ms = Fraction(60_000, bpm)
    phrases = []
    for entry in song["LABELS"].split(","):
        beat, label = entry.split("=")
        phrases.append({"t": round(Fraction(beat.strip()) * beat_ms), "label": label})
    charts = [tags(section) for section in sections]
    for chart_id, difficulty, meter in ((CHART_ID, "Medium", "8"), (PIANO_ID, "Hard", "10")):
        chart, = (
            c for c in charts if (c["STEPSTYPE"], c["DIFFICULTY"], c["METER"], c["CREDIT"])
            == ("dance-single", difficulty, meter, "Wyde")
        )
        piano = chart_id == PIANO_ID
        result = {
            "format": 1, "id": chart_id, "title": song["TITLE"] + (" (Piano Hard)" if piano else ""),
            "composer": song["ARTIST"], "chapter": "free", "step": 6 if piano else 5,
            "tier": "sonata", "level": int(meter),
            # StepMania subtracts OFFSET (seconds); TOCCATA adds offset_ms on load.
            "bpm": bpm, "offset_ms": round(-1000 * Fraction(song["OFFSET"])),
            "keys": list(PIANO_KEYS if piano else KEYS), "fall_ms": 1500,
            "audio": f"{CHART_ID}/original.ogg", "mixer_audio": f"{CHART_ID}/{MIXER_FILE}",
            "audio_length_ms": audio_ms,
            "notes": convert_notes(chart["NOTES"], beat_ms, piano=piano), "phrases": phrases,
        }
        output = CHARTS / f"{chart_id}.chart.json"
        data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if not output.exists() or output.read_bytes() != data:
            output.write_bytes(data)


if __name__ == "__main__":
    main()
