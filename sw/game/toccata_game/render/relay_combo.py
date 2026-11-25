"""Song-clock combo counter, radio checkpoints and hundred-hit encore stamps."""

from __future__ import annotations

import math
from contextlib import contextmanager
from functools import lru_cache

import pygame

from . import relay_theme as D
from .theme import TextCache, mix


_GOLD = (255, 198, 77)
_FOIL = (255, 250, 224)
_BRONZE = (155, 76, 40)


@contextmanager
def _clipped(surf, box):
    previous = surf.get_clip()
    visible = previous.clip(box)
    try:
        surf.set_clip(visible)
        yield bool(visible)
    finally:
        surf.set_clip(previous)


def _size(width, height):
    return max(1, round(width)), max(1, round(height))


def _tint(mask, color):
    result = mask.copy()
    result.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return result


class ComboDisplay:
    def __init__(self, text: TextCache, *, pixel: bool):
        self.text = text
        self.pixel = pixel
        self.dark = D.BLACK if pixel else D.DEEP
        self.signal = D.CYAN if pixel else D.MINT
        self.resize = pygame.transform.scale if pixel else pygame.transform.smoothscale
        # Keep only recent compositions. Numbers reuse ten glyphs in the shared TextCache.
        self._number = lru_cache(maxsize=12)(self._make_number)
        self._word = lru_cache(maxsize=24)(self._make_word)
        self._plate = lru_cache(maxsize=4)(self._make_plate)

    def _make_word(self, word, height, width, ink):
        source = self.text.spaced("label_bold", 38, word, ink, 3)
        source = source.subsurface(source.get_bounding_rect())
        return self.resize(source, _size(min(width, height * source.get_width() / source.get_height()), height))

    def _make_number(self, value, height, max_width, accent):
        glyphs = [self.text.tight("num", 96, ch, (255, 255, 255)) for ch in str(value)]
        mask = pygame.Surface((sum(g.get_width() for g in glyphs) + 3 * (len(glyphs) - 1),
                               max(g.get_height() for g in glyphs)), pygame.SRCALPHA)
        x = 0
        for glyph in glyphs:
            mask.blit(glyph, (x, mask.get_height() - glyph.get_height()))
            x += glyph.get_width() + 3

        depth = max(1, round(height * .08))
        edge = max(1, round(height * .025))
        h = max(1, height - depth - 2 * edge)
        lean = round(h * .24)
        w = max(1, min(max_width - lean - depth - 2 * edge, round(h * mask.get_width() / mask.get_height())))
        mask = self.resize(mask, (w, h))
        if self.pixel:
            mask = pygame.mask.from_surface(mask).to_surface(setcolor="white", unsetcolor=(0, 0, 0, 0))
        slant = pygame.Surface((w + lean, h), pygame.SRCALPHA)
        step = 2 if self.pixel else 1
        for y in range(0, h, step):
            dx = round(lean * (1 - y / max(1, h - 1)) / step) * step
            slant.blit(mask, (min(lean, dx), y), (0, y, w, step))

        face = slant.copy()
        light = mix(accent, _FOIL, .88)
        horizon = h // 2
        for y in range(h):
            if y < horizon:
                color = mix(light, mix(accent, _FOIL, .49), y / max(1, horizon))
            else:
                color = mix(accent, light, .8 * (y - horizon) / max(1, h - horizon - 1))
            if y in (horizon - 1, h - 1):
                color = _FOIL
            face.fill(color, (0, y, face.get_width(), 1), special_flags=pygame.BLEND_RGB_MULT)

        ink = _tint(slant, self.dark)
        bevel = _tint(slant, mix(self.dark, accent, .46))
        sprite = pygame.Surface((slant.get_width() + depth + 2 * edge, height), pygame.SRCALPHA)
        origin = depth + edge
        for z in range(depth, -1, -1):
            x, y = origin - z, edge + z
            if z in (0, depth):
                for dx, dy in ((-edge, 0), (edge, 0), (0, -edge), (0, edge)):
                    sprite.blit(ink, (x + dx, y + dy))
            sprite.blit(bevel if z else face, (x, y))
        return sprite, slant, (origin, edge)

    def counter(self, surf, rect, combo: int, age_ms: float) -> None:
        """Draw the current run. age_ms is elapsed song time since the hit."""
        box = pygame.Rect(rect)
        with _clipped(surf, box) as visible:
            if not visible:
                return
            tier = sum(combo >= threshold for threshold in (1, 10, 30, 50, 100))
            inks = (D.STEEL, self.signal, (141, 189, 255), D.HOT if self.pixel else D.PINK,
                    (255, 149, 91), _GOLD)
            accent = inks[tier]
            horizontal = box.w >= box.h * 2.4
            if horizontal:
                digits = pygame.Rect(box.x, box.y, round(box.w * .56), box.h)
                caption = pygame.Rect(digits.right, box.y, box.right - digits.right, box.h)
            else:
                digits = pygame.Rect(box.x, box.y, box.w, round(box.h * .74))
                caption = pygame.Rect(box.x, digits.bottom, box.w, box.bottom - digits.bottom)

            stamp, _, _ = self._number(combo, max(1, round(digits.h * .88)), round(digits.w * .86), accent)
            if combo and 0 <= age_ms < 230:
                t = age_ms / 230
                punch = (1 - t) ** 2 * math.cos(t * 2 * math.pi)
                stamp = self.resize(stamp, _size(stamp.get_width() * (1 + .17 * punch),
                                                 stamp.get_height() * (1 - .21 * punch)))
            surf.blit(stamp, stamp.get_rect(midbottom=(digits.centerx, digits.bottom - round(digits.h * .04))))

            label_h = max(1, round(min(box.h * .32, caption.h * .47, box.w * .085)))
            label = self._word("COMBO", label_h, round(caption.w * .88), mix(accent, D.CREAM, .58))
            left = caption.x + round(caption.w * .04) if horizontal else caption.centerx - label.get_width() // 2
            top = caption.centery - label_h // 2 - 1
            surf.blit(label, (left, top))
            # Five segments under the call sign mark the current colour tier.
            pitch = max(2, label.get_width() // 5)
            y = top + label_h + max(2, label_h // 4)
            for i in range(5):
                x = left + i * pitch
                surf.fill(accent if i < tier else mix(self.dark, D.STEEL, .35),
                          (x, y, max(1, pitch - 2), max(1, label_h // 6)))

    def checkpoint(self, surf, rect, value: int, phase: float) -> None:
        """Pulse at 50, 150, ... over the caller's roughly 600 ms interval."""
        if value <= 0 or value % 100 != 50 or not 0 <= phase < 1:
            return
        box = pygame.Rect(rect)
        with _clipped(surf, box) as visible:
            if not visible:
                return
            h = max(1, round(.76 * box.h))
            pad = max(1, round(.17 * h))
            icon_w = round(.82 * h)
            gap = max(1, round(.13 * h))
            room = max(2, box.w - icon_w - 2 * pad - gap)
            word = self._word("COMBO", max(1, round(.39 * h)), round(.55 * room), self.signal)
            number = self._word(str(value), max(1, round(.62 * h)), room - word.get_width(), D.CREAM)
            w = min(box.w, icon_w + number.get_width() + gap + word.get_width() + 2 * pad)
            badge = pygame.Surface((w, h), pygame.SRCALPHA)
            cut = min(pad, w // 2)
            rim = [(cut, 0), (w - 1, 0), (w - 1, h - 1 - cut), (w - 1 - cut, h - 1),
                   (0, h - 1), (0, cut)]
            body = mix(self.dark, self.signal, .13)
            pygame.draw.polygon(badge, body, rim)
            pygame.draw.polygon(badge, mix(body, self.signal, .58), rim, 1)

            center = (pad + icon_w // 2, h // 2)
            for delay in (0., .18):
                wave = (phase - delay) / .58
                if 0 <= wave < 1:
                    radius = max(1, round(h * (.13 + .26 * wave)))
                    pygame.draw.circle(badge, mix(self.signal, body, wave), center, radius, 1)
            pygame.draw.circle(badge, D.CREAM, center, max(1, round(.08 * h)))
            x = pad + icon_w
            badge.blit(number, number.get_rect(midleft=(x, h // 2)))
            badge.blit(word, word.get_rect(midleft=(x + number.get_width() + gap, h // 2)))
            if phase > .72:
                badge.set_alpha(round(255 * (1 - phase) / .28))
            surf.blit(badge, badge.get_rect(midleft=box.midleft))

    def _make_plate(self, w, h, value):
        plate = pygame.Surface((w, h), pygame.SRCALPHA)
        body = D.GLASS if self.pixel else (62, 39, 66)
        facet = (37, 64, 80) if self.pixel else (104, 56, 76)
        trim = D.HOT if self.pixel else (255, 140, 106)

        def polygon(ink, points):
            pygame.draw.polygon(plate, ink, [(round(x * (w - 1)), round(y * (h - 1))) for x, y in points])

        # Split the ends of the ribbon into pinstripes; the gaps show the stage behind it.
        polygon(_BRONZE, ((.097, .21), (.99, .21), (.91, .82), (.62, .82),
                          (.60, .95), (.07, .95), (.12, .59), (.05, .59)))
        polygon(self.dark, ((.091, .15), (.987, .15), (.904, .77), (.59, .77),
                            (.57, .90), (.066, .90), (.11, .53), (.041, .53)))
        polygon(body, ((.109, .19), (.966, .19), (.893, .73), (.58, .73),
                       (.56, .85), (.09, .85), (.14, .48), (.07, .48)))
        polygon(facet, ((.17, .20), (.52, .20), (.35, .84), (.09, .84)))
        polygon(_GOLD, ((.10, .12), (.975, .12), (.969, .16), (.094, .16)))
        polygon(trim, ((.11, .89), (.44, .89), (.427, .94), (.10, .94)))
        streaks = ((.022, .13, .27), (0, .12, .34), (.03, .06, .41), (.84, .14, .85), (.78, .15, .90))
        for x, length, y in streaks:
            polygon(trim if y == .34 else _GOLD,
                    ((x + .009, y), (x + length, y), (x + length - .009, y + .025), (x, y + .025)))
        for x in (.86, .89, .92):
            polygon(facet, ((x, .25), (x + .018, .25), (x - .017, .54), (x - .035, .54)))

        # The digits break through the top rail. Their optical right edge anchors both labels.
        number, face, inset = self._number(value, max(1, round(.88 * h)), round(.45 * w), _GOLD)
        number_box = number.get_rect(midright=(round(.567 * w), round(.47 * h)))
        plate.blit(number, number_box)
        left = round(.59 * w)
        word = self._word("COMBO", max(1, round(.22 * h)), round(.263 * w), _FOIL)
        plate.blit(word, (left, round(.27 * h)))
        tag = self._word("ENCORE", max(1, round(.145 * h)), round(.215 * w), self.dark)
        tab = pygame.Rect(left - round(.02 * w), round(.545 * h), tag.get_width() + round(.077 * w),
                          max(1, round(.23 * h)))
        cut = round(tab.h * .38)
        pygame.draw.polygon(plate, _GOLD, [(tab.left + cut, tab.top), tab.topright,
                                           (tab.right - cut, tab.bottom), tab.bottomleft])
        plate.blit(tag, tag.get_rect(center=tab.center))
        return plate, face, (number_box.x + inset[0], number_box.y + inset[1])

    @staticmethod
    def _foil_sweep(plate, face, position, progress):
        """Move reflected light across the gold face, leaving its extrusion in shadow."""
        w, h = face.get_size()
        band = max(2, round(.20 * h))
        skew = round(.38 * h)
        x = round(progress * (w + skew + band)) - band
        gleam = pygame.Surface((w, h), pygame.SRCALPHA)
        for dx, width, alpha in ((0, band, 190), (-band // 2, max(1, band // 4), 85)):
            left = x + dx
            pygame.draw.polygon(gleam, (255, 255, 246, alpha),
                                [(left, 0), (left + width, 0), (left + width - skew, h), (left - skew, h)])
        gleam.blit(face, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        plate.blit(gleam, position)

    def milestone(self, surf, rect, value: int, phase: float) -> None:
        """Show a hundred-hit encore for one normalized interval on the caller's clock."""
        if value <= 0 or value % 100 or not 0 <= phase < 1:
            return
        box = pygame.Rect(rect)
        with _clipped(surf, box) as visible:
            if not visible:
                return
            base, face, position = self._plate(box.w, box.h, value)
            plate = base.copy()
            if phase < .17:
                self._foil_sweep(plate, face, position, .27 + .73 * phase / .17)
            elif .25 <= phase < .43:
                self._foil_sweep(plate, face, position, (phase - .25) / .18)

            # A live scope in the leading tip of the ribbon.
            cy = round(.65 * box.h)
            trace = []
            for i in range(17):
                t = i / 16
                level = math.sin(t * math.pi) ** 2 * math.sin(t * 4 * math.pi - phase * 16)
                px = round((.028 + .126 * t) * box.w)
                py = cy + round(level * box.h * .12)
                if self.pixel and trace:
                    trace.append((px, trace[-1][1]))
                trace.append((px, py))
            pygame.draw.lines(plate, self.signal, False, trace, max(1, round(box.h / 48)))

            # A short specular flash passes between two corners of the foil.
            for px, py, at in ((.535, .14, .045), (.60, .79, .32)):
                shine = max(0., 1 - abs(phase - at) / .12)
                if shine:
                    cx, cy = round(px * box.w), round(py * box.h)
                    r = max(1, round(shine * box.h * .13))
                    n = max(1, r // 4)
                    pygame.draw.polygon(plate, _FOIL, [(cx, cy - r), (cx + n, cy - n), (cx + r, cy), (cx + n, cy + n),
                                                       (cx, cy + r), (cx - n, cy + n), (cx - r, cy), (cx - n, cy - n)])
            if phase < .20:
                # Foil flecks fly out from the perimeter as the stamp makes contact.
                t = phase / .20
                tail = .68 * (1 - t)
                edge = max(1, round(.043 * box.h * (1 - t)))
                for px, py, dx, dy in ((.10, .21, -.08, -.17), (.11, .55, -.10, .11),
                                       (.27, .84, -.09, .14), (.71, .14, .09, -.12),
                                       (.89, .24, .10, -.15), (.89, .67, .09, .18)):
                    x = (px + dx * t) * box.w
                    y = (py + dy * t) * box.h
                    tip = (round(x + dx * tail * box.w), round(y + dy * tail * box.h))
                    pygame.draw.polygon(plate, _FOIL if dy < 0 else _GOLD,
                                        [(round(x), round(y - edge)), tip, (round(x), round(y + edge))])

                punch = (1 - t) ** 2 * math.cos(math.tau * t)
                plate = self.resize(plate, _size(box.w * (1 + .15 * punch), box.h * (1 - .16 * punch)))
            if phase > .73:
                plate.set_alpha(round(255 * (1 - phase) / .27))
            surf.blit(plate, plate.get_rect(center=box.center))
