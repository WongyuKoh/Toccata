"""The rooftop stage apron and pitch contacts below the relay's timing rail."""

from __future__ import annotations

import math
from functools import lru_cache

import pygame

from . import relay_theme as D
from .geometry import KeyLayout
from .theme import mix


_CLEAR_DEPTH = 56  # Room for a note to pass the rail before the floor hardware.


def _monitor(pixel, ink):
    """A low wedge monitor, with a sloped grille and a recessed side handle."""
    monitor = pygame.Surface((104, 36), pygame.SRCALPHA)
    shell = D.BLACK if pixel else D.DEEP
    rim = D.BEZEL if pixel else D.VIOLET
    grille = mix(shell, rim, .40)
    pygame.draw.ellipse(monitor, (*shell, 100), (1, 26, 103, 10))
    pygame.draw.polygon(monitor, shell, [(0, 23), (13, 3), (87, 0), (103, 23),
                                         (96, 31), (13, 34), (0, 29)])
    pygame.draw.polygon(monitor, grille, [(4, 23), (15, 5), (84, 2), (73, 21)])
    pygame.draw.lines(monitor, mix(grille, ink, .35), False, [(4, 23), (15, 4), (85, 1)])
    for driver in (pygame.Rect(19, 8, 24, 12), pygame.Rect(51, 5, 16, 9)):
        pygame.draw.ellipse(monitor, shell, driver)
        pygame.draw.ellipse(monitor, mix(grille, rim, .38), driver, 1)
    for row in range(4):
        x = 17 - row * 2
        pygame.draw.line(monitor, mix(grille, shell, .55), (x, 8 + row * 4),
                         (x + 62, 5 + row * 4))
    pygame.draw.lines(monitor, grille, False, [(75, 23), (87, 4), (99, 23)])
    pygame.draw.line(monitor, grille, (84, 23), (93, 22), 2)
    pygame.draw.line(monitor, mix(grille, ink, .72), (12, 28), (21, 28), 2)
    return monitor


@lru_cache(maxsize=6)
def _deck(width, depth, pixel, lane_centers):
    """Bake the reflected light, calibrated lane guides and fixed stage furniture."""
    far = D.GLASS if pixel else D.NAVY
    near = (37, 55, 72) if pixel else (75, 57, 87)
    white, black = (D.CYAN, D.HOT) if pixel else (D.MINT, D.ORANGE)
    trim = D.STEEL if pixel else D.LAVENDER

    # Two broad pools of light spread from either wing towards the foreground.
    wash = pygame.Surface((49, 13), depth=32)
    for row in range(13):
        z = row / 12
        base = mix(far, near, z)
        for col in range(49):
            u = col / 48
            edge = min(u, 1 - u)
            light = max(0., 1 - abs(edge - .12) / (.17 + .23*z))
            ink = white if u < .5 else black
            wash.set_at((col, row), mix(base, ink, (.05 + .23*z) * light**2))
    floor = pygame.transform.smoothscale(wash, (width, depth))

    # Pitch guides stay vertical. The receding panel seams begin beyond them.
    guide_depth = min(depth, _CLEAR_DEPTH)
    for x in lane_centers:
        if 0 <= x < width:
            for y in range(3, guide_depth):
                floor.set_at((x, y), mix(floor.get_at((x, y)), trim, .20*(1 - y/guide_depth)))
    start = max(_CLEAR_DEPTH, round(depth * .32))
    room = depth - start
    if room > 0:
        seam = mix(near, trim, .13)
        for i in range(-4, 5):
            x0 = round(width * (.5 + i * .14))
            x1 = round(width * (.5 + i * .25))
            pygame.draw.line(floor, seam, (x0, start), (x1, depth - 1))
        for distance in (0., .33, .92):
            y = start + round((room - 1) * distance)
            pygame.draw.line(floor, seam, (0, y), (width - 1, y))
        # Inset strips catch the coloured light along the outer panel seams.
        for side, ink in ((-1, white), (1, black)):
            for z0, z1 in ((.39, .57), (.63, .71)):
                ends = [(round(width * (.5 + side * (.28 + .22*z))), start + round((room - 1)*z))
                        for z in (z0, z1)]
                pygame.draw.line(floor, mix(near, ink, .38), *ends, 2)
    # The caller may overlay pitch names in the last 22 px of the page.
    if room >= 58 and width >= 260:
        margin = min(46, width // 28)
        y = depth - 58
        floor.blit(_monitor(pixel, white), (margin, y))
        right = pygame.transform.flip(_monitor(pixel, black), True, False)
        floor.blit(right, (width - margin - right.get_width(), y))
    return floor


def draw_runout(surf, layout: KeyLayout, *, bottom, now, beat_ms, down, hits, active_keys, pixel):
    """Draw the timing rail and apron up to exclusive bottom. Hits map pitches to song ms."""
    y = round(layout.land_y)
    width = surf.get_width()
    depth = min(round(bottom), surf.get_height()) - y
    old_clip = surf.get_clip()
    clip = old_clip.clip((0, y - 3, width, depth + 3))
    if depth <= 0 or not clip:
        return

    pitches = [(note, round(layout.x(note))) for note in range(layout.base, layout.base + 12)]
    lanes = tuple(x for note, x in pitches if note in active_keys)
    shadow, metal, edge = (D.BLACK, D.STEEL, D.WHITE) if pixel else (D.DEEP, D.LAVENDER, D.CREAM)
    white, black = (D.CYAN, D.HOT) if pixel else (D.MINT, D.ORANGE)
    beat = now / beat_ms if beat_ms > 0 else 0.
    pulse = .5 + .5 * math.cos(math.tau * beat)

    surf.set_clip(clip)
    try:
        surf.blit(_deck(width, depth, pixel, lanes), (0, y))
        surf.fill(shadow, (0, y-2, width, 6))
        surf.fill(mix(shadow, metal, .65), (0, y-1, width, 4))
        surf.fill(edge, (0, y, width, 1))
        for end, step, ink in ((0, 1, white), (width - 1, -1, black)):
            bracket = [(end, y-3), (end+22*step, y-3), (end+15*step, y+6), (end, y+6)]
            pygame.draw.polygon(surf, shadow, bracket)
            pygame.draw.lines(surf, metal, False, bracket[:3])
            lamp = mix(shadow, ink, .52 + .35*pulse)
            pygame.draw.line(surf, lamp, (end+3*step, y), (end+13*step, y), 2)

        for note, x in pitches:
            sharp = layout.is_black(note)
            ink = black if sharp else white
            age = now - hits.get(note, -math.inf)
            attack = (1 - age / 200)**2 if 0 <= age < 200 else 0.
            light = max(attack, .72 if note in down else 0.)
            idle = .54 if note in active_keys else .22
            color = mix(shadow, ink, idle + (1-idle)*light)
            key_width = layout.black_w if sharp else layout.white_w
            half = max(2, min(13, round(key_width * .09)))
            bevel = min(4 if sharp else 1, half)
            pad = [(x-half+bevel, y+2), (x+half, y+2),
                   (x+half-bevel, y+5), (x-half, y+5)]
            pygame.draw.polygon(surf, color, pad)
            if light:
                pygame.draw.line(surf, mix(color, edge, .60*light), (x-half+bevel, y), (x+half, y))
                pygame.draw.line(surf, color, (x, y+5), (x, y+5+round(6*light)))
    finally:
        surf.set_clip(old_clip)
