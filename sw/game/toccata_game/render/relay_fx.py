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
    reach: int  # Half-width in pixels at the 1024-wide logical resolution.
    lift: int
    grains: int  # per side
    alpha: int


_STRIKES = {
    PERFECT: _Strike(255, 94, 128, 5, 255),
    GREAT: _Strike(225, 79, 103, 4, 237),
    GOOD: _Strike(195, 61, 76, 3, 211),
}
_MISS_MS = 120
_PINCH_MS = 48
_CLOSE_MS = 245
_SIGNAL_MS = 335
_CAPACITY = 48

# Each fragment leaves at a different angle. Steep and shallow paths come first
# so even a GOOD has a readable silhouette with its smaller particle budget.
_GRAINS = ((.32, 1.04, 6), (1.03, .34, 6), (.72, .78, 5), (.91, .58, 4), (.13, .95, 4))
# Points run from the contact point out into the positive half of the lane.
_SWEEP = ((.04, .01), (.39, .15), (.95, .27), (1.02, .24), (.64, .07), (.33, .015))
_WAVE = ((-1, 0), (-.48, .27), (-.23, .55), (-.49, .91), (-.29, 1),
         (0, .61), (0, .40), (-.39, .08))
_PETAL = ((.08, .035), (.37, .38), (.75, .59), (.64, .35), (.35, .13))
_SPLINTER = ((.13, .12), (.22, .50), (.44, .86), (.39, .52), (.27, .29))
_GLINT = ((.20, .12), (.43, .31), (.66, .49), (.51, .30))
_CORE = ((-1, .03), (-.34, .20), (-.55, .48), (-.13, .33), (.06, 1),
         (.16, .43), (.57, .63), (.38, .29), (1, .08), (.31, 0), (-.41, 0))


@dataclass(frozen=True)
class _Cue:
    at: float
    x: int
    grade: str
    closing: bool
    broadcast: bool
    velocity: int
    lean: int


_CUE_TIME = attrgetter("at")


class RelayFX:
    def __init__(self, layout: KeyLayout, *, top: int, pixel: bool, beat_ms: float) -> None:
        self.layout = layout
        self.beat_ms = beat_ms
        self._cues: list[_Cue] = []
        self._inks = {
            PERFECT: D.CYAN if pixel else (55, 223, 197),
            GREAT: (156, 199, 255) if pixel else (254, 200, 111),
            GOOD: D.STEEL if pixel else (255, 145, 132),
            MISS: D.HOT if pixel else D.PINK,
        }
        self._accent = D.HOT if pixel else (255, 146, 112)
        self._white = (255, 255, 250)
        # Drawing into a reusable strip leaves the landing rule clear and obeys
        # the destination clip. One unit is one pixel at the stage's design size.
        key_scale = layout.white_w / (1024 / 7)
        bottom = round(layout.land_y) - max(1, round(4 * key_scale))
        self._scale = max(0., min(key_scale, (bottom - top) / 148))
        height = math.ceil(148 * self._scale)
        self._top = bottom - height
        self._strip = pygame.Surface((layout.width, height), pygame.SRCALPHA)
        self._floor = height - 1

    def judged(self, judgment: Judgment, combo: int, velocity: int = 80) -> None:
        """Queue a score decision; a missing MIDI velocity uses a normal attack."""
        center = self.layout.x(judgment.key)
        if center is None:
            return
        success = judgment.grade != MISS
        cue = _Cue(judgment.at, round(center), judgment.grade,
                   success and judgment.part == HOLD, success and combo > 0 and combo % 10 == 0,
                   min(127, max(0, velocity)) if success else 0, 1 if judgment.note % 2 else -1)
        # Judge.update can flush multiple pitches out of timestamp order. Keep the
        # newest decisions even when old expirations arrive after a recent strike.
        index = bisect_right(self._cues, cue.at, key=_CUE_TIME)
        if index and self._cues[index - 1] == cue:
            return  # A missed hold head and its automatic tail share one dim mark.
        self._cues.insert(index, cue)
        if len(self._cues) > _CAPACITY:
            del self._cues[0]

    def reset(self) -> None:
        self._cues.clear()

    def draw(self, surface: pygame.Surface, now: float, judge: Judge) -> None:
        """Blit onto the logical playfield after its background and before its notes."""
        del self._cues[:bisect_right(self._cues, now - _SIGNAL_MS, key=_CUE_TIME)]
        if self._scale <= 0:
            return
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
                    self._close(cue, strike, age)
                    painted = True
            elif age < strike.ms:
                self._burst(cue, strike, age / strike.ms)
                painted = True
            if cue.broadcast:
                self._signal(cue.x, age / _SIGNAL_MS)
                painted = True
        if painted:
            surface.blit(self._strip, (0, self._top))
            self._strip.fill((0, 0, 0, 0))

    def _facet(self, ink, x, y, width, height, points):
        """Draw a filled facet in local coordinates; positive height points up."""
        pygame.draw.polygon(self._strip, ink, [(round(x + u * width), round(y - v * height))
                                               for u, v in points])

    def _burst(self, cue: _Cue, strike: _Strike, phase: float, *, release=False) -> None:
        size = self._scale * (.83 + .17 * cue.velocity / 127)
        reach = strike.reach * size
        lift = strike.lift * size
        if release:
            reach *= 1.09
            lift *= .77
        color = self._inks[cue.grade]
        # The arrival frame already has a silhouette. Open it quickly, then pull
        # the bright material back into the key as the loose grains keep flying.
        opening = 1 - (1 - min(1., phase / .34)) ** 2
        body = max(0., 1 - max(0., phase - .17) / .40)
        span = reach * (.76 + .24 * opening)
        height = lift * (.72 + .28 * opening) * (.40 + .60 * body)
        # A low, detached wave carries the hit sideways after the core collapses.
        wave = max(0., 1 - phase / .82)
        if wave > 0:
            for side in (-1, 1):
                edge = cue.x + side * reach * (1.17 - .52 * wave ** 2)
                self._facet((*color, round(strike.alpha * wave)), edge, self._floor - size * (2 + 4 * opening),
                            side * reach * (.16 + .24 * wave), size * (8 + 5 * wave), _WAVE)
        if body > 0:
            alpha = round(strike.alpha * body)
            for side in (-1, 1):
                width = side * span
                h = height * (1.06 if side == cue.lean else .88)
                self._facet((*color, alpha), cue.x, self._floor, width, h, _SWEEP)
                self._facet((*self._accent, round(alpha * .84)), cue.x, self._floor, width, h, _SPLINTER)
                self._facet((*color, alpha), cue.x, self._floor, width, h, _PETAL)
                self._facet((*self._white, round(alpha * .86)), cue.x, self._floor, width, h, _GLINT)
            self._facet((*self._white, alpha), cue.x, self._floor, cue.lean * span * .65,
                        height * .54, _CORE)
        self._grains(cue, strike, phase, reach, lift)

    def _grains(self, cue, strike, phase, reach, lift):
        scale = self._scale
        travel = .64 + .54 * (1 - (1 - phase) ** 3)
        fall = .42 * phase ** 2
        fade = (1 - phase) ** .93
        lag = max(0., phase - .10)
        prev = .64 + .54 * (1 - (1 - lag) ** 3)
        for side in (-1, 1):
            for i in range(strike.grains):
                u, v, diameter = _GRAINS[i]
                sideways = side * reach * u
                upward = lift * v * (.96 if side == cue.lean else .84)
                dx, dy = sideways * travel, upward * travel - lift * fall
                x, y = round(cue.x + dx), round(self._floor - dy)
                color = self._accent if i == 1 else self._inks[cue.grade]
                # The trail turns over as the fragment starts to fall.
                px = round(cue.x + sideways * prev)
                py = round(self._floor - upward * prev + lift * .42 * lag ** 2)
                radius = max(1, round(diameter * scale * (.55 + .45 * fade)))
                pygame.draw.line(self._strip, (*color, round(113 * fade)), (px, py), (x, y),
                                 max(1, radius // 2))
                self._strip.fill((*color, round(strike.alpha * fade)),
                                 (x - radius // 2, y - radius // 2, radius, radius))
                if i < 2:
                    chip = max(1, radius // 2)
                    self._strip.fill((*self._white, round(strike.alpha * fade)),
                                     (x - chip // 2, y - chip // 2, chip, chip))

    def _hold_pulse(self, key: int, age: float) -> None:
        beat = age / self.beat_ms
        pulse = (1 + math.cos(math.tau * beat)) / 2
        color = self._accent if self.layout.is_black(key) else self._inks[PERFECT]
        x = self.layout.x(key)
        s = self._scale
        # Outside the 18 px rail and above the 29 px guide head, two tapered
        # ribbons breathe on the beat. Brighter flecks climb through each ribbon.
        for side in (-1, 1):
            width = side * s * (25 + 7 * pulse)
            floor = self._floor - 22 * s
            self._facet((*color, round(112 + 53 * pulse)), x, floor, width, s * (50 + 9 * pulse),
                        ((.42, 0), (.95, .34), (1.05, .72), (.78, 1), (.87, .57), (.69, .30)))
            for i in range(2):
                step = (beat + i * .5 + side * .08) % 1
                dx = side * s * (17 + 12 * math.sin(math.pi * step))
                y = self._floor - s * (31 + 59 * step)
                self._facet((*self._white, round(207 * (1 - step))), x + dx, y, side * 4 * s, 8 * s,
                            ((-.5, 0), (-1, .4), (.4, 1), (.5, .4)))

    def _close(self, cue: _Cue, strike: _Strike, age: float) -> None:
        if age >= _PINCH_MS:
            self._burst(cue, strike, (age - _PINCH_MS) / (_CLOSE_MS - _PINCH_MS), release=True)
            return
        pinch = (1 - age / _PINCH_MS) ** 1.5
        s = self._scale
        color = self._inks[cue.grade]
        for side in (-1, 1):
            x = cue.x + side * (4 + strike.reach * .65 * pinch) * s
            y = self._floor - s * (9 + 10 * pinch)
            self._facet((*color, strike.alpha), x, y, side * 20 * s, s * (28 + 17 * pinch),
                        ((0, .5), (.88, 1), (1, .91), (.53, .5), (1, .11), (.86, 0)))
        self._facet((*self._white, strike.alpha), cue.x, self._floor, s * (9 + 11 * (1 - pinch)),
                    s * (36 - 22 * pinch), ((-1, .27), (0, 1), (1, .27), (0, 0)))

    def _miss(self, x: int, phase: float) -> None:
        s = self._scale
        y = self._floor - (6 - 4 * phase) * s
        ink = (*self._inks[MISS], round(98 * (1 - phase)))
        for dx in (-7, 3):
            self._strip.fill(ink, (round(x + dx * s), round(y), max(1, round(5 * s)), max(1, round(2 * s))))

    def _signal(self, x: int, phase: float) -> None:
        s = self._scale
        y = self._floor - s * (107 + 18 * phase)
        alpha = round(244 * (1 - phase ** 2))
        # A floating transmitter with two wide, flat-ended radio waves is only
        # emitted on the tenth decision. It sits above the strike, clear of its core.
        star = ((0, 1), (.26, .25), (1, 0), (.26, -.25), (0, -1), (-.26, -.25), (-1, 0), (-.26, .25))
        self._facet((*self._accent, alpha), x, y, 12 * s, 14 * s, star)
        self._facet((*self._white, alpha), x, y, 5 * s, 7 * s, star)
        for wave in (0, 1):
            radius = (17 + 26 * phase + wave * 12) * s
            for side in (-1, 1):
                self._facet((*self._accent, alpha), x + side * radius, y, side * 9 * s, (9 + wave * 4) * s,
                            ((0, 1), (.40, 1), (1, .42), (1, -.42), (.40, -1), (0, -1),
                             (.57, -.30), (.57, .30)))
