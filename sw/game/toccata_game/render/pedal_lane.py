"""A side-scrolling sustain-pedal part for the strip below the piano keys."""
from __future__ import annotations

import math

import pygame

from . import relay_theme as D
from .theme import mix


# The illustrated playfield uses the dark rooftop inks beneath its keys.
_ROOFTOP = D.MenuInks(D.DEEP, D.NAVY, D.CREAM, D.LAVENDER, D.VIOLET, D.MINT, D.PANEL, 5)


def _pedal(surf, x, y, pressed, ink, base):
    """Side view, with a fixed heel and a toe that travels with the real input."""
    toe = y + (3 if pressed else -8)
    pygame.draw.rect(surf, base, (x, y + 9, 34, 4))
    pygame.draw.polygon(surf, ink, [(x + 3, y + 4), (x + 27, toe - 2),
                                    (x + 32, toe), (x + 30, toe + 3), (x + 3, y + 8)])
    pygame.draw.circle(surf, base, (x + 5, y + 6), 2)


def _marker(surf, x, y, down, ink, field, radius):
    """A solid down-chevron starts a ribbon; an open up-chevron ends it."""
    badge = pygame.Rect(x - 7, y - 7, 15, 15)
    pygame.draw.rect(surf, ink if down else field, badge, border_radius=radius)
    if not down:
        pygame.draw.rect(surf, ink, badge, 1, border_radius=radius)
    dy = 2 if down else -2
    pygame.draw.lines(surf, field if down else ink, False,
                      [(x - 4, y - dy), (x, y + dy), (x + 4, y - dy)], 2)


def _timeline(surf, text, track, spans, now, beat, palette):
    field, ink = palette.background, palette.accent
    pygame.draw.rect(surf, field, track, border_radius=palette.radius)
    cursor = track.x + track.w // 10
    stride = (track.right - 1 - cursor) / 4  # Four beats ahead, regardless of tempo.
    cy = track.y + track.h * 2 // 3

    def position(at):
        return cursor + round((at - now) / beat * stride)

    # Fixed distance labels and a moving song-beat grid serve different readings.
    for beats, label in enumerate(("지금", "+1박", "+2박", "+3박")):
        glyph = text.tight("sans_bold", 12, label, palette.text if beats == 0 else palette.muted)
        x = cursor + round(beats * stride)
        surf.blit(glyph, glyph.get_rect(center=(x, track.y + 8)))
    half_beat = math.floor(now / beat * 2)
    for step in range(half_beat - 1, half_beat + 10):
        x = position(step * beat / 2)
        if step % 2 == 0:
            pygame.draw.line(surf, palette.line, (x, cy - 8), (x, cy + 8))
        height = 5 if step % 8 == 0 else (3 if step % 2 == 0 else 1)
        surf.fill(palette.muted if step % 8 == 0 else palette.line, (x, track.bottom - height, 2, height))
    pygame.draw.line(surf, palette.line, (track.x, cy), (track.right - 1, cy))

    active = next_start = last_end = None
    earliest = now - (cursor - track.x + 8) / stride * beat
    latest = now + (track.right - cursor + 8) / stride * beat
    for span in spans:
        if span.end <= now:
            last_end = span.end if last_end is None else max(last_end, span.end)
        elif span.t <= now:
            active = span
        elif next_start is None:
            next_start = span.t
        if span.t > latest:
            break
        if span.end < earliest:
            continue
        start, end = position(span.t), position(span.end)
        left, right = max(start, track.left), min(end, track.right - 1)
        if left <= right:
            ribbon = pygame.Rect(left, cy - 4, right - left + 1, 9)
            pygame.draw.rect(surf, ink, ribbon)
            surf.fill(mix(field, ink, .52), (left, cy + 2, ribbon.w, 3))
            elapsed = min(right + 1, cursor) - left
            if elapsed > 0:
                surf.fill(palette.active, (left, ribbon.y, elapsed, ribbon.h))
        if start >= track.left - 7:
            _marker(surf, start, cy, True, ink, field, palette.radius)
        if end < track.right + 7:
            _marker(surf, end, cy, False, ink, field, palette.radius)

    # Keep the center of the gate open so both edge symbols survive the crossing.
    pygame.draw.polygon(surf, palette.text, [(cursor - 4, cy - 13), (cursor + 4, cy - 13), (cursor, cy - 8)])
    pygame.draw.polygon(surf, palette.text, [(cursor - 4, cy + 13), (cursor + 4, cy + 13), (cursor, cy + 8)])
    return active, next_start, last_end


def _forecast(action, beats):
    halves = math.floor(beats * 2 + .5)
    if halves == 0:
        return f"곧 {action}"
    if halves == 1:
        return f"반 박 후 {action}"
    count = f"{halves // 2}박" + (" 반" if halves % 2 else "")
    return f"{count} 후 {action}"


def _cue(active, next_start, last_end, now, beat):
    if active is not None:
        attack = now - active.t < min(beat / 3, (active.end - active.t) / 2)
        return ("지금 밟기" if attack else "계속 유지",
                _forecast("떼기", (active.end - now) / beat))
    if last_end is not None and now - last_end < beat / 3:
        action = "지금 떼기"
    elif next_start is not None and next_start - now <= beat:
        action = "밟기 준비"
    else:
        action = "떼고 대기"
    return action, _forecast("밟기", (next_start - now) / beat) if next_start is not None else "다음 구간 없음"


def draw_pedal_lane(surf, text, rect, spans, now, pressed, feedback=None, *, beat_ms=333, pixel=True):
    """Draw the chart targets on the song clock, alongside the live pedal switch."""
    box = pygame.Rect(rect)
    previous_clip = surf.get_clip()
    visible = box.clip(previous_clip)
    if not visible or box.w < 100 or box.h < 32:
        return
    beat = max(1., beat_ms)
    palette = D.CONSOLE if pixel else _ROOFTOP
    strike = D.HOT if pixel else D.ORANGE
    track = pygame.Rect(box.x + round(box.w * .14), box.y + 3, round(box.w * .58), box.h - 6)
    cue_x = track.right + 13
    result_x = box.x + round(box.w * .87)
    heading_y, value_y = box.centery - 12, box.centery + 8

    def label(value, x, cy, width, size, color, role="sans_bold"):
        glyph = text.fit(role, size, value, color, max(1, width))
        surf.blit(glyph, glyph.get_rect(midleft=(x, cy)))

    surf.set_clip(visible)
    try:
        surf.fill(palette.panel, box)
        surf.fill(palette.line, (box.x, box.y, box.w, 2))
        input_ink = strike if pressed else palette.muted
        _pedal(surf, box.x + 10, box.centery + 1, pressed, input_ink, palette.line)
        input_x = box.x + 54
        label("페달 입력", input_x, heading_y, track.x - input_x - 5, 14, palette.muted)
        label("밟음" if pressed else "뗌", input_x, value_y, track.x - input_x - 5, 22, input_ink)

        surf.set_clip(visible.clip(track))
        active, next_start, last_end = _timeline(surf, text, track, spans, now, beat, palette)
        surf.set_clip(visible)
        action, forecast = _cue(active, next_start, last_end, now, beat)
        cue_width = result_x - cue_x - 10
        label(forecast, cue_x, heading_y, cue_width, 14, palette.muted)
        label(action, cue_x, value_y, cue_width, 22, palette.accent if active is not None else palette.text)

        surf.fill(palette.line, (result_x, box.y + 9, 1, box.h - 18))
        x = result_x + 12
        width = box.right - x - 8
        if feedback and 0 <= now - feedback[0] < min(1000, max(550, beat * 2)):
            _, part, grade = feedback
            label("밟기 판정" if part == "pedal_down" else "떼기 판정", x, heading_y, width, 14, palette.muted)
            color = {"PERFECT": palette.accent, "GOOD": palette.muted, "MISS": strike}.get(grade, palette.text)
            label(grade, x, value_y, width, 25, color, "num")
        else:
            for down, word, cy in ((True, "밟기", heading_y + 2), (False, "떼기", value_y + 1)):
                _marker(surf, x + 7, cy, down, palette.accent, palette.background, palette.radius)
                label(word, x + 22, cy, width - 22, 15, palette.muted)
    finally:
        surf.set_clip(previous_clip)
