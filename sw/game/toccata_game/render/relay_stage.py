"""Song-clock lighting and audience for the relay's rooftop note field."""

from __future__ import annotations

import math
from random import Random

import pygame


# Paint at two screen pixels per dot in the usual 610 x 386 field. The set ends
# above the landing effects. Its last rows dissolve back into the lane guides.
_WIDTH, _FIELD_HEIGHT, _HEIGHT = 305, 193, 165
_SIZE = (_WIDTH, _HEIGHT)
_PIVOTS = ((17, 12), (287, 12))
_FOCUS_Y = 112
_GOLD = (255, 197, 87)
_DUETS = (
    ((79, 204, 206), (230, 118, 173)),
    ((119, 142, 248), (248, 144, 114)),
    ((97, 224, 169), (204, 123, 238)),
    ((76, 195, 248), (251, 107, 163)),
)


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _ease(start, end, t):
    t = min(1., max(0., (t - start) / (end - start)))
    return t * t * (3 - 2 * t)


def _star(surf, x, y, radius, ink):
    if radius == 1:
        surf.set_at((x, y), ink)
        return
    pygame.draw.polygon(surf, ink, [(x, y-radius), (x+1, y-1), (x+radius, y),
                                     (x+1, y+1), (x, y+radius), (x-1, y+1),
                                     (x-radius, y), (x-1, y-1)])


class StageLights:
    def __init__(self, *, pixel: bool):
        self.pixel = pixel
        self.night = (13, 20, 38) if pixel else (39, 32, 58)
        self.dusk = (49, 61, 89) if pixel else (103, 70, 96)
        self.shadow = (12, 19, 33) if pixel else (32, 26, 45)
        self.rim = (64, 91, 111) if pixel else (111, 83, 110)
        self._backdrop = self._city()
        self._frame = pygame.Surface(_SIZE, pygame.SRCALPHA)
        self._light = pygame.Surface(_SIZE, depth=32)
        self._mask = self._lane_mask()
        self._scaled = None
        self._last_pose = None

        # Shuffled admission times fill scattered seats, rather than building a
        # single row from left to right. The rightmost spectator leads the wave last.
        rng = Random(409)
        self._rows = []
        for row, spacing in enumerate((12, 16)):
            seats = []
            for i, x in enumerate(range(4 + row * 5, _WIDTH, spacing)):
                x += rng.randint(-2, 2)
                edge = abs(x - 152) / 152
                floor = 147 + row * 11 - round(edge * (9 - row * 3))
                admission = 0 if edge > .55 and i % 5 == row else rng.randint(1, 90)
                seats.append((x, floor, admission, rng.randrange(4), rng.random()))
            self._rows.append(seats)

    def _city(self):
        sky = pygame.Surface(_SIZE, depth=32)
        for y in range(_HEIGHT):
            ink = _mix(self.night, self.dusk, _ease(18, 150, y))
            pygame.draw.line(sky, ink, (0, y), (_WIDTH, y))
        rng = Random(118)
        for _ in range(32):
            x, y = rng.randrange(_WIDTH), rng.randrange(4, 92)
            sky.set_at((x, y), _mix(self.night, self.rim, rng.uniform(.4, .85)))

        # A sliced poster moon, a water tower and a broadcast spire break the
        # building silhouettes even when all the concert lamps are sleeping.
        moon = (85, 103, 124) if self.pixel else (172, 121, 133)
        for y in range(-11, 12):
            if y not in (3, 7, 8, 10):
                dx = math.isqrt(121 - y*y)
                pygame.draw.line(sky, moon, (250-dx, 40+y), (250+dx, 40+y))
        for layer in range(2):
            wall = _mix(self.dusk, self.shadow, .36 + layer * .32)
            glint = _mix(wall, self.rim, .64)
            amber = _mix(wall, (199, 140, 98), .37)
            x = -3
            while x < _WIDTH:
                width = rng.randint(9, 24) + 4 * layer
                edge = abs(x + width/2 - 152) / 152
                roof = 115 + layer*14 - round(21*edge) + rng.randrange(-9, 9)
                sky.fill(wall, (x, roof, width-1, _HEIGHT-roof))
                sky.fill(wall, (x+3, roof-3, max(3, width//3), 4))
                for wy in range(roof+5, roof+24, 5):
                    for wx in range(x+3, x+width-2, 5):
                        if rng.randrange(4) == 0:
                            sky.fill(amber if wx % 3 == 0 else glint, (wx, wy, 2+layer, 1))
                x += width
            if layer == 0:
                for foot in (34, 42):
                    pygame.draw.line(sky, wall, (foot, 83), (foot-1, 101), 2)
                pygame.draw.polygon(sky, wall, [(29, 78), (38, 73), (47, 78),
                                                (45, 79), (44, 88), (32, 88), (31, 79)])
                pygame.draw.line(sky, glint, (31, 78), (44, 78))
                pygame.draw.lines(sky, wall, False, [(258, 104), (265, 67), (272, 104)], 2)
                for ry in (80, 87, 94):
                    span = (ry - 67) // 5
                    pygame.draw.line(sky, wall, (265-span, ry+4), (265+span, ry))
                sky.fill(moon, (265, 66, 1, 2))

        for x, _ in _PIVOTS:
            # Short sections of box truss project from the top corners.
            outside = -1 if x < 152 else 1
            end = x - outside * 12
            pygame.draw.line(sky, self.rim, (x+outside*19, 2), (end, 2), 2)
            pygame.draw.line(sky, self.rim, (x+outside*19, 7), (end, 7))
            for offset in (-10, -2, 6, 14):
                near = x + outside*offset
                pygame.draw.line(sky, self.rim, (near, 7), (near+outside*5, 2))
            sky.fill(self.shadow, (x-2, 6, 5, 7))
        return sky

    @staticmethod
    def _lane_mask():
        mask = pygame.Surface(_SIZE, pygame.SRCALPHA)
        for x in range(_WIDTH):
            edge = abs(x - 152) / 152
            opacity = 125 + round(118 * _ease(.12, .91, edge))
            pygame.draw.line(mask, (255, 255, 255, opacity), (x, 0), (x, 148))
            for y in range(149, _HEIGHT):
                alpha = round(opacity * (1 - _ease(148, _HEIGHT-1, y)))
                mask.set_at((x, y), (255, 255, 255, alpha))
        return mask

    def _cone(self, pivot, target, spread, color, power):
        # Concentric quads feather the shaft. Add each beam separately so the
        # overlap naturally gets brighter as the two operators find each other.
        x, y = pivot
        light = self._light
        light.fill((0, 0, 0))
        for band in range(10):
            width = spread * (1 - band / 11)
            ink = _mix((0, 0, 0), color, power * (.035 + .55 * (band / 9) ** 1.2))
            pygame.draw.polygon(light, ink, [(x-2, y), (x+2, y),
                                            (target+width, _FOCUS_Y), (target-width, _FOCUS_Y)])
            pygame.draw.ellipse(light, ink, (target-width, _FOCUS_Y-2, 2*width, 5))
        self._frame.blit(light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _lamp(self, pivot, target, color, power):
        x, y = pivot
        length = math.hypot(target-x, _FOCUS_Y-y)
        dx, dy = (target-x)/length, (_FOCUS_Y-y)/length

        def point(forward, sideways):
            return (round(x + dx*forward + dy*sideways), round(y + dy*forward - dx*sideways))

        pygame.draw.polygon(self._frame, self.shadow, [point(-4, -3), point(-4, 3),
                                                       point(5, 5), point(5, -5)])
        pygame.draw.line(self._frame, self.rim, point(-3, -3), point(4, -5), 2)
        pygame.draw.line(self._frame, _mix(self.rim, color, .35 + .63*power),
                         point(5, -4), point(5, 4), 2)

    def _audience(self, beat, combo, hit, colors, encore, gold):
        frame = self._frame
        cheer = min(1., combo/38)
        for row, seats in enumerate(self._rows):
            ink = _mix(self.shadow, self.rim, .30 if row == 0 else .08)
            for x, floor, admission, style, offset in seats:
                if combo < admission:
                    continue
                # A crest moves from house left to house right during the finale.
                crest = max(0., 1 - abs(encore - (.34 + .48*x/_WIDTH)) / .14)
                sway = math.sin(math.tau * (beat/2 + offset))
                bounce = round(cheer * (1 + sway) + crest * 5)
                head = floor - 7 - row*3 - bounce
                # Bobs, caps and headphones give the bank an irregular contour.
                pygame.draw.circle(frame, ink, (x, head), 2+row)
                if style == 0:
                    frame.fill(ink, (x-3-row, head-1, 5, 1))
                elif style == 1:
                    pygame.draw.circle(frame, ink, (x+2, head-2), 2)
                pygame.draw.polygon(frame, ink, [(x-2, head+2), (x+2, head+2),
                                                (x+4+row, head+5), (x+5+row, floor+1),
                                                (x-5-row, floor+1), (x-4-row, head+5)])
                side = -1 if style % 2 else 1
                hand_x = x + side * (4+row) + round(2*sway*cheer)
                hand_y = head + 3 - round(cheer*3 + crest*4)
                pygame.draw.line(frame, ink, (x+side*2, head+5), (hand_x, hand_y), 2)
                tip = (hand_x + round(sway*(1+cheer*2)), hand_y - 2 - row - round(cheer*2))
                dye = _mix(colors[style % 2], _GOLD, max(gold*.52, crest))
                glow = .19 + cheer*(.22 + .13*(1+sway)) + hit*.10 + crest*.20
                stick = _mix(ink, dye, min(1., glow))
                pygame.draw.line(frame, stick, (hand_x, hand_y), tip, 1+row)
                if row:
                    reflection = _mix(ink, stick, .45)
                    pygame.draw.line(frame, reflection, (x+side, head-3), (x+side*2, head-2))
                    pygame.draw.line(frame, reflection, (x+side*2, head+3), (x+side*3, head+4))
            # Foreshortened parapets anchor each row without a second landing rule.
            lip = 147 + row * 11
            for left, mid, end in ((-1, 50, 135), (305, 247, 169)):
                rim = [(left, lip-9+row*3), (mid, lip-6+row*2), (end, lip)]
                pygame.draw.polygon(frame, self.shadow, [*rim, (end, _HEIGHT), (left, _HEIGHT)])
                pygame.draw.lines(frame, _mix(self.shadow, self.rim, .43), False, rim)

    def _sparkles(self, phase):
        # A brief pool of light and a hot core at unison, then a fan of embers.
        age = (phase - .56) / .40
        if not 0 < age < 1:
            return
        light = self._light
        light.fill((0, 0, 0))
        x, y = _WIDTH//2, _FOCUS_Y
        flash = _ease(0, .12, age) * (1 - _ease(.19, .71, age))
        if flash:
            radius = 2 + round(15*age)
            haze = _mix((0, 0, 0), _GOLD, .24*flash)
            pygame.draw.ellipse(light, haze, (x-2*radius, y-3, 4*radius+1, 7))
            _star(light, x, y, 1 + round(7*flash), _mix((0, 0, 0), _GOLD, flash))
        for i in range(14):
            t = (age - (i % 4)*.06) / .82
            if 0 < t < 1:
                side = -1 if i % 2 else 1
                reach = (10 + i*4) * t
                lift = (26 + i*7 % 39)*t - 24*t*t
                twinkle = math.sin(math.pi*t)
                _star(light, round(x + side*reach), round(y-lift), 1 + round(2*twinkle),
                      _mix((0, 0, 0), _GOLD, twinkle * .85))
        self._frame.blit(light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, surf: pygame.Surface, rect: pygame.Rect, *, beat: float, combo: int,
             hit: float, encore: float) -> None:
        """Paint inside the caller's clip. Encore is normalized over its 1.5 s cue."""
        box = pygame.Rect(rect)
        if box.w < 1 or box.h < 1 or not box.colliderect(surf.get_clip()):
            return
        if beat < 0:
            combo, encore = 0, -1.
        if combo <= 0 and encore < 0:
            beat, hit = 0., 0.
        combo = max(0, combo)
        hit = min(1., max(0., hit))
        size = (box.w, max(1, round(box.h * _HEIGHT / _FIELD_HEIGHT)))
        pose = (size, beat, combo, hit, encore)
        if pose == self._last_pose:
            surf.blit(self._scaled, box.topleft)
            return
        level = math.sqrt(min(1., combo / 100))
        pulse = (1 - beat % 1) ** 2
        gold = _ease(0, .17, encore) * (1 - _ease(.79, 1, encore))
        tier = sum(combo >= threshold for threshold in (10, 30, 60))
        colors = _DUETS[tier]
        # Trade gel colors on alternating bars, easing through the downbeat.
        bar = math.floor(beat / 4)
        exchange = _ease(0, .5, beat % 4)
        swap = (exchange if bar % 2 else 1-exchange) * (.4 if combo else 0)
        colors = (_mix(colors[0], colors[1], swap), _mix(colors[1], colors[0], swap))
        self._frame.blit(self._backdrop, (0, 0))
        lamps = []
        for side, pivot in enumerate(_PIVOTS):
            swing = math.sin(math.tau * (beat/8 + side*.19))
            aim = 43 + level*41 + (7 + 21*level)*swing
            # Cross high, hold the X, then bring both footprints to one spot.
            crossing = _ease(.03, .36, encore)
            unison = _ease(.42, .62, encore)
            show_aim = aim + (238 - aim)*crossing
            show_aim += (152 - show_aim)*unison
            aim += (show_aim - aim) * (1 - _ease(.82, 1, encore))
            target = _WIDTH-1-aim if side else aim
            color = _mix(colors[side], _GOLD, gold)
            power = min(1., .18 + level*.42 + min(1., combo/10)*(.13*pulse + .12*hit) + .55*gold)
            self._cone(pivot, target, 10 + level*11 + gold*6, color, power)
            lamps.append((pivot, target, color, power))
        self._sparkles(encore)
        for lamp in lamps:
            self._lamp(*lamp)
        self._audience(beat, max(combo, 100*gold), hit, colors, encore, gold)
        self._frame.blit(self._mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if self._scaled is None or self._scaled.get_size() != size:
            self._scaled = pygame.Surface(size, pygame.SRCALPHA)
        scale = pygame.transform.scale if self.pixel else pygame.transform.smoothscale
        scale(self._frame, size, self._scaled)
        self._last_pose = pose
        surf.blit(self._scaled, box.topleft)
