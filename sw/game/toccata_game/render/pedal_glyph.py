"""Pixel-art foot and hinged damper pedal for the note lanes and HUD."""

from functools import lru_cache

import pygame


_SIZE = (22, 18)
# The cuff, two laces, heel patch and welt move together around the heel.
_SHOE = (
    "  iiiii",
    "  isssi",
    "  isssi",
    "  isssi",
    " iisssii",
    " iaiiiipi",
    " iaappipii",
    " iaapppipppi",
    " iaappaappppiii",
    " iappppaappppppi",
    " isssssssssssssi",
    " iiiiiiiiiiiiii",
)
# Toe rise above the heel, and height of the pedal's free end in sprite coordinates.
_POSE = {"press": (4, 12), "held": (1, 14), "lift": (8, 11)}
_DOWN = (
    "  iiii  ",
    "  iaai  ",
    "  iaai  ",
    "iiiaaiii",
    " iaaaai ",
    "  iaai  ",
    "   ii   ",
)


@lru_cache(maxsize=96)
def _sprite(size, pose, ink, accent):
    sprite = pygame.Surface(_SIZE, pygame.SRCALPHA)
    rise, tip_y = _POSE[pose]
    # A light shoe reads on an ink outline; reverse the values for a light outline.
    leather = (255, 246, 220) if sum(ink[:3]) < 500 else (57, 71, 92)
    palette = {"i": ink, "a": accent, "p": leather, "s": (157, 178, 196)}
    for y, row in enumerate(_SHOE):
        for x, pixel in enumerate(row):
            if pixel != " ":
                lift = round(rise * max(0, x-2) / 13)
                sprite.set_at((x, y+4-lift), palette[pixel])

    # The free end of the brass lever is beneath the ball of the foot.
    steel = (117, 134, 153)
    pygame.draw.line(sprite, ink, (1, 16), (5, 16))
    pygame.draw.line(sprite, steel, (1, 17), (21, 17))
    pygame.draw.line(sprite, ink, (12, tip_y), (20, 14), 2)
    pygame.draw.line(sprite, accent, (12, tip_y), (19, 14))
    pygame.draw.rect(sprite, ink, (18, 13, 4, 4))
    pygame.draw.line(sprite, steel, (20, 14), (20, 16))
    sprite.set_at((19, 14), accent)
    if pose != "held":
        rows = _DOWN if pose == "press" else reversed(_DOWN)
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                if pixel != " ":
                    sprite.set_at((14+x, y), palette[pixel])
    return pygame.transform.scale(sprite, size)


def draw_pedal_glyph(surf, rect, pose, *, ink, accent):
    """Draw a press, held or lift pose inside rect, respecting the surface clip."""
    box = pygame.Rect(rect)
    if box.w <= 0 or box.h <= 0 or not surf.get_clip().colliderect(box):
        return
    icon = _sprite(box.size, pose, tuple(pygame.Color(ink)), tuple(pygame.Color(accent)))
    surf.blit(icon, box.topleft)
