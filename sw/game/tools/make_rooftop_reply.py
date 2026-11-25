#!/usr/bin/env python3
"""Generate 「첫 번째 답장」, an original follow-up to 「첫 닿음」.

Run with the project's Python: .venv/bin/python sw/game/tools/make_rooftop_reply.py
Bar 0 is the count-in. All positions and durations in the score are quarter notes.
"""
from __future__ import annotations

import json
from pathlib import Path

import mido

OUT_DIR = Path(__file__).resolve().parents[1] / "toccata_game" / "data" / "charts"
CHART_ID = "rooftop-reply"
BPM = 104
BEATS_PER_BAR = 4
TPB = 480
C, D, E = 60, 62, 64
FINGER = {C: 1, D: 2, E: 3}

# One entry per played bar: chord, then (beat from zero, player key, beats held).
# A zero duration is a tap. The reply leaves beat one empty before coming in.
SCORE = (
    ("C6/9",  ((0, C, 0), (1, D, 0), (2, E, 0))),
    ("Am7",   ((1, E, 0), (2, D, 0))),
    ("Fmaj9", ((0, C, 1.5), (2, D, 0), (3, E, 0))),
    ("G6",    ((0, D, 2.5),)),
    ("C/E",   ((1, E, 0), (2, D, 0), (3, C, 0))),
    ("Am7",   ((0, E, 2), (3, D, 0))),
    ("Fmaj9", ((1, C, 1.5), (3, E, 0))),
    ("Em7",   ((1, D, 0), (2, E, 1.5))),
    ("Dm7",   ((0, D, 2), (3, C, 0))),
    ("G9sus", ((0, E, 0), (2, D, 1.5))),
    ("C6/9",  ((0, C, 0), (1, D, 0), (2, E, 0))),
    ("Fmaj9", ((1, E, 0), (2, C, 1.5))),
    ("G6",    ((0, E, 0), (2, D, 1.5))),
    ("C6/9",  ((0, C, 3),)),
)
BRIDGE, REPRISE = 7, 11
PHRASES = ((1, "도레미 호출"), (5, "첫 답장"), (BRIDGE, "옥상의 메아리"), (REPRISE, "끝인사"))

# Downbeat bass, second bass note, and electric-piano voicing, all below middle C.
VOICINGS = {
    "C6/9":  (36, 43, (50, 52, 55, 57)),
    "Am7":   (33, 40, (48, 52, 55)),
    "Fmaj9": (41, 36, (48, 52, 55, 57)),
    "G6":    (31, 38, (47, 50, 52, 55)),
    "C/E":   (40, 43, (48, 52, 55)),
    "Em7":   (40, 35, (47, 50, 55)),
    "Dm7":   (38, 45, (48, 53, 57)),
    "G9sus": (31, 38, (48, 50, 53, 57)),
}

# Lower answering voice in the bridge: (beat, pitch, duration).
ECHO = (
    ((0, 53, 0.65), (2.5, 57, 0.4)),
    ((0, 55, 0.9), (3.5, 52, 0.4)),
    ((1, 53, 0.5), (2, 57, 0.8)),
    ((0.5, 55, 0.55), (1.5, 53, 0.55), (3, 50, 0.85)),
)


def ms(beats: float) -> int:
    return round(beats * 60_000 / BPM)


def chart_notes() -> list[dict]:
    notes = []
    for bar, (_, melody) in enumerate(SCORE, start=1):
        for beat, key, length in melody:
            start = bar * BEATS_PER_BAR + beat
            notes.append({"t": ms(start), "k": key, "d": ms(start + length) - ms(start), "f": FINGER[key]})
    return notes


def chart_data() -> dict:
    return {
        "format": 1, "id": CHART_ID, "title": "첫 번째 답장", "composer": "TOCCATA (자작)",
        "chapter": "prologue", "step": 1, "tier": "prelude", "level": 2,
        "bpm": BPM, "offset_ms": 0, "keys": [C, D, E], "fall_ms": 2000,
        "accomp": f"{CHART_ID}.accomp.mid", "notes": chart_notes(),
        "phrases": [{"t": ms(bar * BEATS_PER_BAR), "label": label} for bar, label in PHRASES],
    }


def midi_track(name, channel, notes, program=None) -> mido.MidiTrack:
    """Write absolute (beat, key, length, velocity) notes as delta-time MIDI."""
    track = mido.MidiTrack([mido.MetaMessage("track_name", name=name)])
    if program is not None:
        track.append(mido.Message("program_change", channel=channel, program=program))
    events = []
    for beat, key, length, velocity in notes:
        events.append((round(beat * TPB), velocity, key))
        events.append((round((beat + length) * TPB), 0, key))
    previous = 0
    for tick, velocity, key in sorted(events):  # Releases first if a pitch repeats on the same tick.
        kind = "note_on" if velocity else "note_off"
        track.append(mido.Message(kind, channel=channel, note=key, velocity=velocity, time=tick - previous))
        previous = tick
    return track


def accompaniment() -> mido.MidiFile:
    bass, piano, vibes = [], [], []
    # GM high wood block, then kick, side stick and closed hat once the trio enters.
    drums = [(beat, 76, 0.12, velocity) for beat, velocity in enumerate((61, 46, 48, 51))]
    for bar, (chord, _) in enumerate(SCORE, start=1):
        start = bar * BEATS_PER_BAR
        root, second, voicing = VOICINGS[chord]
        if bar == len(SCORE):
            bass.append((start, root, 3.5, 64))
            strokes = ((0, 3.75, 47),)
        elif BRIDGE <= bar < REPRISE:
            # Wide sustained chords and one bass attack open up space for the echo.
            bass.append((start, root, 2.75, 59))
            strokes = ((0.5, 3.25, 43),)
            for beat, pitch, length in ECHO[bar - BRIDGE]:
                vibes.append((start + beat, pitch, length, 48))
            if bar == REPRISE - 1:
                drums.extend(((start + 3, 37, 0.12, 39), (start + 3.5, 42, 0.12, 35)))
        else:
            bass.extend(((start, root, 1.5, 67), (start + 2.5, second, 0.85, 55)))
            strokes = ((0.5, 1.15, 49), (2, 0.7, 43), (3.5, 0.4, 39))
            drums.extend(((start, 36, 0.15, 51), (start + 1, 37, 0.12, 45), (start + 3, 37, 0.12, 42)))
            for beat in (0.5, 1.5, 2.5, 3.5):
                drums.append((start + beat, 42, 0.10, 35 if beat == 2.5 else 29))
        for beat, length, velocity in strokes:
            for key in voicing:
                piano.append((start + beat, key, length, velocity))

    midi = mido.MidiFile(type=1, ticks_per_beat=TPB)
    midi.tracks.extend((
        mido.MidiTrack([
            mido.MetaMessage("track_name", name=CHART_ID),
            mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM)),
            mido.MetaMessage("time_signature", numerator=BEATS_PER_BAR, denominator=4),
        ]),
        midi_track("Fingered bass", 1, bass, program=33),
        midi_track("Electric piano", 2, piano, program=4),
        midi_track("Vibraphone reply", 3, vibes, program=11),
        midi_track("Count and kit", 9, drums),
    ))
    return midi


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chart = json.dumps(chart_data(), ensure_ascii=False, indent=2)
    (OUT_DIR / f"{CHART_ID}.chart.json").write_text(chart + "\n", encoding="utf-8")
    accompaniment().save(OUT_DIR / f"{CHART_ID}.accomp.mid")


if __name__ == "__main__":
    main()
