#!/usr/bin/env python3
"""Generate the original 164 BPM breakbeat étude 「막차 스퍼트」.

Run with .venv/bin/python sw/game/tools/make_last_train_sprint.py.
Bar zero is the four-click count-in. The right hand owns the entire lead.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import mido

if __package__:
    from .make_rooftop_reply import OUT_DIR, TPB, midi_track
else:
    from make_rooftop_reply import OUT_DIR, TPB, midi_track

CHART_ID = "last-train-sprint"
BPM = 164
KEYS = {"C": 60, "D": 62, "E": 64, "F": 65}
HOOK = "CDE.F.D."

# Each cell is an eighth note. A letter alone is a tap; '-' extends it into a hold.
SCORE = (
    ("Am7", HOOK),       ("Fmaj7", "E..C..D."), ("Dm9", HOOK),       ("G13", "E---..D."),
    ("Am7", "C..E.D.."), ("Fmaj7", "F--.ED.."), ("Dm9", "C..D.E.."), ("G13", "F---.ED."),
    ("Am7", HOOK),       ("C/E", "E.FD.C.."),    ("Fmaj7", "F.ED.CD."), ("G7", "E-..F..."),
    ("C6", HOOK),        ("Am7", "EFD.C.FE"),    ("Fmaj7", HOOK),     ("G13", "E.F.D-.."),
    ("C6", HOOK),        ("Am7", "EFD.C.FE"),    ("Dm9", "CDEFCDEF"), ("Fmaj7", "D.E.C---"),
    ("Fmaj7", "F.ED..C."), ("Dm9", "D-..F.E."),  ("G13", HOOK),      ("C6", "E.D.C---"),
)
PHRASES = ((1, "출발 신호"), (5, "터널 진입"), (9, "계단 질주"), (13, "막차 스퍼트"), (21, "종착 안내"))
CHORUS = range(13, 21)
BREAK_BAR = 12

# Bass root, moving bass tone, and electric-piano shell below the player's C4.
VOICINGS = {
    "Am7":   (33, 40, (48, 52, 55)),
    "Fmaj7": (41, 36, (48, 52, 57)),
    "Dm9":   (38, 45, (48, 52, 53)),
    "G13":   (31, 38, (47, 52, 53)),
    "G7":    (31, 38, (47, 50, 53)),
    "C/E":   (40, 43, (48, 52, 55)),
    "C6":    (36, 43, (52, 55, 57)),
}


def ms(beats: float) -> int:
    return round(beats * 60_000 / BPM)


def chart_data() -> dict:
    notes = []
    for bar, (_, pattern) in enumerate(SCORE, 1):
        if len(pattern) != 8 or not re.fullmatch(r"(?:[CDEF]-*|\.)+", pattern):
            raise ValueError(f"Invalid eighth-note score in bar {bar}: {pattern!r}")
        for match in re.finditer(r"([CDEF])(-*)", pattern):
            letter, tie = match.groups()
            start = ms(bar * 4 + match.start() / 2)
            end = ms(bar * 4 + match.end() / 2) if tie else start
            note = {"t": start, "k": KEYS[letter], "d": end - start, "f": "CDEF".index(letter) + 1}
            if (pattern == HOOK and match.start() == 4) or (bar == 19 and match.start() == 0):
                note["v"] = "f"
            notes.append(note)
    return {
        "format": 1, "id": CHART_ID, "title": "막차 스퍼트", "composer": "TOCCATA (자작)",
        "chapter": "prologue", "step": 2, "tier": "etude", "level": 4,
        "bpm": BPM, "offset_ms": 0, "keys": list(KEYS.values()), "fall_ms": 1500,
        "accomp": f"{CHART_ID}.accomp.mid", "notes": notes,
        "phrases": [{"t": ms(bar * 4), "label": label} for bar, label in PHRASES],
    }


def drum_bar(bar):
    """Relative (beat, GM drum, gate, velocity) events for a two-bar break."""
    kick, snare, hat, open_hat = 36, 38, 42, 46
    if bar == len(SCORE):
        return [(0, kick, .12, 101), (0, hat, .1, 67), (1, snare, .12, 94),
                (2, kick, .12, 106), (2, open_hat, .12, 76)]
    if bar == BREAK_BAR:
        # Unison stab on beat three, followed by a completely empty fourth beat.
        return [(0, kick, .12, 102), (.5, hat, .1, 64), (1, snare, .12, 89),
                (1.5, snare, .1, 55), (1.75, snare, .1, 72),
                (2, snare, .12, 105), (2, kick, .12, 100), (2, open_hat, .1, 72)]

    chorus = bar in CHORUS
    tunnel = 5 <= bar <= 8
    kicks = (0, 2.5) if bar % 2 else (0, 1.75, 2.5)
    drums = [(beat, kick, .12, 106 if beat == 0 else 91) for beat in kicks]
    drums.extend([(1, snare, .12, 101), (3, snare, .12, 109)])
    for slot, velocity in enumerate((68, 47, 59, 49, 64, 46, 59, 53)):
        if tunnel and slot in (2, 6):
            continue
        sound = open_hat if slot == 7 and (chorus or bar % 4 == 0) else hat
        drums.append((slot / 2, sound, .1, velocity + (7 if chorus else 0)))
    if not tunnel:
        drums.append((2.25 if bar % 2 else .75, 40, .1, 49))
    if chorus:
        drums.extend([(.75, hat, .08, 38), (2.75, hat, .08, 45)])
        if bar % 2:
            drums.append((3.5, kick, .12, 78))
    if bar in (4, 8, 11, 16, 20, 23):
        drums.extend([(3.5, 40, .1, 65), (3.75, snare, .1, 80)])
    return drums


def accompaniment() -> mido.MidiFile:
    bass, keys, bells = [], [], []
    drums = [(beat, 76 if beat == 0 else 77, .12, velocity)
             for beat, velocity in enumerate((88, 64, 68, 74))]
    for bar, (chord, _) in enumerate(SCORE, 1):
        start = bar * 4
        root, passing, shell = VOICINGS[chord]
        for beat, pitch, gate, velocity in drum_bar(bar):
            drums.append((start + beat, pitch, gate, velocity))

        if bar == len(SCORE):
            # Two pickups resolve with the player's last C onto a sustained tonic.
            line = [(0, root + 12, .65, 83), (1, passing, .65, 76), (2, root, 2, 96)]
            stabs = [(0, .45, 57), (1, .4, 50), (2, 2, 68)]
            bells.append((start + 2, 79, 1.5, 48))
        elif bar == BREAK_BAR:
            line = [(0, root, 1, 89), (1.5, passing, .28, 77), (2, root, .35, 93)]
            stabs = [(.5, .27, 53), (2, .35, 64)]
        elif 5 <= bar <= 8:
            line = [(0, root, 1.35, 86), (2.5, passing, .75, 75)]
            stabs = [(.5, .5, 52), (2, .65, 49)]
        else:
            # The short offbeat octave answers the kick. Extra sixteenths push the chorus.
            line = [(0, root, .62, 91), (.75, root + 12, .45, 74),
                    (2, root, .35, 82), (2.5, passing, .67, 86)]
            stabs = [(.5, .3, 56), (1.5, .26, 50), (3.5, .25, 53)]
            if bar in CHORUS:
                line.append((3.5, root + 12, .3, 76))
                stabs.append((2.75, .22, 53))
                # High platform-bell replies leave the middle-C register to the hand.
                if bar % 2:
                    bells.extend([(start + 1.5, shell[0] + 24, .3, 44),
                                  (start + 3.5, shell[-1] + 24, .32, 50)])
        bass.extend((start + beat, pitch, gate, vel) for beat, pitch, gate, vel in line)
        for beat, gate, velocity in stabs:
            keys.extend((start + beat, pitch, gate, velocity) for pitch in shell)

    midi = mido.MidiFile(type=1, ticks_per_beat=TPB)
    midi.tracks.extend((
        mido.MidiTrack([mido.MetaMessage("track_name", name=CHART_ID),
                        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM)),
                        mido.MetaMessage("time_signature", numerator=4, denominator=4)]),
        midi_track("Syncopated synth bass", 1, bass, program=38),
        midi_track("Electric piano stabs", 2, keys, program=4),
        midi_track("Platform bells", 3, bells, program=11),
        midi_track("Count and breakbeat kit", 9, drums),
    ))
    return midi


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chart = json.dumps(chart_data(), ensure_ascii=False, indent=2)
    (OUT_DIR / f"{CHART_ID}.chart.json").write_text(chart + "\n", encoding="utf-8")
    accompaniment().save(OUT_DIR / f"{CHART_ID}.accomp.mid")


if __name__ == "__main__":
    main()
