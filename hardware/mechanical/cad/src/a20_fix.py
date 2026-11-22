"""A20 (2026-11-22) fixes after the user's one-octave test assembly (on top of A18 / A19).

The user's list (2026-11-22):
  - '홀센서 구멍 크게, 기둥을 뒤쪽도 끼울 수 있게(옆으로 넣는 식)'
  - '기판쪽 관에 구멍 꽂는 곳 구멍이 제대로 안나옴'
  - '홀센서 쪽 기판 공간을 넓히고, 메인 기판처럼 밑에 뚫고 높이를 키우기'
  - '모델링은 6개 구멍이 나오지만, 실제 크기를 보면 3~4개밖에 공간이 안나옴'
  - '무게 추 끼우는 게 사이즈가 안맞음 조정 필요'
What A20 changes:
  1-2 sensor bar (센서 바): every hall-sensor pocket is 0.25 bigger on each side (3.55 x 4.4 -> 4.05 x 4.9, the body is
      3.15 x 4.0). The three D0.9 lead holes (3.6 long 'tubes' a 0.4 nozzle does not print) become one 1.6-wide slot per
      sensor, and the pocket, the lead groove and the slot all run out through the bar's rear edge (y77.5): the sensor's
      legs can still be dropped in from the top, or the sensors are soldered to the board first and the bar is slid on
      from behind (legs through the slots, bodies along the pocket channels) until the slot ends stop on the front legs.
  3-4 sensor board (센서 기판 SB / EL / ER): the two support ribs under the board (front y61.0..62.8, rear y73.2..75.5)
      covered rows 1 and 6 of the 6-row board and left 2.0 (z5..7) over the floor, so only the 3-4 middle rows were usable
      from below. A20 removes the ribs and cuts the floor away under the board (as A18 did for the control board): the
      underside has z3 (EVA top) .. z7.0 = 4.0 everywhere except over 4.0-wide floor bridges (module 3; EL / ER none), and the
      board sits on the left post (unchanged, M3x10) + 3.5-long pads under the unused edge rows (y61.92 / y74.62) at the
      right end and on each bridge. All 6 rows are open along the whole board apart from those pads (2 holes per pad).
      (Cutting the same window out of the 3 mm EVA sheet under the module gives 7.0, if more is ever needed.)
  5   steel weight (무게 추, SS400 9 x 19 x 40) pocket in the lever carrier: the pocket was 40.0 x 19.0 x 9.2 with crush ribs
      to 39.6 (rear) and 9.03 (cover) - zero room in z and 0.1..0.3 interference in y for the specified 39.7..39.9 cut,
      so a real hot-rolled bar (9 +-0.25, 19 +-0.5, sawn length) did not go in. A20: pocket 40.5 (y150.0..190.5) x 19.5
      (z32.75..52.25) x 9.4 (walls 0.69 -> 0.59), ribs 0.3 at the rear (to 40.2) and 0.17 on the cover (to 9.23): a bar
      up to 40.2 x 19.5 x 9.23 slides in, up to 40.5 x 9.4 crushes the ribs; the MS polymer fills the rest.
      A 15-min coupon (무게추칸 시험편) checks the bar before the carriers are printed again.
  7   snap joints ('탈착이 너무 쉽게 되는게 아닌지 테스트', estimate for PLA): the lever cover came off at 3~4 N (hooks 0.4,
      both faces 45 deg) -> hooks 0.5 deep with a 60 deg return face (~10~16 N; the MS polymer is still what holds it while
      playing). The cage legs never pulled out (flat 90 deg catch) but the fin-leg catch could crush under a hard up-stop
      hit (~31 N each vs 45~70 N) -> barb 0.8, flex room 0.8, recess to z4.0, fin legs 1.4 thick and 5.0 long (~62 N each).
      The balance rail already holds (84~106 N for 4 lips) and is left as A18.
"""
from cadlib import box, diff, prism_z

A20_ON = True
A20 = {
    # sensor bar
    "pocket_grow": 0.25, "slot_w": 1.6, "groove_past": 0.9, "slot_y0": 63.9, "rear_out": 78.5,
    # sensor board support
    "sb_inset": 0.2, "pad_len": 3.5, "pad_depth": 2.0, "bridge_w": 4.0,
    "bridges": {"module": (32.4, 88.3, 141.6), "left": (), "right": ()},   # EL / ER: short; EL leads run back over x15..38
    # steel pocket (lever carrier, lever angle 0): walls 0.1 thinner, rear face +0.5, z +-0.25 around the 9 x 19 x 40 steel
    # (lever C: x3.82..13.22, y150.0..190.5, z32.75..52.25)
    "wall_thin": 0.1, "rear_add": 0.5, "z_add": 0.25,
    "rib_rear": 0.3, "rib_cover": 0.17,
    # 7 snap joints ('탈착이 너무 쉽게 되는게 아닌지 테스트'; PLA E3.5 GPa cantilever estimate, child analysis 2026-11-22)
    # lever cover hooks: 0.4 deep, both faces 45 deg -> 3~4 N to pull off; now 0.5 deep, return face 60 deg -> ~10~16 N
    "hook_h": 0.5, "hook_return_deg": 60.0,
    # cage snap legs: catch 0.35 -> 0.65 (barb 0.8, flex room 0.8, recess to z4.0); fin legs 1.4 thick, 5 long in y
    "barb": 0.8, "leg_room": 0.8, "barb_z": (3.0, 4.0), "fin_clip_y": (178.5, 183.5), "fin_leg_t": 1.4,
}


def sb_bar_cuts(pocket_x, pocket_y, zf, lead_x):
    """cuts of one A20 sensor position in the sensor bar: bigger pocket, lead groove and one lead slot, all open to the rear."""
    g, ry = A20["pocket_grow"], A20["rear_out"]
    px0, px1 = pocket_x[0] - g, pocket_x[1] + g
    py0 = pocket_y[0] - g
    hw = A20["slot_w"] / 2.0
    y0 = A20["slot_y0"]
    return [box(px0, px1, py0, ry, zf, 14.5),                                   # pocket channel
            box(px1 - 0.01, lead_x + A20["groove_past"], y0, ry, zf, 14.5),    # lead groove (floor = pocket floor)
            box(lead_x - hw, lead_x + hw, y0, ry, 8.0, zf + 0.01)]              # lead slot through the bar


def sb_bed(board, post_x1, bridges, z_floor=(3.0, 5.0), z_board=7.0):
    """(adds, cuts) of the bed under one sensor board: pads on the unused edge rows (right end + each bridge) and a floor
    window down to the EVA everywhere else under the board. board = (x0, x1, y0, y1)."""
    bx0, bx1, by0, by1 = board
    e, L, D, W = A20["sb_inset"], A20["pad_len"], A20["pad_depth"], A20["bridge_w"]
    fz0, fz1 = z_floor
    spans = [(bx1 - e - L, bx1 - e)] + [(xc - L / 2.0, xc + L / 2.0) for xc in bridges]
    adds = []
    for (a, b) in spans:
        adds.append(box(a, b, by0 + e, by0 + e + D, fz1 - 0.01, z_board))
        adds.append(box(a, b, by1 - e - D, by1 - e, fz1 - 0.01, z_board))
    win = box(post_x1 + e, bx1 - e, by0 + e, by1 - e, fz0 - 0.1, fz1 + 0.1)
    keep = [box(xc - W / 2.0, xc + W / 2.0, by0 - 1.0, by1 + 1.0, fz0 - 0.2, fz1 + 0.2) for xc in bridges]
    a = bx1 - e - L - 0.3
    keep += [box(a, bx1 + 1.0, by0 - 1.0, by0 + e + D + 0.3, fz0 - 0.2, fz1 + 0.2),
             box(a, bx1 + 1.0, by1 - e - D - 0.3, by1 + 1.0, fz0 - 0.2, fz1 + 0.2)]
    return adds, [diff(win, keep)]


def steel_pocket(pk):
    """the A20 steel pocket envelope pk = (x0, x1, y0, y1, z0, z1), cut from the carrier body and the cover (the crush ribs
    are added after it). keyaction.a20_pocket(parts) gives it for each lever (walls 0.1 thinner, rear face +0.5, z +-0.25)."""
    return box(*pk)


def body_ribs(pk, rib_z, rib_w):
    """2 crush ribs on the pocket's rear face (A20: face y190.5, ribs 0.3 -> 40.2), 45 deg lead-in at the open (+x) end."""
    x0, x1, _y0, yb, _z0, _z1 = pk
    r, w = A20["rib_rear"], rib_w / 2.0
    xe = x1 - 0.9
    poly = [(x0 - 0.01, yb + 0.01), (x0 - 0.01, yb - r), (xe, yb - r), (xe + r + 0.01, yb + 0.01)]
    return [prism_z(poly, zc - w, zc + w) for zc in rib_z]


def cover_ribs(pk, rib_z, rib_w, rib_y):
    """crush ribs on the cover's inner face (A20: face 0.1 further out, ribs 0.17 -> 9.23)."""
    x1 = pk[1]
    w = rib_w / 2.0
    return [box(x1 - A20["rib_cover"], x1 + 0.01, rib_y[0], rib_y[1], zc - w, zc + w) for zc in rib_z]
