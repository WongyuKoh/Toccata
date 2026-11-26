"""건반마다 악보에 적힌 잔향과 손에서 페달로 넘어간 실제 울림을 그린다."""
from math import sin, tau

import pygame

from .theme import SOLFEGE


_BRASS = (193, 151, 88)
_GOLD = (255, 201, 96)
_LIGHT = (255, 240, 187)
_SHADOW = (70, 50, 43)
_BROKEN = (244, 157, 151)
_STRIP = (22, 30, 48)
_WHITE = (243, 244, 240)


def _bracket(surf, x, y):
    # The tips meet the top of a guided head. Unguided heads leave a small gap.
    points = [(x-18, y-27), (x-18, y-32), (x-5, y-32), (x, y-36),
              (x+5, y-32), (x+18, y-32), (x+18, y-27)]
    pygame.draw.lines(surf, _SHADOW, False, points, 4)
    pygame.draw.lines(surf, _GOLD, False, points, 2)


def _damper(surf, x, y, color):
    # The wide bar marks the exact time. The two shorter bars remain visible
    # below the head and its shadow if this pitch strikes again right at the end.
    pygame.draw.line(surf, _SHADOW, (x-13, y), (x+13, y), 4)
    pygame.draw.line(surf, color, (x-12, y), (x+12, y), 2)
    pygame.draw.line(surf, color, (x-8, y+5), (x+8, y+5), 2)
    pygame.draw.line(surf, color, (x-4, y+9), (x+4, y+9), 2)


def _sounding(surf, x, top, floor, attack_y, now, carried):
    # The planned span falls. Its brighter, sounding section grows out of the key.
    tip = max(top, floor - 9 - max(0, attack_y - floor))
    ink = _LIGHT if carried else _GOLD
    pygame.draw.line(surf, _SHADOW, (x, tip), (x, floor), 5)
    pygame.draw.line(surf, ink, (x, tip), (x, floor), 3 if carried else 2)
    if not carried:
        pygame.draw.circle(surf, ink, (x, floor-4), 4, 1)
        return

    # Glints travel up each carried string. No animation clock runs during a pause.
    phase = now / 420
    for y in range(floor - int(phase * 32) % 32, tip + 2, -32):
        pygame.draw.line(surf, _GOLD, (x-3, y), (x+3, y), 2)
    height = round(3 * sin(phase * tau))
    y = floor - 5
    wave = [(x-14, y), (x-7, y-height), (x, y), (x+7, y+height), (x+14, y)]
    pygame.draw.lines(surf, _GOLD, False, wave, 2)


def draw_resonance_trails(surf, text, layout, field, groups, now, y_of, judge):
    """Draw after chord connectors and before note heads, on the caller's song clock."""
    field = pygame.Rect(field)
    original = surf.get_clip()
    visible = original.clip(field)
    if not visible:
        return
    floor = field.bottom - 1
    surf.set_clip(visible)
    try:
        for group in groups:
            head = round(y_of(group.t, now))
            if head < field.top:
                break
            end = round(y_of(group.end, now))
            if end - 6 >= visible.bottom and now <= group.end:
                continue
            for key in group.keys:
                pitch_x = layout.x(key)
                if pitch_x is None:
                    continue
                x = round(pitch_x)
                if x + 20 < visible.left or x - 20 >= visible.right:
                    continue
                state = judge.resonance_state(group.idx, key)
                live = state in ("finger", "carried")
                if now > group.end and not live:
                    continue
                if state in ("broken", "cleared"):
                    if state == "broken":
                        pygame.draw.line(surf, _BROKEN, (x-5, floor-9), (x+5, floor-2), 2)
                        pygame.draw.line(surf, _BROKEN, (x+5, floor-9), (x-5, floor-2), 2)
                    continue

                cap = min(end, floor)
                top = max(cap, field.top)
                bottom = floor if live else min(head - 35, floor)
                if bottom > top:
                    pygame.draw.line(surf, _BRASS, (x, top), (x, bottom))
                if live:
                    _sounding(surf, x, top, floor, head, now, state == "carried")
                else:
                    _bracket(surf, x, head)
                if visible.top - 10 <= cap < visible.bottom + 2:
                    _damper(surf, x, cap, _LIGHT if live else _GOLD)
    finally:
        surf.set_clip(original)


def _cue(groups, now, judge):
    """Keep the remaining finger or missing pitch actionable within a partly played chord."""
    for group in groups:
        states = {key: judge.resonance_state(group.idx, key) for key in group.keys}
        for phase in ("waiting", "finger", "carried"):
            keys = [key for key in group.keys if states[key] == phase]
            if not keys or (phase == "waiting" and now > group.end):
                continue
            if phase == "waiting":
                title = "다음 울림" if now < group.t else "지금 칠 음"
                action = "금빛 괄호 음을 치고, 페달을 밟은 뒤 손을 떼세요"
            elif phase == "finger":
                title = "손으로 누르는 음"
                action = "페달을 밟고, 음 길이에 맞춰 손을 떼세요"
            else:
                title = "페달로 울리는 음"
                action = "다음 화음 전에, 겹선이 판정선에 닿으면 페달을 떼세요"
            return title, keys, action
        if "broken" in states.values() and group.t <= now < group.end:
            return "울림 끊김", group.keys, judge.resonance_reason(group.idx)
    return None


def _pitch_names(keys):
    return " · ".join(SOLFEGE[key % 12].replace("♯", "#") for key in keys)


def draw_resonance_guidance(surf, text, rect, groups, now, judge, feedback):
    """Replace the left voicing legend in its existing strip and preserve the dynamics results."""
    box = pygame.Rect(rect)
    original = surf.get_clip()
    visible = original.clip(box)
    if not groups or not visible or box.w < 20 or box.h < 20:
        return
    cue = _cue(groups, now, judge)
    result = ""
    result_ink = _LIGHT
    if feedback and 0 <= now - feedback[0] < 1450:
        _, idx, grade = feedback
        pitches = next((_pitch_names(g.keys) for g in groups if g.idx == idx), "")
        if grade == "MISS":
            detail = judge.resonance_reason(idx)
            result_ink = _BROKEN
        else:
            detail = "울림 정리"
        result = f"{pitches}  {grade}  {detail}".strip()

    surf.set_clip(visible)
    try:
        surf.fill(_STRIP, box)
        if cue is None and not result:
            return
        x = box.left + 9
        width = box.w - 18
        y = box.top + box.h // 4
        if cue:
            title, keys, action = cue
            heading = f"{title}   {_pitch_names(keys)}"
            label = text.fit("sans_bold", 18, heading, _GOLD, width // 2 if result else width)
            surf.blit(label, label.get_rect(midleft=(x, y)))
            line = text.fit("sans_bold", 21, action, _WHITE, width)
            surf.blit(line, line.get_rect(midleft=(x, box.top + box.h * 3 // 4)))
        if result:
            room = width - label.get_width() - 12 if cue else width
            word = text.fit("sans_bold", 17, result, result_ink, max(1, room))
            anchor = {"midright": (box.right - 9, y)} if cue else {"midleft": (x, box.centery)}
            surf.blit(word, word.get_rect(**anchor))
    finally:
        surf.set_clip(original)
