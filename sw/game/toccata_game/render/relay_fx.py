"""Song-clock landing effects for the rooftop stage, painted before the falling notes."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from operator import attrgetter

import pygame

from ..core.judge import GOOD, GREAT, HOLD, MISS, PERFECT, Judge, Judgment
from . import relay_theme as D
from .geometry import KeyLayout


@dataclass(frozen=True)
class _Strike:
    ms: int
    reach: int
    lift: int
    dots: int  # per hammer
    alpha: int


_STRIKES = {
    PERFECT: _Strike(320, 74, 54, 3, 250),
    GREAT: _Strike(250, 56, 38, 2, 222),
    GOOD: _Strike(185, 39, 24, 1, 186),
}
_MISS_MS = 120
_CLOSE_MS = 215
_SIGNAL_MS = 360
_CAPACITY = 48


@dataclass(frozen=True)
class _Cue:
    at: float
    x: int
    grade: str
    closing: bool
    broadcast: bool


_CUE_TIME = attrgetter("at")


class RelayFX:
    def __init__(self, layout: KeyLayout, *, top: int, pixel: bool, beat_ms: float) -> None:
        self.layout = layout
        self.beat_ms = beat_ms
        self._cues: list[_Cue] = []
        self._inks = {
            PERFECT: D.CYAN if pixel else D.MINT,
            GREAT: D.WHITE if pixel else D.CREAM,
            GOOD: D.STEEL if pixel else D.ORANGE,
            MISS: D.HOT if pixel else D.PINK,
        }
        self._accent = D.HOT if pixel else D.ORANGE
        # Leave the landing rule clear. A single reusable alpha strip also respects
        # the destination's existing clip without changing it for subsequent notes.
        bottom = round(layout.land_y) - 4
        self._top = max(top, bottom - 88)
        self._strip = pygame.Surface((layout.width, bottom - self._top), pygame.SRCALPHA)
        self._floor = self._strip.get_height() - 1
        self._reach = max(1, round(layout.white_w * 0.5))

    def judged(self, judgment: Judgment, combo: int) -> None:
        """Call once per decision with ScoreKeeper.combo immediately after add()."""
        center = self.layout.x(judgment.key)
        if center is None:
            return
        success = judgment.grade != MISS
        cue = _Cue(judgment.at, round(center), judgment.grade,
                   success and judgment.part == HOLD, success and combo > 0 and combo % 10 == 0)
        # Judge.update can flush multiple pitches out of timestamp order. Keep the
        # newest decisions even when old expirations arrive after a recent strike.
        index = bisect_right(self._cues, cue.at, key=_CUE_TIME)
        if index and self._cues[index - 1] == cue:
            return  # A missed hold head and its automatic tail share one dim mark.
        self._cues.insert(index, cue)
        if len(self._cues) > _CAPACITY:
            del self._cues[0]

    def reset(self) -> None:
        """Clear a reused view on retry. A newly constructed view is already clear."""
        self._cues.clear()

    def draw(self, surface: pygame.Surface, now: float, judge: Judge) -> None:
        """Blit onto the logical playfield after its background and before its notes."""
        del self._cues[:bisect_right(self._cues, now - _SIGNAL_MS, key=_CUE_TIME)]
        painted = False
        for key in range(self.layout.base, self.layout.base + 12):
            hold = judge.active_hold(key)
            if hold and hold.holding:
                age = now - judge.heads[hold.note].at
                if age >= 0:
                    self._hold_pulse(key, age)
                    painted = True
        for cue in self._cues:
            age = now - cue.at
            if age < 0:
                break
            if cue.grade == MISS:
                if age < _MISS_MS:
                    self._miss(cue.x, age / _MISS_MS)
                    painted = True
                continue
            strike = _STRIKES[cue.grade]
            if cue.closing:
                if age < _CLOSE_MS:
                    self._close(cue, strike, age / _CLOSE_MS)
                    painted = True
            elif age < strike.ms:
                self._hammer(cue, strike, age / strike.ms)
                painted = True
            if cue.broadcast:
                self._signal(cue.x, age / _SIGNAL_MS)
                painted = True
        if painted:
            surface.blit(self._strip, (0, self._top))
            self._strip.fill((0, 0, 0, 0))

    def _hammer(self, cue: _Cue, strike: _Strike, phase: float) -> None:
        spread = 1 - (1 - phase) ** 2
        span = round(6 + (min(self._reach, strike.reach) - 6) * spread)
        lift = round(9 + (strike.lift - 9) * spread)
        color = self._inks[cue.grade]
        iron = (*color, round(strike.alpha * max(0, 1 - phase / 0.78)))
        afterglow = (*color, round(strike.alpha * (1 - phase)))
        # A flat ellipse reads as contact with the keyboard, even during a hold
        # whose wide labelled head covers the origin of the burst.
        ring_w = 2 * span + 18
        pygame.draw.ellipse(self._strip, afterglow, (cue.x-ring_w//2, self._floor-13, ring_w, 11), 2)
        for side in (-1, 1):
            tip = cue.x + side * span
            y = self._floor - lift
            if iron[3]:
                root = cue.x + side * round(span * .40)
                pygame.draw.polygon(self._strip, iron, [(root, self._floor-5), (tip, y-5),
                                                        (tip+side*2, y+3), (root+side*6, self._floor-5)])
            for dot in range(strike.dots):
                dx = round((0.42 + 0.20 * dot) * span)
                dy = lift + 3 + round((4 + dot * 6) * spread)
                size = 5 if dot == 0 else 3
                self._strip.fill(afterglow, (cue.x + side * dx - 1, self._floor - dy, size, size))

    def _hold_pulse(self, key: int, age: float) -> None:
        pulse = (1 + math.cos(math.tau * age / self.beat_ms)) / 2
        color = self._accent if self.layout.is_black(key) else self._inks[PERFECT]
        ink = (*color, round(135 + 100 * pulse))
        x = round(self.layout.x(key))
        # The guide head is up to 29 px tall and the hold rail is 18 px wide.
        y = max(4, self._floor - 29 - round(4 * pulse))
        gap = 16 + round(8 * pulse)
        for side in (-1, 1):
            inner = x + side * gap
            pygame.draw.lines(self._strip, ink, False,
                              [(inner, y), (inner + side * 11, y), (inner + side * 18, y - 7)], 3)
            for index in range(2):
                step = (age / self.beat_ms + index * .5) % 1
                self._strip.fill((*color, round(160 * (1-step))),
                                 (x + side*(11+round(12*step)), y-5-round(24*step), 3, 4))

    def _close(self, cue: _Cue, strike: _Strike, phase: float) -> None:
        ink = (*self._inks[cue.grade], round(strike.alpha * (1 - phase ** 2)))
        y = self._floor - 9
        gap = round(min(self._reach, strike.reach) * (1 - min(1, phase / 0.68)) ** 2)
        for side in (-1, 1):
            inner = cue.x + side * gap
            outer = inner + side * 5
            pygame.draw.lines(self._strip, ink, False, [(outer, y - 4), (inner, y), (outer, y + 4)], 2)
        if gap <= 2:
            pygame.draw.polygon(self._strip, ink, [(cue.x, y - 3), (cue.x + 3, y),
                                                  (cue.x, y + 3), (cue.x - 3, y)])

    def _miss(self, x: int, phase: float) -> None:
        y = self._floor - 6 + round(4 * phase)
        ink = (*self._inks[MISS], round(98 * (1 - phase)))
        for dx in (-7, 3):
            self._strip.fill(ink, (x + dx, y, 5, 2))

    def _signal(self, x: int, phase: float) -> None:
        # A small transmitting aerial above the two hammers. The wavefronts
        # travel in pairs, away from the centre of the incoming note.
        y = max(5, self._floor - 43)
        ink = (*self._accent, round(232 * (1 - phase ** 2)))
        pygame.draw.lines(self._strip, ink, False, [(x - 4, y + 9), (x, y), (x + 4, y + 9)], 2)
        self._strip.fill(ink, (x - 2, y - 2, 4, 4))
        for wave in (0, 1):
            radius = 15 + round(22 * phase) + wave * 12
            for side in (-1, 1):
                edge = x + side * radius
                pygame.draw.lines(self._strip, ink, False,
                                  [(edge, y - 5), (edge + side * 3, y), (edge, y + 5)], 2)
