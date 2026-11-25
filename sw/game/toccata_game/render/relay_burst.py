"""The gold impact and two firework trails behind the rooftop encore notes."""

from __future__ import annotations

import math

import pygame


# Match the stage's two-pixel grid. Leave the last rows above the keys clear.
_WIDTH, _FIELD_HEIGHT, _HEIGHT = 305, 193, 171
_CX, _CY = 152, 82
_GOLD = (255, 191, 56)
_HONEY = (255, 222, 111)
_HOT = (255, 246, 198)
_AMBER = (239, 120, 39)

# Uneven lengths leave dark gaps between the ribbons. The longest pair sets
# a diagonal from the lower left through the impact to the upper right.
_RAYS = tuple(
    (math.cos(math.radians(angle)), math.sin(math.radians(angle)), length, width)
    for angle, length, width in (
        (-168, 81, 6), (-148, 107, 9), (-126, 76, 6), (-106, 95, 8),
        (-83, 68, 5), (-65, 89, 8), (-48, 75, 5), (-29, 128, 10),
        (-9, 83, 7), (12, 101, 6), (35, 83, 7), (61, 81, 8),
        (88, 71, 5), (116, 87, 7), (151, 118, 9), (171, 75, 5),
    )
)

# Each arc fattens in the middle and tapers at both ends.
_ARCS = tuple(
    tuple((math.cos(math.radians(start + span * i / 16)),
           math.sin(math.radians(start + span * i / 16)),
           math.sin(math.pi * i / 16)) for i in range(17))
    for start, span in ((-176, 91), (-78, 68), (-3, 92), (97, 77))
)

# Horizontal travel, initial lift, and individual launch delay for each
# fragment. Mirroring this fan sends the two showers toward opposite wings.
_FRAGMENTS = (
    (-40, 65, .03), (-27, 45, .07), (-15, 83, .00), (-3, 61, .08),
    (12, 86, .03), (24, 43, .09), (36, 75, .00), (48, 53, .05),
    (62, 78, .03), (75, 37, .09), (87, 57, .00), (98, 22, .06),
    (63, 12, .04), (30, 18, .07),
)


def _star(layer, center, width, height, ink):
    x, y = center
    waist = min(width, height) * .24
    pygame.draw.polygon(layer, ink, (
        (x, y - height), (x + waist, y - waist), (x + width, y), (x + waist, y + waist),
        (x, y + height), (x - waist, y + waist), (x - width, y), (x - waist, y - waist),
    ))


class EncoreBurst:
    def __init__(self, *, pixel: bool):
        self._scale = pygame.transform.scale if pixel else pygame.transform.smoothscale
        self._accents = ((84, 232, 222), (255, 108, 162)) if pixel else (
            (165, 235, 211), (250, 158, 180))
        self._layer = None
        self._scaled = None
        self._last_phase = None

    def _ribbons(self, phase):
        if phase >= .45:
            return
        age = phase / .45
        travel = 1 - (1 - age) ** 3
        tip = .80 + .69 * travel
        base = .04 + 1.20 * travel
        alpha = round(246 * (1 - age ** 1.35))
        for i, (dx, dy, length, width) in enumerate(_RAYS):
            def point(radius, offset=0):
                return (_CX + dx * radius - dy * offset,
                        _CY + .76 * (dy * radius + dx * offset))

            start = point(base * length)
            end = point(tip * length)
            shoulder = (.39 * base + .61 * tip) * length
            fold = width * (1 - .53 * travel)
            lit = point(shoulder, -fold)
            dark = point(shoulder - length * .09, fold * .6)
            ridge = point(shoulder, -fold * .16)
            pygame.draw.polygon(self._layer, (*_AMBER, alpha), (start, lit, end, dark))
            color = _HONEY if i % 3 else _GOLD
            pygame.draw.polygon(self._layer, (*color, alpha), (start, lit, end, ridge))
            if i % 3 == 1:
                # A sliver shears off the lit face and leads the wider ribbon.
                ahead = tip * length + 7 + 9 * travel
                offset = -fold - 4 - 5 * travel
                pygame.draw.polygon(self._layer, (*_HOT, alpha), (
                    point(ahead - 12, offset + 2), point(ahead - 4, offset - 1),
                    point(ahead + 3, offset - 2), point(ahead - 5, offset + 1)))

        # A hot four-point core holds for the hit, then contracts as the blades
        # detach. Its warm corona is local to the impact.
        core = max(0., 1 - phase / .26) ** 1.25
        if core:
            center = (_CX, _CY)
            _star(self._layer, center, 50 * core, 34 * core, (*_GOLD, round(244 * core)))
            _star(self._layer, center, 34 * core, 27 * core, (*_HOT, round(255 * core)))

    def _wave(self, age, color, strength):
        if not 0 <= age < 1:
            return
        expansion = 1 - (1 - age) ** 2
        rx, ry = 15 + 169 * expansion, 8 + 72 * expansion
        width = 1.4 + 5.5 * (1 - age)
        ink = (*color, round(strength * (1 - age ** 1.6)))
        for arc in _ARCS:
            outer = [(_CX + x * rx, _CY + y * ry) for x, y, _ in arc]
            inner = [(_CX + x * (rx - width * taper), _CY + y * (ry - width * taper))
                     for x, y, taper in reversed(arc)]
            pygame.draw.polygon(self._layer, ink, outer + inner)

    def _shower(self, phase, start, side, accent):
        # A tracer travels from the impact, then breaks into tumbling foil and
        # hot grains. Sample the same parabola twice to put tails behind heads.
        age = (phase - start) / .58
        if not 0 <= age < 1:
            return
        ox, oy = _CX + side * 64, _CY - (24 if side < 0 else 32)
        fuse = .16
        if age < fuse:
            t = age / fuse
            head = (_CX + (ox - _CX) * t, _CY + (oy - _CY) * t)
            prev = max(0., t - .62)
            tail = (_CX + (ox - _CX) * prev, _CY + (oy - _CY) * prev)
            pygame.draw.line(self._layer, (*_GOLD, 215), tail, head, 2)
            _star(self._layer, head, 6, 4, _HOT)
            return
        age = (age - fuse) / (1 - fuse)
        colors = (accent, _HONEY, _GOLD, _HOT)
        for i, (reach, lift, lag) in enumerate(_FRAGMENTS):
            t = (age - lag) / (1 - lag)
            if t < 0:
                continue
            lag_t = max(0., t - .115)
            x = ox + side * reach * t
            y = oy - lift * t + 68 * t * t
            tail = (ox + side * reach * lag_t, oy - lift * lag_t + 68 * lag_t * lag_t)
            fade = 1 - t ** 2
            color = colors[i % 4]
            pygame.draw.line(self._layer, (*color, round(173 * fade)), tail, (x, y), 2)
            if i % 3 == 0:
                _star(self._layer, (x, y), 4.7 * fade, 4.7 * fade, (*color, round(255 * fade)))
            else:
                tilt = side * math.cos(9 * t + i) * 3
                size = 1.1 + 1.5 * fade
                half_width = size * (.35 + .55 * abs(math.sin(9 * t + i)))
                pygame.draw.polygon(self._layer, (*color, round(245 * fade)), (
                    (x - tilt - half_width, y - size), (x - tilt + half_width, y - size),
                    (x + tilt + half_width, y + size), (x + tilt - half_width, y + size)))
        flash = max(0., 1 - age / .24)
        if flash:
            _star(self._layer, (ox, oy), 14 * flash, 11 * flash, (*_HOT, round(255 * flash)))

    def draw(self, surf: pygame.Surface, rect: pygame.Rect, phase: float) -> None:
        """Paint the normalized encore cue into the lane rect, under the notes."""
        if not 0 <= phase < 1:
            return
        box = pygame.Rect(rect)
        if box.w <= 0 or box.h <= 0:
            return
        size = (box.w, max(1, round(box.h * _HEIGHT / _FIELD_HEIGHT)))
        if not surf.get_clip().colliderect((box.topleft, size)):
            return
        if self._layer is None:
            self._layer = pygame.Surface((_WIDTH, _HEIGHT), pygame.SRCALPHA)
        if self._scaled is None or self._scaled.get_size() != size:
            self._scaled = pygame.Surface(size, pygame.SRCALPHA)
            self._last_phase = None
        if self._last_phase != phase:
            self._layer.fill((0, 0, 0, 0))
            self._wave((phase + .064) / .57, _HONEY, 234)
            self._wave((phase - .056) / .62, _GOLD, 190)
            self._ribbons(phase)
            self._shower(phase, .15, -1, self._accents[0])
            self._shower(phase, .42, 1, self._accents[1])
            self._scale(self._layer, size, self._scaled)
            self._last_phase = phase
        surf.blit(self._scaled, box.topleft)
