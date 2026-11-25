"""The rooftop band's MIDI score, instruments and mixer, shared by SDL and WAV.

Load a chart once with load_arrangement(). Pass BandPlayer.due() the unadjusted
song clock, including its negative lead-in. Create a fresh player for a new run.
For render_wav(), melody event times and song_start_ms use the recording clock.
No display, mixer or pygame import is needed to load a score or write a WAV.
"""
from __future__ import annotations

from array import array
from bisect import bisect_left
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from itertools import accumulate, islice, repeat
from math import cos, exp, isfinite, sin, tau
from operator import add, attrgetter, mul
from pathlib import Path
from random import Random
import sys
from threading import Event, Thread
from time import monotonic
import wave

RATE = 22_050
_BLOCK = RATE // 4
_KEY_RELEASE_MS = 155


@dataclass(frozen=True)
class MidiNote:
    start_ms: float
    end_ms: float
    channel: int
    program: int
    note: int
    velocity: int


@dataclass(frozen=True)
class Arrangement:
    notes: tuple[MidiNote, ...]
    length_ms: float


def load_arrangement(chart) -> Arrangement:
    """Read the MIDI next to chart.path. Chart offset shifts keys relative to this track."""
    if not chart.accomp:
        return Arrangement((), 0.0)
    if chart.path is None:
        raise ValueError("반주 파일을 찾으려면 채보 경로가 필요합니다")
    import mido

    midi = mido.MidiFile(Path(chart.path).parent / chart.accomp)
    programs = [0] * 16
    held = defaultdict(deque)
    notes = []
    now = 0.0

    def release(channel, note):
        start, program, velocity = held[channel, note].popleft()
        notes.append(MidiNote(start, now, channel, program, note, velocity))

    # MidiFile iteration merges tracks and converts delta ticks using the tempo map.
    for msg in midi:
        now += msg.time * 1000.0
        if msg.type == "program_change":
            programs[msg.channel] = msg.program
        elif msg.type == "note_on" and msg.velocity:
            held[msg.channel, msg.note].append((now, programs[msg.channel], msg.velocity))
        elif msg.type in ("note_on", "note_off") and held[msg.channel, msg.note]:
            release(msg.channel, msg.note)
    for channel, note in held:
        while held[channel, note]:
            release(channel, note)
    return Arrangement(tuple(sorted(notes, key=lambda n: n.start_ms)), now)


# Each partial specifies frequency ratio, peak amplitude and exponential decay
# per second. Slight detuning models paired piano strings. The faster upper
# modes leave a rounder fundamental as the hammer, tine or pluck dies away.
_PARTIALS = {
    "piano": ((1, .57, 1.05), (1.0017, .24, .86), (2.001, .28, 1.95),
              (3.003, .16, 3.6), (4.009, .09, 4.8), (6.016, .05, 12)),
    "electric": ((1, .75, .83), (1.0011, .18, .98), (2, .20, 1.9),
                 (3, .13, 2.8), (7.01, .075, 8.4)),
    "vibes": ((1, .86, .94), (1.0025, .14, .91), (3.99, .30, 2.7), (9.9, .07, 8.0)),
    "guitar": ((1, .68, 1.65), (2, .36, 2.2), (3, .17, 3.7), (5, -.11, 5.8),
               (6, -.06, 7.0)),
    "bass": ((1, .78, .78), (2, .32, 1.43), (3, .17, 2.1), (4, .10, 3.8),
             (6, .075, 7.8)),
}
# Natural length, attack, damper release (ms) and full-velocity PCM level.
_PATCH = {
    "keys":     (5600, 8, _KEY_RELEASE_MS, 13400),
    "piano":    (4800, 9, 135, 6900),
    "electric": (5100, 11, 190, 5900),
    "vibes":    (5000, 6, 250, 8100),
    "guitar":   (3500, 6, 115, 6800),
    "bass":     (5600, 9, 90, 11500),
}


def _instrument(n):
    if n.channel == 9:
        return "kit"
    if 4 <= n.program < 8:
        return "electric"
    if 8 <= n.program < 16:
        return "vibes"
    if 24 <= n.program < 32:
        return "guitar"
    if 32 <= n.program < 40:
        return "bass"
    return "piano"


def _frames(ms):
    return round(ms * RATE / 1000)


def _speed(value):
    if not isfinite(value) or value <= 0:
        raise ValueError("재생 속도는 양의 유한한 값이어야 합니다")
    return value


def _soft_edges(pcm, attack_ms, tail_ms):
    attack = _frames(attack_ms)
    for i in range(min(len(pcm), attack)):
        pcm[i] = round(pcm[i] * i / attack)
    size = min(len(pcm), _frames(tail_ms))
    for i in range(size):
        pcm[-1 - i] = round(pcm[-1 - i] * i / size)
    return pcm


@lru_cache(maxsize=96)
def _tone(instrument, note):
    natural, attack, _, level = _PATCH[instrument]
    hz = 440 * 2 ** ((note - 69) / 12)
    waves = []
    for ratio, amplitude, decay in _PARTIALS["piano" if instrument == "keys" else instrument]:
        if hz * ratio >= RATE * .48:
            continue
        angle = tau * hz * ratio / RATE
        step = exp(-decay / RATE) * complex(cos(angle), sin(angle))
        # A damped rotating phasor generates one mode without a per-frame sine call.
        values = accumulate(repeat(step), mul, initial=complex(amplitude * level))
        waves.append(map(attrgetter("imag"), values))
    if not waves:
        return array("h", [0])  # All partials exceed the sample rate's Nyquist limit.
    signal = waves.pop()
    for partial in waves:
        signal = map(add, signal, partial)
    pcm = array("h", map(round, islice(signal, _frames(natural))))
    return _soft_edges(pcm, attack, 60)


@lru_cache(maxsize=32)
def _drum(note):
    """One-shot kit. Use a fixed noise seed for identical live and recorded hits."""
    rng = Random(note)
    if note in (35, 36):
        seconds = .34
    elif note in (38, 40):
        seconds = .23
    elif note in (42, 44, 46):
        seconds = .28 if note == 46 else .085
    else:
        seconds = .105
    pcm = array("h")
    previous = 0.0
    for i in range(round(seconds * RATE)):
        t = i / RATE
        noise = rng.uniform(-1, 1)
        high = (noise - previous) * .5
        previous = noise
        if note in (35, 36):
            # The head settles near 54 Hz after its initial downward sweep.
            phase = tau * (54 * t + 2.15 * (1 - exp(-45 * t)))
            sample = 12200 * sin(phase) * exp(-16 * t) + 2300 * high * exp(-110 * t)
        elif note in (38, 40):
            sample = (5200 * sin(tau * 187 * t) * exp(-35 * t)
                      + 7700 * (.7 * noise + .3 * high) * exp(-22 * t))
        elif note in (42, 44, 46):
            metal = .13 * sin(tau * 3821 * t) + .08 * sin(tau * 5387 * t)
            sample = 6700 * (high + metal) * exp((-18 if note == 46 else -55) * t)
        elif note == 37:   # Rim click
            sample = (6900 * sin(tau * 830 * t) * exp(-82 * t)
                      + 4400 * sin(tau * 1613 * t) * exp(-125 * t) + 3200 * high * exp(-220 * t))
        else:              # Woodblock, including the GM high/low pair (76/77)
            hz = 970 if note == 76 else 740
            sample = 8900 * (sin(tau * hz * t) + .38 * sin(tau * hz * 2.64 * t)) * exp(-58 * t)
        pcm.append(round(sample))
    return _soft_edges(pcm, 2, 9)


def _volume(velocity):
    # SDL_mixer uses 128 gain steps. Render the same gain in the WAV mixer.
    return round(128 * (min(127, max(0, velocity)) / 127) ** 1.05)


@lru_cache(maxsize=192)
def _voice(instrument, note, velocity, gate):
    if instrument == "kit":
        source = _drum(note)
        end = len(source)
    else:
        source = _tone(instrument, note)
        end = min(len(source), gate + _frames(_PATCH[instrument][2]))
    gain = _volume(velocity)
    pcm = array("h", (s * gain // 128 for s in memoryview(source)[:end]))
    if instrument != "kit" and gate < end:
        release = _frames(_PATCH[instrument][2])
        for i in range(gate, end):
            pcm[i] = pcm[i] * (release - (i - gate)) // release
    return pcm


@dataclass(frozen=True, order=True)
class _Hit:
    start: int
    instrument: str
    note: int
    velocity: int
    gate: int


def _backing(arrangement, speed, start_ms=0.0):
    speed = _speed(speed)
    start = _frames(start_ms)
    return [_Hit(start + _frames(n.start_ms / speed), _instrument(n), n.note, n.velocity,
                 max(0, _frames((n.end_ms - n.start_ms) / speed)))
            for n in arrangement.notes]


def _keyboard(events, end):
    held = {}
    hits = []

    def release(note, at):
        before = held.pop(note, None)
        if before is not None:
            start, velocity = before
            hits.append(_Hit(start, "keys", note, velocity, max(0, at - start)))

    for ms, kind, note, velocity in sorted(events, key=lambda event: event[0]):
        if kind not in ("on", "off"):
            raise ValueError(f"알 수 없는 건반 이벤트 {kind!r}")
        at = _frames(ms)
        release(note, at)
        if kind == "on" and velocity > 0:
            held[note] = at, velocity
    for note in list(held):
        release(note, end)
    return hits


def _blocks(hits, end):
    """Mix quarter-second native int16 blocks. Only sounding voices enter each sum."""
    hits = sorted(hits)
    starts = [h.start for h in hits]
    cursor = 0
    sounding = []
    for start in range(0, end, _BLOCK):
        stop = min(start + _BLOCK, end)
        upcoming = bisect_left(starts, stop, lo=cursor)
        for h in hits[cursor:upcoming]:
            # Drum note-offs don't damp one-shot samples. Canonicalise their cache key.
            pcm = _voice(h.instrument, h.note, h.velocity, 0 if h.instrument == "kit" else h.gate)
            sounding.append((h.start, memoryview(pcm)))
        cursor = upcoming
        block = [0] * (stop - start)
        remaining = []
        for onset, source in sounding:
            first, last = max(start, onset), min(stop, onset + len(source))
            if first < last:
                a, b = first - start, last - start
                block[a:b] = map(add, block[a:b], source[first - onset:last - onset])
            if onset + len(source) > stop:
                remaining.append((onset, source))
        sounding = remaining
        if min(block) < -32768 or max(block) > 32767:
            block = [min(32767, max(-32768, value)) for value in block]
        yield array("h", block)


def render_wav(path, arrangement, melody_events, *, duration_ms, speed=1.0, song_start_ms=0.0):
    """Write 22,050 Hz mono PCM; an event is (recording_ms, 'on'|'off', key, velocity).

    The recording starts at 0. song_start_ms places MIDI beat zero within it; only
    the MIDI score follows speed. Overhanging notes are trimmed to duration_ms.
    """
    if not isfinite(duration_ms) or duration_ms < 0:
        raise ValueError("녹음 길이는 0 이상의 유한한 값이어야 합니다")
    end = _frames(duration_ms)
    hits = _backing(arrangement, speed, song_start_ms) + _keyboard(melody_events, end)
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, RATE, end, "NONE", "not compressed"))
        for block in _blocks(hits, end):
            if sys.byteorder == "big":
                block.byteswap()
            out.writeframesraw(block.tobytes())


class KeyboardPlayer:
    """Player piano with natural decay, velocity and a short damper release."""

    def __init__(self, pygame):
        self.mixer = pygame.mixer
        self._sounds = {}
        self._down = {}
        self._scheduled = set()

    def prepare(self, notes):
        """Prime the first key immediately and warm remaining PCM during the lead-in."""
        pending = [note for note in dict.fromkeys(notes) if note not in self._scheduled]
        if not pending:
            return
        self._scheduled.update(pending)
        self._sound(pending[0])

        def warm():
            for note in pending[1:]:
                _tone("keys", note)

        if len(pending) > 1:
            Thread(target=warm, daemon=True, name="rooftop-keys").start()

    def _sound(self, note):
        if note not in self._sounds:
            self._sounds[note] = self.mixer.Sound(buffer=_tone("keys", note).tobytes())
        return self._sounds[note]

    def note_on(self, note, velocity):
        self.note_off(note)
        if velocity > 0:
            sound = self._sound(note)
            channel = sound.play()
            if channel is not None:
                channel.set_volume(_volume(velocity) / 128)
                self._down[note] = channel

    def note_off(self, note):
        channel = self._down.pop(note, None)
        if channel is not None and channel.get_sound() is self._sounds[note]:
            channel.fadeout(_KEY_RELEASE_MS)

    def stop(self):
        for sound in self._sounds.values():
            sound.stop()
        self._down.clear()


class BandPlayer:
    """Queue PCM ahead of the device clock. Seeking skips elapsed audio, including attacks.

    Give this class the initialized mono mixer at RATE and tick due(song_ms) each
    frame. pause()/resume() freeze queued sound in place. stop() ends this run.
    """

    def __init__(self, pygame, arrangement, speed=1.0):
        self.mixer = pygame.mixer
        self.speed = _speed(speed)
        self._pcm = []
        self._cancel = Event()
        self._error = None
        self._channel = None
        self._sounds = deque(maxlen=2)
        self._next = 0
        self._last = None
        self._origin = None
        self._paused_at = None
        hits = _backing(arrangement, speed)
        if hits:
            # Keep the final instrument release. Generate outside the frame loop.
            end = _frames(arrangement.length_ms / speed + 350)
            blocks = _blocks(hits, end)
            Thread(target=self._prepare, args=(blocks,), daemon=True, name="rooftop-band").start()

    def _prepare(self, blocks):
        try:
            for block in blocks:
                if self._cancel.is_set():
                    break
                self._pcm.append(block.tobytes())
        except Exception as exc:
            self._error = exc

    def _playing(self):
        return self._channel is not None and self._channel.get_sound() in self._sounds

    def _silence(self):
        if self._playing():
            self._channel.stop()
        self._channel = None
        self._sounds.clear()
        self._origin = None

    def due(self, song_ms):
        if self._error is not None:
            raise RuntimeError("반주 합성 실패") from self._error
        if self._paused_at is not None or self._cancel.is_set():
            return
        now = monotonic()
        frame = _frames(song_ms / self.speed)
        index, offset = divmod(frame, _BLOCK)
        # The audio device runs between frames. After a seek or a stalled
        # simulation clock, start at the matching sample rather than replay a beat.
        drifted = self._origin is not None and abs(now - self._origin - frame / RATE) > .080
        if drifted or (self._last is not None and frame < self._last):
            self._silence()
        self._last = frame
        if frame < 0:
            return
        if not self._playing():
            if index >= len(self._pcm):
                return
            pcm = self._pcm[index][2 * offset:]
            if not pcm:
                return
            sound = self.mixer.Sound(buffer=pcm)
            self._channel = sound.play()
            if self._channel is None:
                return
            self._origin = now - frame / RATE
            self._sounds.append(sound)
            self._next = index + 1
        if self._next < len(self._pcm) and self._channel.get_queue() is None:
            sound = self.mixer.Sound(buffer=self._pcm[self._next])
            self._channel.queue(sound)
            self._sounds.append(sound)
            self._next += 1

    def pause(self):
        if self._paused_at is not None:
            return
        if self._playing():
            self._channel.pause()
        self._paused_at = monotonic()

    def resume(self):
        if self._paused_at is None:
            return
        if self._origin is not None:
            self._origin += monotonic() - self._paused_at
        if self._playing():
            self._channel.unpause()
        self._paused_at = None

    def stop(self):
        self._cancel.set()
        self._silence()
