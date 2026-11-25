"""Dynamics on falling notes and the velocity readout for one piano attack."""
from __future__ import annotations

import pygame

from ..core.chart import LOUD_MIN, SOFT_MAX
from . import relay_theme as D
from .theme import SOLFEGE, TextCache


_GOLD = (255, 198, 77)
_PITCH_ORDER = {name: pitch for pitch, name in enumerate(SOLFEGE)}


def draw_touch_head(surf, text: TextCache, rect, touch) -> None:
    """Center a small dynamics badge in the slot reserved within a note head."""
    slot = pygame.Rect(rect)
    size = min(18, slot.w, slot.h)
    if touch not in ("p", "f") or size <= 0:
        return
    badge = pygame.Rect(0, 0, size, size)
    badge.center = slot.center
    inner = badge.inflate(-2, -2)
    if touch == "p":
        pygame.draw.ellipse(surf, D.BLACK, badge)
        if size >= 4:
            pygame.draw.ellipse(surf, D.MINT, inner, 1)
        ink = D.WHITE
    else:
        pygame.draw.rect(surf, D.BLACK, badge)
        if size >= 4:
            pygame.draw.rect(surf, _GOLD, inner)
        ink = D.BLACK
    if size >= 7:
        glyph = text.fit("label_bold", size - 1, touch, ink, size - 5)
        surf.blit(glyph, glyph.get_rect(center=badge.center))


def _label(surf, text, role, size, value, color, x, cy, width):
    image = text.fit(role, size, value, color, max(1, width))
    surf.blit(image, image.get_rect(midleft=(x, cy)))


def _meter(surf, x, cy, width, touch, velocity, palette, accent):
    """The colored interval is the target; the tall cursor is the actual strike."""
    track = pygame.Rect(x, cy - 3, width, 6)
    surf.fill(palette.line, track)
    if touch == "p":
        end = round((width - 1) * SOFT_MAX / 127)
        target = pygame.Rect(x, track.y, end + 1, track.h)
    else:
        start = round((width - 1) * LOUD_MIN / 127)
        target = pygame.Rect(x + start, track.y, width - start, track.h)
    surf.fill(accent, target)
    cursor = x + round((width - 1) * velocity / 127)
    surf.fill(palette.panel, (cursor - 2, cy - 6, 5, 12))
    surf.fill(palette.text, (cursor - 1, cy - 5, 3, 10))


def draw_touch_panel(surf, text: TextCache, rect, entries, *, pixel=True) -> None:
    """Draw one onset's (solfege, p/f, MIDI velocity, matched) rows, low pitch first."""
    box = pygame.Rect(rect)
    previous_clip = surf.get_clip()
    visible = box.clip(previous_clip)
    if not entries or not visible or box.w < 32 or box.h < 24:
        return
    palette = D.CONSOLE if pixel else D.ILLUSTRATION
    inner = box.inflate(-16, -6)
    note_x = inner.x + round(inner.w * .14)
    goal_x = inner.x + round(inner.w * .25)
    meter_x = inner.x + round(inner.w * .44)
    value_x = inner.x + round(inner.w * .72)
    result_x = inner.x + round(inner.w * .81)
    header_h = min(19, box.h // 4)
    rows_top = inner.y + header_h + 2
    rows = sorted(entries[:2], key=lambda row: _PITCH_ORDER.get(row[0].replace("#", "♯"), 12))
    badge_size = min(18, (inner.bottom - rows_top) // len(rows) - 2)

    surf.set_clip(visible)
    try:
        pygame.draw.rect(surf, palette.panel, box, border_radius=palette.radius)
        pygame.draw.rect(surf, palette.line, box, 1, border_radius=palette.radius)
        for title, x, end in (("연주음", inner.x, goal_x), ("목표", goal_x, meter_x),
                              ("입력 세기", meter_x, result_x), ("결과", result_x, inner.right)):
            _label(surf, text, "sans_bold", 13, title, palette.muted, x,
                   inner.y + header_h // 2, end - x - 3)
        surf.fill(palette.line, (inner.x, rows_top - 2, inner.w, 1))

        for index, (name, touch, velocity, matched) in enumerate(rows):
            cy = rows_top + (inner.bottom - rows_top) * (2 * index + 1) // (2 * len(rows))
            register = "단음" if len(rows) == 1 else ("낮은 음", "높은 음")[index]
            _label(surf, text, "sans", 14, register, palette.muted, inner.x, cy,
                   note_x - inner.x - 4)
            # The bundled Korean typeface lacks a printable musical sharp.
            _label(surf, text, "sans_bold", 18, name.replace("♯", "#"), palette.text,
                   note_x, cy, goal_x - note_x - 5)
            draw_touch_head(surf, text, (goal_x, cy - badge_size // 2, badge_size, badge_size), touch)
            limit_x = goal_x + badge_size + 3
            limit = f"≤{SOFT_MAX}" if touch == "p" else f"≥{LOUD_MIN}"
            _label(surf, text, "label_bold", 18, limit, palette.text, limit_x, cy, meter_x - limit_x - 5)

            velocity = max(0, min(127, velocity))
            if touch == "p":
                accent = D.CYAN if pixel else (37, 109, 99)
            else:
                accent = _GOLD if pixel else (155, 82, 34)
            _meter(surf, meter_x, cy, max(1, value_x - meter_x - 7), touch, velocity, palette, accent)
            _label(surf, text, "num", 20, str(velocity), palette.text, value_x, cy, result_x - value_x - 5)
            result = "일치" if matched else ("더 여리게" if touch == "p" else "더 세게")
            ink = palette.text if matched else (D.ORANGE if pixel else D.ROSE)
            _label(surf, text, "sans_bold", 16, result, ink, result_x, cy, inner.right - result_x)
    finally:
        surf.set_clip(previous_clip)
