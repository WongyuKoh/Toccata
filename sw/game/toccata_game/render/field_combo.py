"""Live combo and judgment lettering for the rooftop note field."""

from __future__ import annotations

import math
from functools import lru_cache

import pygame

from . import relay_theme as D
from .theme import TextCache, mix


_WHITE = (255, 255, 255)
_KEYLINE = (21, 23, 41)
_PEARL = (255, 250, 231)
_SEA_GLASS = (158, 217, 219)
_GOLD = (255, 203, 109)


def _tint(mask, ink):
    sprite = mask.copy()
    sprite.fill(ink, special_flags=pygame.BLEND_RGB_MULT)
    return sprite


class FieldCombo:
    def __init__(self, text: TextCache, *, pixel: bool):
        self.text = text
        self.pixel = pixel
        self.signal = D.CYAN if pixel else D.MINT
        self.grades = {
            "PERFECT": self.signal,
            "GREAT": D.WHITE if pixel else D.CREAM,
            "GOOD": D.STEEL if pixel else D.ORANGE,
            "MISS": D.HOT if pixel else D.PINK,
        }
        # The shared text cache only sees ten digits and five fixed words.
        self.digits = tuple(text.render("display", 104, str(i), _WHITE) for i in range(10))
        self._number = lru_cache(maxsize=20)(self._make_number)
        self._word = lru_cache(maxsize=24)(self._make_word)

    def _fit_mask(self, source, height, width):
        bounds = source.get_bounding_rect()
        scale = min(max(1, height) / bounds.h, max(1, width) / bounds.w)
        size = max(1, round(bounds.w * scale)), max(1, round(bounds.h * scale))
        mask = pygame.transform.smoothscale(source.subsurface(bounds), size)
        # Preserve partial coverage on the small legends; their counters can be subpixel.
        if self.pixel and size[1] >= 18:
            mask = pygame.mask.from_surface(mask).to_surface(setcolor=_WHITE, unsetcolor=(0, 0, 0, 0))
        return mask

    def _make_number(self, combo, height, width):
        glyphs = [self.digits[int(d)] for d in str(combo)]
        # Keep the font's bearings and baseline, including the round overshoot on 0 and 8.
        tracking = 3
        run = pygame.Surface((sum(g.get_width() for g in glyphs) + tracking * (len(glyphs) - 1),
                              glyphs[0].get_height()), pygame.SRCALPHA)
        x = 0
        for glyph in glyphs:
            run.blit(glyph, (x, 0))
            x += glyph.get_width() + tracking
        mask = self._fit_mask(run, height, width)
        w, h = mask.get_size()
        edge = max(1, round(h * .043))
        depth = max(1, round(h * .05))
        sprite = pygame.Surface((w + 2 * edge, h + 2 * edge + depth), pygame.SRCALPHA)

        # The dark rim separates the face from crossing notes and the bright encore lamps.
        rim = _tint(mask, _KEYLINE)
        for dx, dy in ((-edge, 0), (0, -edge), (edge, 0), (-edge, depth), (0, depth + edge), (edge, depth)):
            sprite.blit(rim, (edge + dx, edge + dy))
        sprite.blit(_tint(mask, (65, 129, 151)), (edge, edge + depth))
        face = mask.copy()
        for y in range(h):
            t = y / max(1, h - 1)
            shade = max(0., (t - .45) / .55)
            ink = mix(_PEARL, _SEA_GLASS, shade * shade)
            face.fill(ink, (0, y, w, 1), special_flags=pygame.BLEND_RGB_MULT)
        sprite.blit(face, (edge, edge))
        return sprite

    def _make_word(self, word, height, width):
        caption = word == "COMBO"
        source = self.text.spaced("label_bold", 48, word, _WHITE, 14 if caption else 5)
        mask = self._fit_mask(source, height, width)
        pad = 1 if caption else max(1, round(height / 11))
        w, h = mask.get_size()
        result = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
        rim = _tint(mask, _KEYLINE)
        for x, y in ((0, pad), (pad, 0), (2 * pad, pad), (pad, 2 * pad)):
            result.blit(rim, (x, y))
        result.blit(_tint(mask, _PEARL if caption else self.grades[word]), (pad, pad))
        return result

    def _accents(self, surf, number, box_width, milestone, phase):
        """Fifty broadcasts two wavefronts. A hundred strikes a pair of foil stars."""
        if milestone <= 0 or milestone % 50 or not 0 <= phase < 1:
            return
        # A four-digit run may leave just a few pixels for each ornament.
        room = (box_width - number.w) // 2
        h = min(number.h, (room - 2) * 2)
        if h < 8:
            return
        encore = milestone % 100 == 0
        w = max(6, round(h * .4))
        mark = pygame.Surface((w, h), pygame.SRCALPHA)
        cy = h // 2
        if encore:
            for delay, px, py, radius in ((0., .36, .44, .14), (.18, .76, .61, .07)):
                t = phase - delay
                if t < 0:
                    continue
                pulse = max(0., 1 - t / .82)
                r = max(1, round(h * radius * pulse))
                cx, sy = round(w * px), round(h * (py - .13 * t))
                points = [(cx, sy-r), (cx+1, sy-1), (cx+r, sy), (cx+1, sy+1),
                          (cx, sy+r), (cx-1, sy+1), (cx-r, sy), (cx-1, sy-1)]
                pygame.draw.polygon(mark, _GOLD, points)
                mark.set_at((cx, sy), _PEARL)
        else:
            for i in range(2):
                radius = max(3, round(h * (.15 + .10 * i + .08 * phase)))
                arc = [(1 + round(radius * math.cos(a)), cy + round(radius * math.sin(a)))
                       for a in (-.8, -.6, -.4, -.2, 0., .2, .4, .6, .8)]
                pygame.draw.lines(mark, self.signal, False, arc, max(1, round(h * .035)))
        mark.set_alpha(round(255 * min(1., (1 - phase) / .34)))
        gap = max(2, round(h * .055))
        surf.blit(mark, mark.get_rect(midleft=(number.right + gap, number.centery)))
        mirrored = pygame.transform.flip(mark, True, False)
        surf.blit(mirrored, mirrored.get_rect(midright=(number.left - gap, number.centery)))

    def draw(self, surf, rect, combo, age_ms, *, milestone=0, phase=-1.0, grade=None):
        box = pygame.Rect(rect)
        previous = surf.get_clip()
        visible = previous.clip(box)
        if not visible:
            return
        surf.set_clip(visible)
        try:
            live = combo > 0 and grade != "MISS"
            if grade in self.grades:
                height = round(box.h * (.15 if live else .28))
                judgment = self._word(grade, height, box.w - 4)
                y = box.y + round(box.h * .106) if live else box.centery
                surf.blit(judgment, judgment.get_rect(center=(box.centerx, y)))
            if not live:
                return

            stamp = self._number(combo, round(box.h * .49), round(box.w * .84))
            # A short key travel, followed by one recoil. All digits move on the same baseline.
            travel = 0
            if 0 <= age_ms < 155:
                t = age_ms / 155
                travel = round(.036 * box.h * (1 - t) ** 2 * math.cos(math.tau * t))
            number = stamp.get_rect(center=(box.centerx, box.y + round(.51 * box.h) + travel))
            surf.blit(stamp, number)
            self._accents(surf, number, box.w, milestone, phase)

            word = self._word("COMBO", round(box.h * .107), box.w - 4)
            caption = word.get_rect(center=(box.centerx, box.y + round(box.h * .923)))
            surf.blit(word, caption)
            # Short stereo-meter ticks flank the baseline of the station lettering.
            unit = max(1, round(box.h / 56))
            for side, end in ((-1, caption.left), (1, caption.right)):
                for i, level in enumerate((2, 3, 1)):
                    x = end + side * (3 + (2 * i + 1) * unit)
                    surf.fill(self.signal, (x, caption.centery - level * unit // 2, unit, level * unit))
        finally:
            surf.set_clip(previous)
