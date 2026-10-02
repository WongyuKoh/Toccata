#!/usr/bin/env python3
"""Toccata v4 key action "W1+" (round 4: fix + SIMPLIFY) - single-source model.

Short seesaw key on a D4 SUS304 rod through a cloth-lined SNAP notch (wraps below the rod equator, lip clearance
at rest) and x-located by a D2 balance pin; the rod lies on printed cradles between the balance blocks.  The hidden
tail's M3 capstan lifts a weighted lever (SS400 flat bar 9T x 19 cut to 40, snapped into a printed carrier with
hub collars) hung on a plain D4 SUS304 cold-drawn rod through the 5 fins (no bushings, no hardened shaft); a
preloaded torsion spring (d0.5 SUS, coil in the hub, long leg in a groove of the rear wall) adds return torque.
r4 up-stop: the exposed steel top of each lever stops on a flat low-rebound pad (microcellular urethane + 1T felt
face) glued under a printed PAD BAR; one pad bar per fin bay slides into the frame's printed TOP PLATE (the r3
bridge extended forward to y146 = 'ledge').  The pad force is carried in compression into the frame: no steel rail,
no screws, no disc springs, no tapped strips, no pins, no magnets, no driver, no re-tightening.  The dust cover is
one loose curtain strip hooked over the front edge of the top plate.  Black keys carry no lead.

Units: mm, g, N, ms  (1 g*mm/ms^2 = 1 N; torque N*mm; inertia g*mm^2; mm/ms = m/s).
z = 0 desk, y = 0 white key front lip (+y away from the player), x = 0 C left nominal boundary.
Key angle a > 0: key front DOWN (CCW in the (y,z) plane about the key rod K).
Lever angle b > 0: steel UP (CW in the (y,z) plane about the lever rod L).

Every number that drawings or DESIGN.md cite is produced here and exported to geometry.json /
metrics.json / parts_list.json (see run_all.py).  Nothing downstream may hand-type a dimension.
"""
import math
import numpy as np

G = 9.80665e-3            # N per g
RHO_PETG = 1.25e-3        # g/mm^3 (Bambu PETG Basic)
RHO_ST = 7.85e-3          # SS400
RHO_SUS = 7.93e-3         # SUS304
RHO_FELT = 0.35e-3        # dense wool felt
RHO_MAG = 7.5e-3          # N35 NdFeB
E_PETG = 1950.0           # MPa flexural
E_ST = 200000.0
E_SUS = 193000.0
TOL = 0.3                 # FDM +-0.3 applied to every clearance (nominal - 0.3 >= 1.0)
CLEAR_MIN = 1.0


# ============================================================================ small geometry helpers
def rot(p, c, a):
    """rotate point p=(y,z) about c by angle a (CCW, rad)."""
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def arc(c, r, a0, a1, n=12):
    """points of a circular arc (angles in degrees, CCW from +y)."""
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def circle(c, r, n=24):
    return arc(c, r, 0, 360, n)[:-1]


def rect(y0, y1, z0, z1):
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def seg_dist(p, q, a, b):
    """distance between segments pq and ab (2D)."""
    def pt_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    if seg_cross(p, q, a, b):
        return 0.0
    return min(pt_seg(p, a, b), pt_seg(q, a, b), pt_seg(a, p, q), pt_seg(b, p, q))


def seg_cross(p, q, a, b):
    def orient(u, v, w):
        return (v[0] - u[0]) * (w[1] - u[1]) - (v[1] - u[1]) * (w[0] - u[0])
    d1, d2 = orient(a, b, p), orient(a, b, q)
    d3, d4 = orient(p, q, a), orient(p, q, b)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                c = not c
    return c


def poly_dist(A, B):
    """signed distance between two simple polygons: >0 gap, <0 overlap (depth estimate)."""
    edgesA = [(A[i], A[(i + 1) % len(A)]) for i in range(len(A))]
    edgesB = [(B[i], B[(i + 1) % len(B)]) for i in range(len(B))]
    dmin = 1e9
    for p, q in edgesA:
        for a, b in edgesB:
            d = seg_dist(p, q, a, b)
            if d < dmin:
                dmin = d
    depth = 0.0
    hit = dmin == 0.0
    for P_, Q_, E_ in ((A, B, edgesB), (B, A, edgesA)):
        for p in P_:
            if inside(p, Q_):
                hit = True
                dd = min(seg_dist(p, p, a, b) for a, b in E_)
                depth = max(depth, dd)
    if hit:
        return -max(depth, 0.01)
    return dmin


def poly_area_centroid(poly):
    A = cy = cz = 0.0
    n = len(poly)
    for i in range(n):
        y0, z0 = poly[i]
        y1, z1 = poly[(i + 1) % n]
        c = y0 * z1 - y1 * z0
        A += c
        cy += (y0 + y1) * c
        cz += (z0 + z1) * c
    A *= 0.5
    return abs(A), (cy / (6 * A), cz / (6 * A))


def r2(v, n=2):
    if isinstance(v, (list, tuple)):
        return [r2(x, n) for x in v]
    if isinstance(v, dict):
        return {k: r2(x, n) for k, x in v.items()}
    if isinstance(v, float):
        return round(v, n)
    return v




# ============================================================================ design parameters
P = dict(
    # ---- v3 interfaces kept (P/S tables of v3)
    module_w=164.5, white_pitch=23.5, black_slot=164.5 / 12, frame_depth=212.0, rear_wall=(209.0, 212.0),
    z_eva=(0.0, 3.0), z_floor=(3.0, 5.0),
    key_top=43.5, key_bot=23.5, black_top=55.5, skin_w=2.0, skin_b=2.0, wall=1.2,
    dip_w=10.0, dip_b=9.5,
    # r3: head gap 1.46 (head 22.04), white-white tail gap 1.62, black base 10.4: every key-key x gap stays >= 1.3 after
    # the +-0.1 rear yaw at the balance pin AND the lateral play at the guide tab (tab_play)
    # r4: white-white tail gap 1.62 -> 1.64 (the balance pin moved 1.2 forward, so the rear yaw per mm grew and the E|F / B|C
    # tail gap fell to 1.2999)
    head_gap=1.46, tail_gap_ww=1.64, black_w=10.4, black_top_w=9.5,
    y_head=50.0, y_body_end=146.0, y_skin_end=147.0, y_black_top_end=142.0,   # top skin overhangs the rear wall 1.0 = rear lip (fingernail)
    y_black_front=54.2,
    # r4.1 (verifier geometry major 2): black top skin lowered behind the curtain (y144.3-147) to z54.1 (0.6 thick lip,
    # underside z53.5 kept): the pads of a pad bar being slid out pass 1.30 above it (r4.0: -0.10)
    black_skin_step=(144.3, 54.1),
    y_elem=67.0, z_elem_w=12.68, z_elem_b=10.15, bar_top_w=13.6, bar_top_b=11.5, bar_y=(59.0, 77.5),
    board_x=(47.25, 117.25), board_y=(145.5, 195.5), board_z=(9.0, 10.6), comp_zmax=20.0,
    # r4.1 (verifier physics major 2): the F|F# fin reaches the floor through an open slot cut from the front edge of the
    # stripboard (fin +-0.5, to y172; parts and wires keep 1.0 from the fin, i.e. out of x81.4-85.2 for y145.5-173;
    # the RP2040-Zero behind y172 is untouched).  The fin is grounded over y152-171, hung behind it
    # r4.3 (circuit BRD-01): the fin's grounded foot ends at y170.7 (r4.1: 171.0) so that its rear face stays 1.3 in front
    # of the RP2040-Zero's front edge (y172.0, the Zero now overhangs the slot end lifted on headers); the stripboard slot
    # itself still ends at board_slot_y1 = y172.0 (unchanged for the circuit), keep-out to y173.0
    # r4.3: keep-out for board parts / wires 1.0 -> 1.2 from the fin's main faces (x81.22-85.42, to y173.2): 1.3 from the
    # 0.1-inset foot that passes the slot (r4.1: 1.1 = 0.8 after +-0.3 FDM); every BRD-01 part is already outside it
    fin_slot_y=(152.0, 170.7), board_slot_clear=0.5, board_slot_keepout=1.2, board_slot_y1=172.0,
    # r4.3 (circuit BRD-01, control board designed against r4.1): the RP2040-Zero cannot be soldered flat (chips, crystal
    # and LDO on its underside); it stands on pin headers in its inner 2.54 holes, 1.3 higher than v3: USB-C centre z14.5
    # (v3 z13.2), plug overmould z10.7-18.3 (7.6 tall, <= 12.5 wide, <= 25 long from the receptacle mouth y195.5).
    # usb_clear = printed part to plug, nominal (1.0 after +-0.3 FDM)
    # r4.4 (circuit cross-check 2): the receptacle stands ~1.3 (1.0-1.5) proud of the Zero's edge -> plug face y196.8
    # (r4.3 y195.5), overmould y196.8-221.8
    usb_x=(77.75, 90.25), usb_y=(196.8, 221.8), usb_z=(10.7, 18.3), usb_wall_open=(74.0, 94.0, 5.0, 21.0), usb_clear=1.3,
    # BRD-01 parts (module x, y; z from the desk): Zero on headers (PCB z11.9-12.9, top parts <= z16.3:
    # receptacle z12.9-16.1 is the tallest, header pins trimmed), its USB-C receptacle, the 4067 module on headers
    # (<= z20), the 2x8 ribbon block J301 (16-core 1.27 ribbon = 20.32 wide), the EXT 1x6 pads J302 (lead soldered from
    # the underside), pad radius on the stripboard 0.9
    # r4.4 (circuit cross-check 1, BRD-01 on the Zero's 2.54 lattice x = 76.52 + 2.54 i, y = 173.59 + 2.54 j): Zero x75.14
    # (+0.14: Waveshare drawing puts the USB-C 4.67 from the right edge -> receptacle x79.53-88.47 centred on the shelf
    # slot, unchanged), receptacle y189.5-196.8 (proud of the edge), 4067 x54.93-72.71 y152.0-192.64, J301 x61.28-79.06
    # y148.19 / 150.73 now soldered from the UNDERSIDE (top: joints only <= ribbon_z), the ribbon runs under the board
    # (ribbon_under_z) centred on SB J201 (ribbon_xc, the lane centre) and only its last ribbon_j301[1] mm at J301 are
    # offset ribbon_j301[0] to the J301 centre x70.17; J302 x94.30-107.00 y193.91
    zero_xy=(75.14, 93.14, 172.0, 195.5), zero_z=(11.9, 12.9, 16.3), usb_rcpt=(79.53, 88.47, 189.5, 196.8, 12.9, 16.1),
    mux_xy=(54.93, 72.71, 152.0, 192.64), ribbon_pads=(61.28, 79.06, 148.19, 150.73), ribbon_cores=16, ribbon_pitch=1.27,
    ext_pads=(94.30, 107.00, 193.91), board_pad_r=0.9, ribbon_z=12.0, ext_z=12.0,
    ribbon_xc=70.48, ribbon_j301=(0.31, 6.0), ribbon_under_z=(5.0, 9.0),
    # r4.4 (circuit cross-check 3, circuit delta 14): 4 control-board stand-offs printed with the frame, D6 x z5-9 (board
    # underside z9.0): 'screw' = boss with a D2.5 bore down to z4.2 (0.8 into the floor) for an M3x6 screw = board 1.6
    # + stand-off 4.0 + 0.4; 'pin' = printed locating pin D2.8 through the board's D3.0 hole, 1.2 above the board.
    # v3 P114 spots (49.75,148)... left the head 0.75 from the rail's rear face y144.5 and 1.05 from the shelf ribs'
    # front face y196.8.  r4.4 resume: the bought screw is the v3.2 purchase line L35 '스텐 유두 렌치볼트 M3 x 6mm' =
    # ISO 7380 button head D5.7 x 1.65 (the circuit's delta 14 assumed a D5.5 head); board_screw = head envelope
    # D5.7 x 3.0, which also covers a DIN 912 socket head (D5.5 x 3.0) bought instead
    board_standoffs=((50.0, 149.0, "screw"), (114.5, 149.0, "pin"), (50.0, 192.5, "pin"), (114.5, 192.5, "screw")),
    standoff_d=6.0, standoff_bore=(2.5, 4.2), board_screw=(5.7, 3.0, 6.0), board_screw_real=(5.7, 1.65), board_pin=(2.8, 1.2), board_hole=3.0,
    # r4.4 fix 2b (verifier geometry CRITICAL: the board could not be put into the one-piece frame - the F|F# fin foot runs from
    # the floor to the top plate through the board's front-open slot and the fin hangs over the board's solid strip behind the
    # slot, the plate covers the board, and there is 1.3 of room behind it): the floor is opened under the board (board_hatch
    # x0, x1, y0, y1: 1.0 around the board, a notch to 1.0 behind the USB-C receptacle that stands 1.3 proud of the board edge), the board goes in from BELOW, its slot sliding up along the foot; the
    # foot no longer stands on a floor under it: fin_keel (y_rail, z bottom, z top) = the fin plate continued forward inside the
    # slot to the balance rail's rear face grounds it; the four stand-offs become bosses hanging ABOVE the board
    # (board_mount 'hung'): the front two on brackets from the balance rail's rear face (top board_boss[0]), the rear two on
    # brackets from the shelf ribs x50 / x116 up to the shelf underside; the two M3x6 go in from BELOW (head under the board)
    # into D2.5 blind bores up to board_boss[1]; the two locating pins hang down through the board's D3.0 holes (board_pin[1]
    # below the board).  Hole positions, slot, keep-out and every BRD-01 part are unchanged.
    board_mount="hung", board_hatch=(46.25, 118.25, 144.5, 196.5), board_hatch_notch=(78.53, 89.47, 197.8),
    fin_keel=(144.5, 3.0, 19.3), board_boss=(17.0, 15.4),
    # r4.5 fix 2 (resume): the keel to z21 of the first r4.5 fix-2 pass left 0.21 to key F's balance-block corner (y144.29 z20.9 at
    # the rigid bottom; the key's right tail wall is right over the F|F# fin line x82.52-83.72).  The keel top is set by the
    # block's rear-bottom edge in the return-overshoot pose (y143.4-144.2 z20.62): z19.3 leaves 1.34, and the F|F# fin itself
    # (full height, floor underside z3 to the plate) now starts at fin_keel_front, 1.4 behind key F's rearmost point (skin tail
    # y147.20 at the return overshoot) instead of y152: the keel is 4.1 long, not 7.5
    fin_keel_front=148.6,
    # r4.5 fix 2 (verifier fixes minor: the keel was clamped to a rigid balance rail): the keel root is now a 2x2 spring (w,
    # slope) = the balance rail + the floor strip under it as a beam along x between the neighbouring fin lines (keel_rail =
    # 'fins': simply supported for bending, twist held; 'hatch': clamped at the board-hatch edges; None: rigid as r4.4); over
    # the ribbon lane the rail (z lane top .. rail top) and the floor strip are separate (not composite); rail_top_est = the
    # rail top z used before the solved z_rail_low exists (build_geo)
    keel_rail="fins", rail_top_est=19.0,
    # r4.4 (circuit cross-check 4-5): v3 sensor-board support kept and now in the model: post (v3 P111, the M3x10 of the
    # bar / board go into it), front / rear ribs (v3 P113) under the spare rows y61.92 / 74.62, top z7.0 = board
    # underside; the rear rib is cut where the ribbon (module) or the lead pads (end parts) leave the board's underside.
    # Module rear-rib gap x60-82 (v3) -> x59-82 = the ribbon lane (ribbon x60.32-80.64 had 0.32 on the left)
    sb_board=(1.0, 162.6, 60.65, 75.89, 7.0, 8.6), sb_post=(0.5, 6.0, 59.0, 77.5), sb_rib_front=(61.0, 62.8), sb_rib_rear=(73.2, 75.5),  # r4.5 after circuit 2nd: SB end 162.9 -> 162.6 (circuit request: hand-cut stripboard +-0.3, 0.4 to the ledge post x163.0)
    sb_rib_x=(6.0, 158.5), sb_rib_gap=(59.0, 82.0), sb_j201=(61.59, 79.37, 72.08, 74.62),
    # r4.5 circuit 2nd cross-check (item 8): the v3 P112 right ledge of the frame over the sensor bar's right end (lost in
    # the r4 export; the v3 frame mass 175 g already holds it): lip x161.5-163.0 (1.5 overhang, underside = white bar top
    # z13.6), post x163.0-164.3 from the floor (0.2 seam inset as the fins), two pieces off the B sensor leads (y63.9-70.1)
    sb_ledge=(161.5, 163.0, 164.3, 13.6, 15.1), sb_ledge_y=((59.0, 63.4), (70.6, 77.5)),
    # end-part leads W401 (EL, 5 cores) / W411 (ER, 3 cores) of 1.27 ribbon strands: lane under the balance rail z5-10
    # (+ lead_margin per side) and a notch in the rear wall z5-12 at the same x (END_DEF[side]['sb'])
    lead_lane_z=(5.0, 10.0), lead_notch_z=(5.0, 12.0), lead_margin=1.3,
    # r4.4 resume: the lead's plan path fans in from the pad row to its lane width within lead_fan behind the board's
    # rear edge (EL: the wires of pads 3-5 sit in front of the A#0 black tab base y79; attempt 1 drew the fan-in to
    # y78.89 and its slanted edge came 0.76 from the tab base corner)
    lead_fan=1.5,
    # component envelope: <= comp_zmax up to comp_rear[0], then <= comp_rear[1] in the strip in front of the rear shelf
    # (shelf front y195.8, underside z18.05: 1.3 from both)
    comp_rear=(194.5, 16.7),
    # ... and it starts 1.3 behind the balance rail's rear face y144.5 (board edge y145.5 is 1.0 behind it; BRD-01 parts
    # start at y147.7, the ribbon passes under the rail in its lane)
    comp_front_y=145.8,
    # r4.3: ribbon lane under the balance rail widened 1.0 to the left (r4.1 x60-82): the 16-core ribbon (20.32, centred
    # on the J301 block x70.48) keeps 1.32 / 1.36 to the lane walls (r4.2 with 16 cores: 0.32 / 1.36)
    ribbon_x=(59.0, 82.0), bar_low_half=7.0,
    wall_relief=(137.0, 145.0, 25.2),            # tail side walls cut back over the key rod (y0, y1, bottom z)
    # v3 front parts (white stop rail/felt, guide tabs, hooks -> non-touching keepers)
    # r4 (audit A10 / r3 minor): white front felt cut to y1.5-9.0 (r3 9.8: 0.88 to the crossbar / rib corner at ff);
    # the key's down-stop floor y2.7-9.5 overhangs it by 0.5 only
    w_felt_y=(1.5, 9.0), w_floor_y=(2.7, 9.5), felt_front=3.0,
    w_crossbar_y=(10.5, 14.0), crossbar_t=1.6, w_hook_y=(11.5, 14.5), w_tab_y=(14.8, 25.0), w_rib_y=(10.5, 27.0),
    tab_cloth=0.5,
    b_crossbar_y=(76.5, 80.0), b_hook_y=(77.5, 80.5), b_tab_y=(80.8, 91.0), b_tab_base_y=(79.0, 93.0),
    b_felt_y=(54.5, 59.0), b_floor_y=(55.4, 59.3),
    # r4 (retention RET-3): keeper gap 1.2 -> 1.5 (hook printed 0.3 higher): >= 0.3 of 'keeper never touched' margin
    # in every PLAY case and material set
    keeper_gap=1.5, keeper_felt=2.0, hook_t=1.4, keeper_half=2.6,
    # ---- key seesaw
    # SNAP notch (r3): block bottom 0.75 below the rod centre, cloth-lined R2.55 wraps 223 deg; the lips first touch
    # the rod after 0.201 of lift and let go at 0.80 (lip corner on the rod equator).  r4 (RET-2): judged by LIFT
    # (PLAY <= 0.20 = lips never work, ABUSE <= 0.40 = pop-out 0.80 / 2); the static pull-off is 'anti-rattle' only:
    # 1.99 N by the model's lip law, set to 1-2 N by the stage-0 notch-radius coupon (R2.50..2.60)
    K=(141.0, 21.5), rod_k=4.0, cloth=0.5, notch_R=2.55, block_lift=-0.75, block_top=30.0,
    # r4 (RET-4): balance pin 1.2 forward (y136.5 -> 135.3): 1.46 / 1.39 from the snap-lip wall (r3 0.26 / 0.19)
    block_y=(134.0, 146.0),
    snap_F=2.0, snap_F_min=1.0,          # N: stage-0 coupon target band for the static pull-off (anti-rattle only)
    lift_play=0.20, lift_abuse=0.40, lift_popout=0.80,
    block_step_z=22.3, block_lip_wall=0.8,
    removal_lip_clear=0.1,       # the pull-up stops when the rear notch lip is 0.1 above the rod top (then slide forward)
    beam_w=8.0, beam_z=(21.8, 28.5), beam_z_cap=27.5, tail_top=24.9, y_tail_end=199.0, tail_chamfer=1.5,
    tail_w_b=10.0,
    rest_felt=1.5, rest_pad_y=(196.3, 199.0), rest_shim=0.2,     # 2 paper punchings 0.1 under each rest pad = key levelling
    # r4.4 (R44 issue 2): a rest felt that would cross the USB slot of the rear shelf (F, F#) is cut at the slot edge (no
    # felt over the plug) and runs the other way to the thin tail's edge (+ rest_foot[key], a printed foot = the thin tail
    # widened over rest_pad_y): F x71.69-76.45 (59 %, white tail = beam, no room), F# x91.55-95.94 (black tail 10 wide:
    # 55 %, r4.3 42 %).  No foot: an F foot (explored, 2.5 -> 91 %) hits key E's tail when F is drawn out forward.
    rest_foot={},
    # r4.4 fix 2: with the notch seated on the rod (-0.09 at the overshoot, now in the sweep) the F / F# tails at their own
    # return overshoot came to 1.24-1.25 of the control board's component envelope (<= z20, circuit interface, unchanged):
    # their beam / thin-tail underside is raised by the last value between the first two y (in front of the rest felt)
    # r4.4 fix 2b (verifier geometry major): with the worst material set's PLAY return overshoot in the sweep (white key -0.458 deg,
    # F -0.533) the E / G thin tails came 1.27 and the F beam / tail 1.30 from the board's component envelope: E and G get the same
    # relief, F's starts at y176 (over the CD74HC4067)
    tail_relief={"F": (176.0, 195.8, 0.15), "F#": (184.0, 195.8, 0.1), "E": (184.0, 195.8, 0.1), "G": (184.0, 195.8, 0.1)},
    pin_y=135.3, pin_d=2.0, pin_engage=1.0, pin_len=12.0, slot_w=2.2, slot_w_print=3.2, slot_depth=2.5, slot_y=(134.0, 138.0),
    rail_front_y=132.3,
    yaw_pin=0.10,
    # r4 (RET-5): black guide tab 7.5 -> 6.9 (6.9 + 2 x 0.5T cloth = 7.9 in the 8.0 between the black low walls:
    # +-0.05, r3 had 0.25 of interference per side); white tab 7.5 in 8.6 ribs as before
    tab_w=7.5, tab_w_b=6.9, rib_in=8.6, b_wall_in=8.0,
    tab_play=0.05,
    cradle_clear=1.3,
    # capstan = M3 button-head screw (ISO 7380: dk 5.7, k 1.65) in an M3 nut trap in the beam
    cap_dk=5.7, cap_k=1.65, cap_R=3.3, z_c=31.0,
    # ---- lever
    # r4 (audit A3): plain SUS304 D4 cold-drawn h9 rod (same 4 m bar as the key rod) through printed D3.9 bores drilled
    # D4.0; no brass bushings, no hardened shaft, no reamer.  D3 SUS yields (PLAY chord 407 MPa), D4 ABUSE 226 MPa.
    # r4 lead: the loads now stay below the ANNEALED minimum yield (205 MPa), so any SUS304 D4 h9 rod will do
    L=(203.25, 33.5), rod_L=4.0, hub_R=4.3, E_rod_L=193000.0, rod_L_yield=205.0, rod_L_yield_annealed=205.0,
    hub_bore_clear=0.05,
    yaw_lever=0.10,
    # r4 (audit A1): SS400 flat bar 9T x 19 cut to 40 (53.6 g, r3 9 x 50 x 21.5 = 75.8 g); no chamfer (the up-stop
    # contact moved from the R3 cap to the exposed steel top, U3)
    steel_w=9.0, steel_len=40.0, steel_h=19.0,
    steel_chamfer=0.0,
    y_steel_front=150.0, carrier_wall=0.8, lip=1.0, rear_wall_top=50.0, lip_end_y=186.0, cap_R_out=3.0, felt_c=2.0,
    felt_c_y=(176.5, 192.0), carrier_floor_y=(190.8, 192.5), carrier_floor_t=1.5,   # capstan contact stays at y188.3-188.7 (white) / 179.9-180.3 (black) over the stroke
    lip_front_y=165.0,
    lever_w=10.6,
    # r4 (RET-7): fingernail tab on the carrier front (lift the lever by hand for a key removal)
    nail_tab=(1.0, 1.5), nail_tab_below=-1.0,  # (forward, tall), top flush with the carrier top (the pad bar front runs 1.5 higher)
    # r4.2 (drafter): the tab (y148.2-149.2, z51.5-53.0) floated 0.42-3.0 in front of the R3 corner; it now fills the corner
    # above its underside z51.5 back to the arc (same outline as the mass model, which already counted the corner solid)
    # r4.1 (verifier geometry minor): the carrier's upper lips are interrupted over y168-184 (beside the soft pad; the
    # steel stays retained by the lips at y150-168 and 184-186 and by the front wall)
    us_contact="steel", lip_gap_y=(168.0, 184.0),
    # r4.4 (R44 issue 1, drafter): at the settled 1 N bottom (10.7 / 9.0 deg) and at ff the front lip's rear end (lever frame
    # y168) swings to world y172-173 z59-60, i.e. BESIDE the pad (lip x +-3.7..4.5 vs pad +-3.0: 0.64 after the lever yaw,
    # 0.34 after FDM).  The lip was not in geometry.json, so the sweep never saw it.  r4.4: the upper lips (and the side
    # wall top z53 that carries them) exist only over lip_segs (lever frame): the front lip ends at y163 (clear of the pad
    # by >= 1.3 at every pose), the rear lip runs on to the rear wall (y184-190, 2 -> 6 long: it carries the capstan-driven
    # hold-down of the steel's rear end).  lip_gap_y / lip_end_y above are the r4.1-r4.3 values (change log only).
    lip_segs=((150.0, 163.0), (184.0, 190.0)), lip_over=0.9,
    # r4.4 fix 2 (verifier geometry major 4a): between the top-lip segments (the pad zone) the side walls stood beside the soft
    # pad with an x gap of 1.5 only (1.01 once the lever's axial float 0.425 is counted, 0.71 with the pad bar's own +-0.3):
    # there the side-wall top is now wall_drop_pad BELOW the steel top, so the wall passes under the pad face (which rides on
    # the steel top): >= pad compression at ff (1.25) + 1.3 of vertical separation whatever the lateral play
    wall_drop_pad=2.6,
    # r4.4 fix 2 (verifier physics majors 1-2): a side-wall plate model (carrier_wall_plate) shows that the 0.8 side walls cannot
    # carry the pad-strike load as a snap: the eccentric bottom-lip load (51.7 N at PLAY 1.5 m/s) bends the wall at the lip root
    # to 19-26 MPa (in the layer plane, limit 12) and opens the snap 0.7-1.2 (overhang 1.0).  The steel is therefore BONDED into
    # the carrier (2-part epoxy on its two 19 x 40 side faces, after it has snapped in; the lips only hold it while the glue
    # cures).  bond_tau = design lap-shear strength of 2-part epoxy on sanded PETG / bare steel (lower bound, checked by
    # stage-0 test 20); bond_sf = required factor on it for every note (fatigue) / rare loads
    steel_bond=True, bond_tau=1.5, bond_sf_play=4.0, bond_sf_rare=2.0,
    # r4.4 fix 2b (verifier physics majors 1-2): a rigid 5-min epoxy (G ~700 MPa) cannot take the PETG / steel thermal mismatch
    # (shear-lag edge stress dalpha dT sqrt(G E_w t_w / t_a) = 2.2 MPa at dT 15 K, t_a 0.1) and had no gap to go into
    # (pocket 10.6 - 2 x 0.8 = 9.0 = steel).  Now a FLEXIBLE MS-polymer (hybrid sealant-adhesive) bond: shear modulus bond_G,
    # design lap-shear bond_tau (lower bound on sanded PETG / degreased steel, checked by stage-0 test 20 incl. thermal
    # cycles), bond line bond_t per side (checked down to bond_t_min for a steel pushed to one wall), dT every day / rare
    # (transport, car); the carrier SIDE walls are carrier_side_wall thin so the pocket is 9.2 (front / rear walls stay
    # carrier_wall), the top snap lips lip_over wide (inner edge x +-3.7 and the 10.6 outside as before)
    bond_adhesive="MS polymer", bond_G=1.0, bond_t=0.10, bond_t_min=0.02, bond_dT=(15.0, 30.0), bond_rho=1.5e-3,
    cte_petg=60e-6, cte_steel=11.7e-6, bond_G_epoxy=700.0, bond_tau_epoxy=2.0, carrier_side_wall=0.7,
    # r4 (audit A2): preloaded torsion assist spring on the lever rod: SUS304-WPB d0.5, ID 4.5, 4.2 active turns, coil in a
    # D6.1 x 3.0 pocket in the middle of the hub, short leg (3) in the hub, long leg (22.3) in a vertical groove on the
    # rear wall (y209, z50-58); k_t 8 N mm/rad, wound 30 deg at b = 0 (free angle -30 deg); 12 per module
    # r4.5 (user decision 2026-09-28): the custom D05 spring is replaced by the catalogue part MISUMI Korea economy torsion
    # spring C-UA90R5-3-0.5 (SUS304-WPB d0.5, ID 5, 3 turns, arm angle 90 deg, right-hand, arms 50 / 50; 282 KRW + VAT at 100+),
    # both arms cut: long leg spring_leg (coil axis -> tip centre, tangent), short leg spring_short_leg (from the tangent
    # point).  spring_E = the catalogue's own E (its k table back-solves to 186 GPa for all three arm angles with
    # n_body = 3 + (180 - arm) / 360); spring_n = that n_body; spring_swept_free = the wire's swept angle between the two
    # tangent points, free (1080 + 180 - arm).  spring_kt (with leg bending, Shigley N_e = n + (l1 + l2) / (3 pi D)) and
    # spring_free_deg (same b = 0 torque spring_T0 as D05: 8 x 30 deg) are computed below the dict.  spring_cat = the
    # catalogue's rate (legs 25 / 25), max-use angle and part number.  The coil is loaded in its winding direction only if
    # the LONG leg is at the coil's +x end (right-hand helix, CCW in (y, z) from the short leg to the long leg)
    spring_kt=None, spring_free_deg=None, spring_d=0.5, spring_ID=5.0, spring_n=3.25, spring_leg=22.3,
    spring_E=186000.0, spring_arm_deg=90.0, spring_swept_free=1170.0, spring_T0=8.0 * math.radians(30.0),
    spring_cat=dict(part="C-UA90R5-3-0.5", k_deg=0.1368, max_deg=55.0, arms=(50.0, 50.0), krw_100=282, hand="R"),
    # r4.1 (verifier geometry minor): the groove is cut in a printed boss on the rear wall face (y207.8-209, x = lever
    # +-1.6, z47 up to the plate) so it is 2.0 deep with a 0.5 x 45 deg lead-in; its bottom stays at y209.8 (loaded leg
    # unchanged), a keyless lever at -31.3 deg leaves the unloaded leg 1.52 inside the groove (r4.0: 0.32 of 0.8)
    # r4.2: the groove runs down to the boss underside (z47, open there): the long leg (tangent to the coil) reaches the
    # boss zone y >= 207.8 at z44.95, below the boss, and enters the groove from below (r4.1 groove z50-58 left 3 mm of
    # boss under it that the leg would have passed through)
    # r4.5 (MISUMI spring): pocket D6.1 -> 6.6 (coil OD 6.0 free, radial 0.3); rear-wall groove 1.2 x 2.0 -> 2.4 wide (the long
    # leg leaves a coil end at x +-0.8 whichever end it is: no x kink, the leg rises straight into the groove) x 3.2 deep (floor
    # y211.0, 1.0 of rear wall left behind it; the keyless lever keeps its unloaded leg 1.37 inside the mouth); boss 3.2 -> 4.4
    # wide (1.0 walls beside the groove)
    spring_pocket=(6.6, 3.0), spring_groove=(207.8, 47.0, 58.0, 2.4, 3.2), spring_boss=(4.4, 47.0, 1.2), spring_lead_in=0.5,
    # r4.2 (drafter: 'the pocket is closed all round, no slot for the long leg, short-leg hole without position'): the
    # pocket section of the hub (lever x +-1.5) is open through one parallel-sided slot, direction spring_slot[0] deg in the
    # lever frame (from +y toward +z at b = 0), faces at +spring_slot[1] (upper, short-leg seat) and -spring_slot[2] (lower)
    # from the axis (6.0 wide for the 5.5 coil): the coil drops in through it before the rod goes in, the SHORT leg
    # (3 long, tangent at the coil's upper side, bent out ~4.8 deg so its tip bears on the upper face: the return torque
    # goes in there, no hole), the LONG leg (tangent to the coil on the rear side) leaves through it over the whole lever
    # range (free angle -30 deg .. service lift +20 deg) with >= spring_leg_clear to both faces
    # short leg 2.5 (r4.1: 3): its tip then bears 0.6 inside the outer end of the 3.1 long face
    # r4.5 (MISUMI spring): slot faces +-3.25 (6.5 wide: the OD 6.0 coil passes); spring_rm = (ID + d) / 2 (set below).  The
    # catalogue part's swept angle (1170 deg) cannot bring both legs out through one slot (225 deg needed): only the LONG leg
    # uses the slot now; the SHORT leg (straight, tangent, no bend) lies in a new SHORT-LEG GROOVE through the hub wall of the
    # pocket section: spring_notch = (inner clearance: the inner face is rm - d/2 - this from the axis, so that the coil can
    # be slid in along the slot axis and the leg drops into the groove; band start along the leg from its tangent point).
    # Bearing face = the outer face at rm + d/2 (the spring pushes the leg CCW onto it); the groove runs out through the hub
    # wall and locally cuts the web underside over the pocket width
    # r4.5 fix 2 (verifier spring major: coil float on the rod): a short leg that only bears on one face lets the net leg force
    # push the coil 0.44 onto the fixed rod (ID 5.0 on D4): the leg lifts off, the spring unwinds ~11 deg (rest torque 4.19 ->
    # 2.4 N mm) and the coil rubs on the rod with 2-3 N (hysteresis mu_sr N r_rod ~1 N mm).  Now the short leg (cut to
    # spring_short_leg from its tangent point) is CAPTURED in a narrow blind groove (spring_notch = (play across the band,
    # band start inside the pocket, end clearance past the tip)) that runs along the leg from the pocket through the hub wall
    # into the web: the leg touches the groove's outer face at its tip and its inner face at the pocket edge, the spring
    # couple goes into the lever there (F = T / arm) and the coil hangs on its own leg, centred, clear of the rod.  The coil
    # goes in ALONG the leg (tip first) through an insertion slot at the rear-lower side (spring_slot = (direction, set below
    # from the groove, faces +-)); the long leg leaves through the rear opening up to the window face spring_window =
    # (direction, upper-face offset from the axis).  mu_sr = coil wire on the SUS rod (dry, used for the r4.5 comparison: the
    # captured coil does not touch the rod).  spring_groove_dx: the rear-wall groove and boss are centred on the long leg
    # (it leaves the coil's +x end at +0.8 from the lever centre) - verifier spring minor 2
    spring_slot=(318.7, 3.25, 3.25), spring_rm=None, spring_leg_clear=0.2, spring_short_leg=8.0, spring_notch=(0.20, -0.5, 0.3),
    spring_window=(35.0, 2.6), spring_groove_dx=0.8, mu_sr=0.30, spring_mode="capture", spring_notch_rot=0.0,
    # ---- fixed structure behind the keys
    rail_groove_lip=20.5, rail_y=(137.5, 144.5),
    rod_k_x=(1.55, 162.95), rail_x=(0.3, 164.2), rod_L_x=(1.5, 162.9), rod_L_plug=1.2, rod_L_blind=1.2,
    # r4.3: the rear shelf has an open slot over the USB plug, x usb_x -+ usb_clear (76.45-91.55), full depth y195.8-209:
    # the plug top z18.3 left 0.25 under the r4.2 thin shelf (underside z18.55).  shelf_usb_t is no longer used
    shelf_y=(195.8, 209.0), shelf_z=(18.0, 20.0), rib_t=1.2, rib_y0=196.8, shelf_usb_t=1.5,
    ribs=(8.0, 22.0, 36.0, 50.0, 62.0, 75.0, 93.0, 104.0, 116.0, 126.0, 136.0, 150.0),
    fin_t=1.8, fin_end_t=1.6, fin_y=(152.0, 209.0),
    fin_main_y0=176.0, fin_ext_inset=0.1,
    fins_after=("D", "F", "G#"),
    # lever spacing: r4 (A5) the r3 printed C-rings become hub collars (each lever's hub extended by half of every
    # lever-lever ring); lever-fin rings stay the fins' bosses (no brass).  gap = ring + share of the 0.3 axial play
    ring_min=1.5, ring_min_lf=1.35, ring_play=0.3,
    # r4.1 (verifier geometry minor): every printed hub collar 0.05 short -> axial play per fin bay 0.32 -> 0.52
    collar_short=0.05,
    # r4.4 fix 2 (verifier geometry major 4b): a lever-lever pair's two collars never sum to less than ring_min (the r4.1 0.05
    # shortening had left A#|B 1.40, A|A# 1.46, G|G# 1.48): collar = max(collar_min, ring/2 - collar_short), <= ring/2;
    # 0.76 (pair 1.52): with the pair's free gap closed and both levers yawed the carriers keep 1.30 at the overshoot pose
    collar_min=0.76,
    # r4.4 fix 2: a lever floated onto its fin boss (0.075) and yawed (0.05 at the fin's full-thickness front y176) was exactly
    # 1.30 from the fin; every fin boss is boss_extra longer than the ring it replaces (bay play 0.50 -> 0.46)
    boss_extra=0.02,
    # r4.4 fix 2 (verifier geometry major 4): the pad bar's lateral play between its rails (pad_bar_clear each side) moves its
    # pads, wedges, edge strips, leaves and grip; the sweep now adds it to those prisms (and each lever's one-sided axial float
    # on the rod, from the collar / boss gap chain)
    rail_pocket_y0=137.4,
    boss_R=3.5,                                   # fin boss around the lever rod (D7, printed, bore D3.9 drilled D4.0)
    # ---- r4 up-stop (U3 + U5): flat low-rebound pad on the exposed steel top, pad bars slid into the frame's top plate
    # r4 lead decision: pad 10 mm further back than U3 (y160-172 -> 170-182): the top plate is 12 thick behind y186, so the
    # seat at y176 is 1.7x stiffer (plate FE: 955-2107 N/mm per key vs 557-1492 at y166) and the pad face is 2 mm lower
    pad_y=(170.0, 182.0),
    pad_w=6.0,                   # pad width (x), between the carrier's top lips (7.4 apart)
    # r4: 6T foam (U3 had 4T): 18 % less pad force and a seat-compliance-tolerant ghost (0.45 N hold at 950 N/mm: 32 %
    # vs 67 % with 4T); height still under z74
    pad_felt=1.0, pad_foam=6.0,  # 1T felt face + microcellular urethane (PORON-type) foam
    pad_E=1.0,                   # MPa, foam secant modulus at small strain (felt face included)
    pad_epsD=0.8,                # densification strain of the foam law sigma = E eps / (1 - eps / eps_D)
    pad_e=0.06, pad_e_pass=0.07, # effective restitution of the lever on its pad (design / stage-0 pass line)
    seat_k=950.0,                # N/mm per key: pad seat used in the dynamics = the weakest key of the plate FE (F / F#)
    seat_k_req=830.0,            # stage-0 pass line: 100 N on one pad seat -> deflection <= 0.12 mm (the r4.0 seat, all PLAY targets met)
    seat_k_chord_req=460.0,      # r4.1 stage-0 pass line: 6 adjacent pads x 60 N -> each seat <= 0.13 mm
    # r4.1 (verifier geometry minor): the bar is 0.5 longer so it ends ON its rear stop (the plate step y183.5): the pads
    # sit where they are modelled when every note drives the bar back; a printed leaf on each rear-step edge presses
    # the bar up against the rail lips (0.6 x 4 x 8, 0.3 preload: ~0.25 N each, 9x the bar's weight)
    # r4.2 (drafter): the plate step (the bar's rear stop) and the bar's rear end go back 1.5 (183.5 -> 185.0): the
    # wedges / pads (rear edges y183.38 white, 183.17 black) were 0.12-0.45 from the step face; now 1.62 / 1.83
    pad_bar_t=1.5, pad_wedge_min=0.3, pad_bar_y=(146.5, 185.0), plate_step_y=185.0, pad_bar_clear=0.3, pad_bar_grip=3.0,
    # r4.2 (drafter: the bar's high front part ran to y169.5 over the plate's channel end y168 = 1.5 x 1.5 overlap): the
    # bar's top step is bar_joggle_clear in front of the channel end (y167.0), its bottom step 1.5 further (y165.5)
    bar_joggle_clear=1.0,
    # r4.2 (drafter: 'nothing holds the pad bar up'; r4.1 lip was 0.2 thick with 0.3 of overlap, the leaf only in words):
    # L-rails = web (bar_rail[0] wide, down to bar_rail[1] below the seat) + lip rail_lip wide (0.3 gap + 1.0 under the
    # bar edge) and rail_lip_t thick, its top bar_leaf_gap below the bar; each bar edge carries a printed leaf tongue
    # (thick, wide, long, preload) at y bar_leaf_y (root at the rear, bump at the front tip) whose bump rides on the lip and
    # presses the bar up against the plate seat; the tongue is cut free by a bar_leaf_slot slot and the bar above it
    bar_leaf=(0.6, 1.6, 8.0, 0.3), bar_leaf_y=(175.0, 183.0), bar_leaf_slot=0.4, bar_leaf_bump=0.8, bar_leaf_gap=0.3,
    # the lips start at rail_lip_y0 (the carrier side walls of the bay-edge levers pass under the web-only rail front
    # y160-163.5 when a lever is lifted for a key removal: service lift 15.5 deg as r4.1); during a slide-out the bar's lower
    # part rests on the lips until 21.5 mm of pull, where the procedure lifts it into the channel
    rail_lip=1.3, rail_lip_t=0.8, rail_y0=160.0, rail_lip_y0=163.5, bar_raise_pull=21.5,
    # r4.4: 45 deg chamfer on the front-bottom corner of every pad-bar rail web (y160, z64.7): the bay-edge carrier side wall
    # passes it at ff with 1.30 (r4.3 1.32; the r4.4 lever lost 0.08 g of double-counted lip mass and swings 0.02 deg higher)
    rail_front_chamfer=1.0,
    bar_rail=(1.0, 2.6),         # L-rail web under the plate: width, depth below the seat z (to the lip bottom)
    ledge_y0=146.5, plate_t=5.5,  # top plate: 5.5 thick from the front edge to the pads' rear end, 12 behind y186
    plate_rear_max=12.0,         # the top plate behind the pads is at most 12 thick (underside follows the levers + 1.3)
    # gap = pad face above the steel top at the TRULY settled 1 N held bottom, along the face normal (U1/U2):
    # negative = the lever meets its pad before the key meets its front felt
    # r4: white -0.40 / black -0.45 (U2 used -0.8 / -0.6 with the heavy r3 lever and no spring): with the light lever +
    # spring the repetition needs no pad preload; -0.45 on black keeps the 2.5 m/s lift at half the pop-out margin
    # while the black key at 1 N sits only 0.27 above its felt (-0.60: 0.55)
    gap_us_w=-0.40, gap_us_b=-0.45,
    rearm=0.50,                  # firmware re-arms a key when its magnet has risen 50 % of the travel
    # r4 firmware ghost filter (U6): within ghost_win ms of a note-on at >= ghost_v_note m/s (key front), a re-press
    # whose finger-point descent is < ghost_v_desc m/s AND < ghost_ratio x the previous note's speed is dropped
    # r4 lead: the descent limit is 25 % of the previous note's speed (cap 0.40 m/s) - U6 had a flat 0.30 m/s; the
    # 6-key chord ghosts over the soft F|F# plate zone come down at up to 0.30 m/s after a 1.5 m/s chord (0.39 after a 2.0 m/s
    # abuse chord); cap 0.45 = 25 % of 1.8 m/s
    # r4.1 (verifier physics major 1): the 1.2 m/s gate let soft-chord ghosts (0.8-1.1 m/s, descent 0.03-0.17) through;
    # the gate is lowered to 0.3 m/s: within 250 ms of ANY note >= 0.3 m/s a re-press slower than 25 % of it (cap 0.45) is dropped
    ghost_win=250.0, ghost_v_note=0.3, ghost_v_desc=0.45, ghost_ratio=0.25,
    # r4.5 circuit 2nd cross-check (item 9): a held strike that re-arms is run on to t_bottom + ghost_long ms to see whether
    # and when the ghost re-press lands (ghost_reland); the firmware judges the first re-press only up to ghost_rep_max ms
    # after the note-on (after that the key is a normal key again)
    ghost_long=1500.0, ghost_rep_max=500.0,
    front_e=0.20,
    black_mass=0.0, black_mass_pt=(99.0, 28.0),       # r4 (RET-1 / U4 / A4): no lead
    # ---- dust cover: one loose curtain strip hooked into a rabbet on the top plate's front edge (no pins, no magnets)
    # r4: curtain 1.0 forward of the r3 position (the lever's fingernail tab passes behind it at the return overshoot)
    curtain_y=(144.3, 145.5), curtain_gap_w=2.0, curtain_gap_b=2.0, curtain_notch_half=7.0, curtain_t=1.2,
    curtain_hook=(1.5, 1.0),     # hook lip over the top plate (y length, depth of the rabbet)
    dw_target_w=52.0, dw_target_b=51.0,
    # ---- friction (per contact)
    mu_kp=0.25, mu_Lp=0.25, mu_c=0.30, guide_drag=0.02,
    y_f13=13.0, y_f90=90.0, black_finger_back=10.0,
    # ---- r4 load envelopes (R4_BRIEF): PLAY = key-FRONT speed at the front-felt contact <= 1.5 m/s (single keys and
    # 6-key chords, fingers held 0.45-2 N or released); ABUSE = 2.5 m/s single key, 2.0 m/s 6-key chord (no damage only)
    v_play=1.5, v_abuse=2.5, v_abuse_chord=2.0, v_ff=1.0,
    # PETG across-layer stress limits (fins / walls print standing; r3 criteria kept): every note < 5 MPa, rare
    # (<= 1e4 events: 6-key chords, abuse) < 15 MPa; in-layer (plate bending) every note < 12, rare < 25 MPa
    s_cyc=5.0, s_rare=15.0, s_cyc_in=12.0, s_rare_in=25.0,
)
def spring_rate(P):
    """r4.5: torsion-spring rate (N mm/rad) of the cut catalogue spring: E d^4 / (64 D N_e), N_e = n_body + (l_long + l_short)
    / (3 pi D) with l_long = tangent point -> tip of the long leg (spring_leg is axis -> tip), l_short = spring_short_leg."""
    d, D = P["spring_d"], P["spring_ID"] + P["spring_d"]
    rm = D / 2
    l_long = math.sqrt(P["spring_leg"] ** 2 - rm ** 2)
    # r4.5 fix 2: the CAPTURED short leg carries the couple T from its root to the inner-face contact at s_E (moment T) and
    # then down to zero at its tip (s_t): its end-rotation compliance is (s_E + (s_t - s_E) / 3) / EI = the free-leg term
    # l / 3 with l = 2 s_E + s_t ('face' mode: the leg bears at its tip, l = spring_short_leg)
    if P.get("spring_mode", "capture") == "capture":
        s_E = math.sqrt((P["spring_pocket"][0] / 2) ** 2 - (rm - d / 2) ** 2)
        l_short = 2 * s_E + P["spring_short_leg"]
    else:
        l_short = P["spring_short_leg"]
    Ne = P["spring_n"] + (l_long + l_short) / (3 * math.pi * D)
    return P["spring_E"] * d ** 4 / (64 * D * Ne), Ne, l_long


P["spring_rm"] = (P["spring_ID"] + P["spring_d"]) / 2
P["spring_kt"] = spring_rate(P)[0]
P["spring_free_deg"] = -math.degrees(P["spring_T0"] / P["spring_kt"])
# r4.5 fix 2: coil mean radius at the rest wind (the captured short leg holds the loaded coil centred on the rod)
P["spring_rm_rest"] = (P["spring_ID"] + P["spring_d"]) * P["spring_n"] / (P["spring_n"] - P["spring_free_deg"] / 360.0) / 2
P["y_steel_rear"] = P["y_steel_front"] + P["steel_len"]
P["z_sb"] = P["z_c"] + P["felt_c"]                         # steel bottom
P["z_st"] = P["z_sb"] + P["steel_h"]                       # steel top
P["y_lever_front"] = P["y_steel_front"] - P["carrier_wall"]
P["pad_h"] = P["pad_felt"] + P["pad_foam"]

# ---- v3 plan data: white heads / tails, black bodies (x ranges) - v3 P-table KC..KB, KC#..KA#
WHITE = [  # name, head x0, x1, tail x0, x1, sensor/tail centre, guide (tab) centre
    ("C", 0.5, 23.0, 0.5, 14.361, 7.431),
    ("D", 24.0, 46.5, 28.069, 42.431, 35.250),
    ("E", 47.5, 70.0, 56.139, 70.0, 63.070),
    ("F", 71.0, 93.5, 71.0, 83.719, 77.359),
    ("G", 94.5, 117.0, 97.427, 110.646, 104.037),
    ("A", 118.0, 140.5, 124.354, 137.573, 130.964),
    ("B", 141.5, 164.0, 151.281, 164.0, 157.641),
]
BLACK = [("C#", 15.715), ("D#", 43.785), ("F#", 85.073), ("G#", 112.0), ("A#", 138.927)]
ORDER = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def key_table(P=P):
    """dict name -> plan data for the 12 module keys."""
    T = {}
    s = (P["head_gap"] - 1.0) / 2
    st = (P["tail_gap_ww"] - 1.0) / 2
    for n, h0, h1, t0, t1, c in WHITE:
        # v3 head 22.5 (gap 1.0) -> head 22.14 (gap 1.36); tail edges that coincide with a head edge (E|F, B|C
        # neighbours) move in so that white-white tail gaps are 1.52
        t0n = t0 + st if abs(t0 - h0) < 1e-6 else t0
        t1n = t1 - st if abs(t1 - h1) < 1e-6 else t1
        T[n] = dict(name=n, black=False, head=(h0 + s, h1 - s), tail=(t0n, t1n), xc=c, guide_c=(h0 + h1) / 2)
    bw, tw = P["black_w"], P["black_top_w"]
    for n, x0 in BLACK:
        xc = x0 + 5.5
        T[n] = dict(name=n, black=True, head=(xc - bw / 2, xc + bw / 2), tail=(xc - bw / 2, xc + bw / 2), xc=xc,
                    top=(xc - tw / 2, xc + tw / 2), guide_c=xc)
    return T


# ============================================================================ plan layout: levers, fins, spacers
def solve_lever_layout(P, keys, order, fins_fixed, fin_after, x_lo_fin, x_hi_fin):
    """lever centres (one per key, lever_w wide) + interior fins (fin_t) placed in the x-gaps named in
    `fin_after` (fin between order[i] and order[i+1]).  Every gap along the lever rod is >= ring_min plus its
    share of the segment's axial play (ring_play per fin-to-fin segment), so the printed rings can all be
    >= ring_min long: no gap can close below ring_min whatever the axial play does.  Minimise the largest
    |lever - key tail centre| (then the sum).  Each lever's 8 mm beam/balance block must stay inside its key tail.
    fins_fixed = (left fin (x0,x1), right fin (x0,x1)).  Returns dict."""
    from scipy.optimize import linprog
    n = len(order)
    nf = len(fin_after)
    nv = n + nf + 1 + n                     # c_k, f_j, t, d_k
    it = n + nf
    hw = P["lever_w"] / 2
    hf = P["fin_t"] / 2
    fj = {k: j for j, k in enumerate(fin_after)}
    # gap minima: segment gap counts
    seg_n, cur = [], 1
    for i in range(n):
        if i in fj:
            seg_n.append(cur + 0); cur = 1
        else:
            cur += 1 if i < n - 1 else 0
    # simpler: walk the item list
    items = ["fin"]
    for i, nm in enumerate(order):
        items.append(nm)
        if i in fj:
            items.append("fin")
    items.append("fin")
    gmin = []
    seg = []
    for k in range(len(items) - 1):
        seg.append(k)
        if items[k + 1] == "fin":
            for kk in seg:
                base = P["ring_min_lf"] if (items[kk] == "fin" or items[kk + 1] == "fin") else P["ring_min"]
                gmin.append(base + P["ring_play"] / len(seg))
            seg = []
    A, b = [], []

    def row():
        return [0.0] * nv
    # item k=0 is the left fin; gap index g runs over consecutive items
    gi = 0
    r = row(); r[0] = -1.0; A.append(r); b.append(-(fins_fixed[0][1] + gmin[gi] + hw)); gi += 1
    for i in range(n - 1):
        if i in fj:
            j = n + fj[i]
            r = row(); r[i] = 1.0; r[j] = -1.0; A.append(r); b.append(-(hw + hf + gmin[gi])); gi += 1
            r = row(); r[j] = 1.0; r[i + 1] = -1.0; A.append(r); b.append(-(hw + hf + gmin[gi])); gi += 1
        else:
            r = row(); r[i] = 1.0; r[i + 1] = -1.0; A.append(r); b.append(-(2 * hw + gmin[gi])); gi += 1
    r = row(); r[n - 1] = 1.0; A.append(r); b.append(fins_fixed[1][0] - gmin[gi] - hw)
    for i, nm in enumerate(order):
        kd = keys[nm]
        xc = kd["xc"]
        # |c - xc| <= d_i <= t
        r = row(); r[i] = 1.0; r[it + 1 + i] = -1.0; A.append(r); b.append(xc)
        r = row(); r[i] = -1.0; r[it + 1 + i] = -1.0; A.append(r); b.append(-xc)
        r = row(); r[it + 1 + i] = 1.0; r[it] = -1.0; A.append(r); b.append(0.0)
        # beam/block inside the tail footprint
        r = row(); r[i] = -1.0; A.append(r); b.append(-(kd["tail"][0] + P["beam_w"] / 2))
        r = row(); r[i] = 1.0; A.append(r); b.append(kd["tail"][1] - P["beam_w"] / 2)
    bounds = [(None, None)] * (n + nf) + [(0, None)] + [(0, None)] * n
    for j in range(nf):
        bounds[n + j] = (x_lo_fin[j], x_hi_fin[j])
    cost = [0.0] * nv
    cost[it] = 1.0
    for i in range(n):
        cost[it + 1 + i] = 0.02
    res = linprog(cost, A_ub=A, b_ub=b, bounds=bounds, method="highs")
    assert res.status == 0, res.message
    x = res.x
    c = [round(float(v), 3) for v in x[:n]]
    f = [round(float(v), 3) for v in x[n:n + nf]]
    fins = [tuple(fins_fixed[0])] + [(round(fc - hf, 3), round(fc + hf, 3)) for fc in f] + [tuple(fins_fixed[1])]
    levers = {nm: c[i] for i, nm in enumerate(order)}
    # gaps actually present along the lever rod (for spacer rings)
    its = [("fin", fins[0])]
    fi = 1
    for i, nm in enumerate(order):
        its.append((nm, (levers[nm] - hw, levers[nm] + hw)))
        if i in fj:
            its.append(("fin", fins[fi])); fi += 1
    its.append(("fin", fins[-1]))
    gaps = []
    for k, ((n0, r0), (n1, r1)) in enumerate(zip(its[:-1], its[1:])):
        gaps.append(dict(between=(n0, n1), x0=round(r0[1], 3), x1=round(r1[0], 3), gap=round(r1[0] - r0[1], 3), gmin=round(gmin[k], 3)))
    return dict(levers=levers, fins=fins, gaps=gaps, max_offset=round(float(x[it]), 2),
                offsets={nm: round(levers[nm] - keys[nm]["xc"], 2) for nm in order})


def module_layout(P):
    keys = key_table(P)
    fe = P["fin_end_t"]
    fa = [ORDER.index(n) for n in P["fins_after"]]
    lay = solve_lever_layout(P, keys, ORDER, ((0.2, 0.2 + fe), (164.3 - fe, 164.3)), fin_after=fa,
                             x_lo_fin=[keys[ORDER[i]]["xc"] for i in fa], x_hi_fin=[keys[ORDER[i + 1]]["xc"] for i in fa])
    return keys, lay


def spacer_rings(lay, P=None):
    """printed spacer rings (bore 3.2, OD 6) in every gap along the lever rod.  In each fin-to-fin segment
    the rings are shorter than their gaps by the segment's axial play (ring_play, shared equally), and never
    shorter than ring_min: with the play taken up anywhere, no lever-lever or lever-fin gap closes below ring_min."""
    P = globals()["P"] if P is None else P
    rings = []
    seg_gaps = []
    cur = []
    for g in lay["gaps"]:
        cur.append(g)
        if g["between"][1] == "fin":
            seg_gaps.append(cur); cur = []
    for seg in seg_gaps:
        tot = sum(g["gap"] for g in seg)
        s = P["ring_play"] / len(seg)
        for g in seg:
            base = P["ring_min_lf"] if "fin" in g["between"] else P["ring_min"]
            rings.append(dict(between=g["between"], x0=g["x0"], length=round(max(base, g["gap"] - s), 2), gap=g["gap"]))
    return rings


# ============================================================================ rigid bodies (mass model)
class Body:
    def __init__(self, name):
        self.name, self.el = name, []

    def box(self, tag, y0, y1, z0, z1, w, rho=RHO_PETG, fill=1.0):
        m = (y1 - y0) * (z1 - z0) * w * rho * fill
        self.el.append(dict(tag=tag, m=m, y=(y0 + y1) / 2, z=(z0 + z1) / 2,
                            I=m * ((y1 - y0) ** 2 + (z1 - z0) ** 2) / 12.0, rho=rho))
        return self

    def point(self, tag, y, z, m, I=0.0, rho=0.0):
        self.el.append(dict(tag=tag, m=m, y=y, z=z, I=I, rho=rho))
        return self

    @property
    def m(self):
        return sum(e["m"] for e in self.el)

    @property
    def com(self):
        M = self.m
        return (sum(e["m"] * e["y"] for e in self.el) / M, sum(e["m"] * e["z"] for e in self.el) / M)

    def I_about(self, c):
        return sum(e["I"] + e["m"] * ((e["y"] - c[0]) ** 2 + (e["z"] - c[1]) ** 2) for e in self.el)

    def mass_of(self, rho):
        return sum(e["m"] for e in self.el if e["rho"] == rho)


def block_x(P, kd):
    """balance block fills the key tail between its side walls (wide notch contact = roll stiffness); a key may carry
    its own narrower block (r3: C8, so that the rod gets a cradle at each end of its short end part)."""
    if "block" in kd:
        return kd["block"]
    return kd["tail"][0] + P["wall"], kd["tail"][1] - P["wall"]


def tail_w(P, black):
    """width of the thin tail behind the capstan (black keys wider: the long black arm to the rest pad)."""
    return P.get("tail_w_b", P["beam_w"]) if black else P["beam_w"]


def rest_pad_x(P, nm, xl, black):
    """r4.4: x range of a key's rest felt and of its printed rest foot (None if none).  Default: the 8.0 felt centred on
    the lever / beam.  A felt that would cross the USB slot of the rear shelf is cut at the slot edge (nothing hangs over
    the plug) and runs the other way to the thin tail's edge + rest_foot[nm] (the foot widens the thin tail over the
    rest-pad y range)."""
    bw = P["beam_w"] / 2
    a, b = xl - bw, xl + bw
    if "usb_x" not in P or not P.get("rest_felt_cut", True):       # rest_felt_cut False = r4.3 felts (8.0 centred)
        return (a, b), None
    s0, s1 = usb_slot(P)
    if b <= s0 or a >= s1:
        return (a, b), None
    tw = tail_w(P, black) / 2
    ft = P.get("rest_foot", {}).get(nm, 0.0)
    if xl < 0.5 * (s0 + s1):
        return (xl - tw - ft, s0), ((xl - tw - ft, xl - tw) if ft > 0 else None)
    return (s1, xl + tw + ft), ((xl + tw, xl + tw + ft) if ft > 0 else None)

def key_body(P, kd, y_cap, x_lever):
    """mass model of one key (white or black variant) - PETG boxes + magnet + capstan screw/nut."""
    zb = P["key_bot"]
    wl = P["wall"]
    b = Body(kd["name"])
    hw = kd["head"][1] - kd["head"][0]
    tw = kd["tail"][1] - kd["tail"][0]
    if not kd["black"]:
        zt, sk = P["key_top"], P["skin_w"]
        b.box("top skin head", 0, P["y_head"], zt - sk, zt, hw)
        b.box("top skin tail", P["y_head"], P["y_skin_end"], zt - sk, zt, tw)
        b.box("side walls head", 1.5, P["y_head"], zb, zt - sk, 2 * wl)
        b.box("side walls tail", P["y_head"], P["y_body_end"], zb, zt - sk, 2 * wl)
        b.box("front wall", 1.5, 2.7, zb, zt - sk, hw - 2 * wl)
        if hw - tw > 0.1:
            b.box("head step wall", P["y_head"] - wl, P["y_head"], zb, zt - sk, hw - tw)
        b.box("rear wall", P["y_body_end"] - wl, P["y_body_end"], zb, zt - sk, tw - 2 * wl)
        for y in (40.0, 90.0, 118.0):
            b.box("rib", y - 0.6, y + 0.6, zt - sk - 8, zt - sk, (hw if y < 50 else tw) - 2 * wl)
        b.box("guide ribs", P["w_rib_y"][0], P["w_rib_y"][1], zb, zt - sk, 2 * wl)
        b.box("crossbar", P["w_crossbar_y"][0], P["w_crossbar_y"][1], zb, zb + P["crossbar_t"], 8.6)
        b.box("down-stop floor", P["w_floor_y"][0], P["w_floor_y"][1], zb, zb + 1.2, hw - 2 * wl)
    else:
        zt, sk = P["black_top"], P["skin_b"]
        f0 = P["y_black_front"]
        bw = P["black_w"]
        b.box("top skin", f0 + 1.0, P["y_black_top_end"], zt - sk, zt, P["black_top_w"])
        b.box("top skin rear", P["y_black_top_end"], P["y_skin_end"], zt - sk, zt, bw)
        b.box("side walls", f0, P["y_body_end"], zb, zt - sk, 2 * wl)
        b.box("front wall", f0, f0 + wl, zb, zt - sk, bw - 2 * wl)
        b.box("rear wall", P["y_body_end"] - wl, P["y_body_end"], zb, zt - sk, bw - 2 * wl)
        for y in (100.0, 125.0):
            b.box("rib", y - 0.6, y + 0.6, zt - sk - 8, zt - sk, bw - 2 * wl)
        b.box("stop floor", P["b_floor_y"][0], P["b_floor_y"][1], zb, zb + 1.2, bw - 2 * wl)
        b.box("crossbar", P["b_crossbar_y"][0], P["b_crossbar_y"][1], zb, zb + P["crossbar_t"], 8.6)
        if P.get("black_mass", 0.0) > 0:          # r4: no lead -> no pocket
            my = P["black_mass_pt"][0]
            b.box("mass pocket floor", my - 4.0, my + 4.0, zb, zb + 1.0, bw - 2 * wl)
            b.box("mass pocket end walls", my - 4.6, my + 4.6, zb, zb + 9.0, 1.2 * 2 * 0.5)
    # magnet boss tube + magnet; r3: the boss is tied to both side walls by a full-height rib at y_elem (exported too)
    a_boss = math.pi / 4 * (7.6 ** 2 - 5.2 ** 2)
    b.point("magnet boss", P["y_elem"], (zb + zt - sk) / 2, a_boss * (zt - sk - zb) * RHO_PETG, rho=RHO_PETG)
    w_in = (P["black_w"] if kd["black"] else tw) - 2 * wl
    b.box("magnet boss rib (wall to wall, minus the tube)", P["y_elem"] - 0.6, P["y_elem"] + 0.6, zb, zt - sk, max(0.0, w_in - 7.6))
    b.point("magnet N35 5x2", P["y_elem"], zb + 1.0, math.pi / 4 * 25 * 2 * RHO_MAG, rho=RHO_MAG)
    # balance block (8 wide at the lever centre, z block_bottom .. skin), minus the notch half-disc
    zbb = P["K"][1] + P["block_lift"]
    y0, y1 = P["block_y"]
    bx0, bx1 = block_x(P, kd)
    bwid = bx1 - bx0
    c_ = P["block_lift"]
    Rn_ = P["notch_R"]
    notch = (Rn_ ** 2 * math.acos(c_ / Rn_) - c_ * math.sqrt(Rn_ ** 2 - c_ ** 2)) * bwid    # circular segment above the block bottom
    zbt = P["block_top"]
    zs_ = P.get("block_step_z", zbb)
    yl0_, yl1_ = block_lip_y(P)
    vb = (y1 - y0) * (zbt - zs_) * bwid + (yl1_ - yl0_) * (zs_ - zbb) * bwid - notch      # r3: stepped bottom
    b.point("balance block", (y0 + y1) / 2, (zbb + zbt) / 2, vb * RHO_PETG,
            I=vb * RHO_PETG * ((y1 - y0) ** 2 + (zbt - zbb) ** 2) / 12, rho=RHO_PETG)
    b.box("block web to skin", y0, y1, zbt, zt - sk, 1.6)
    b.box("notch cloth", P["K"][0] - 2.5, P["K"][0] + 2.5, zbb, zbb + 2.0, bwid, rho=RHO_FELT, fill=0.25)
    # hidden beam, nut trap, thin tail, rest felt
    b0, b1 = P["beam_z"]
    b.box("beam", P["y_body_end"], y_cap - 6.0, b0, b1, P["beam_w"])
    b.box("beam at capstan (lowered)", y_cap - 6.0, y_cap + 4.0, b0, P["beam_z_cap"], P["beam_w"])
    b.box("nut trap void", y_cap - 2.8, y_cap + 2.8, 23.8, 26.4, 5.6, fill=-1.0)
    b.point("capstan screw M3x6 ISO7380 + nut", y_cap, 27.0, 0.95, rho=RHO_ST)
    b.box("thin tail", y_cap + 4.0, P["y_tail_end"], b0, P["tail_top"], tail_w(P, kd["black"]))
    rl_ = P.get("tail_relief", {}).get(kd["name"])
    if rl_:
        # r4.4 fix 2: underside relief (beam 8 wide in front of y_cap + 4, thin tail behind)
        for ya_, yb_, w_ in ((rl_[0], min(rl_[1], y_cap + 4.0), P["beam_w"]), (max(rl_[0], y_cap + 4.0), rl_[1], tail_w(P, kd["black"]))):
            if yb_ > ya_:
                b.box("tail underside relief", ya_, yb_, b0, b0 + rl_[2], w_, fill=-1.0)
    # r4.4: rest felt cut / widened beside the USB slot (F, F#), printed rest foot (F)
    (fx0, fx1), foot = rest_pad_x(P, kd["name"], x_lever, kd["black"])
    if foot:
        b.box("thin tail rest foot", P["rest_pad_y"][0], P["y_tail_end"], b0, P["tail_top"], foot[1] - foot[0])
    b.box("rest felt", P["rest_pad_y"][0], P["rest_pad_y"][1], b0 - P["rest_felt"], b0, fx1 - fx0, rho=RHO_FELT)
    if kd["black"] and P.get("black_mass", 0.0) > 0:
        b.point("black-key mass (lead / brass, non-magnetic)", P["black_mass_pt"][0], P["black_mass_pt"][1], P["black_mass"], rho=11.3e-3)
    return b



def bump_crown(P):
    """R3 rounding of the carrier's front-top corner (lever frame, rest): circle centre and radius.  r4: no longer the
    up-stop contact (the pad bears on the exposed steel top), kept as the front corner of the carrier and as the
    reference point of the 'cap top' heights."""
    R = P["cap_R_out"]
    return (P["y_lever_front"] + R, P["z_st"] + P["lip"] - R), R


def steel_top_pts(P, n=300):
    """exposed steel top (lever frame): behind the 3 mm printed cap over the steel front, between the top lips."""
    ys = np.linspace(P["y_steel_front"] + 3.0, P["y_steel_rear"], n)
    return np.column_stack([ys, np.full(n, P["z_st"])])


def lever_body(P, h=None):
    """r4 lever: SS400 9T x 19 x 40 in a printed carrier (side walls 0.8 with top/bottom snap lips, front wall with the
    R3 corner and a fingernail tab, rear wall, a 1.5 floor behind the steel that backs the capstan felt), web to the hub,
    hub (D3.9 drilled D4.0) with the torsion-spring pocket; the torsion spring itself (r4.5: 0.13 g) rides on the lever."""
    h = P["steel_h"] if h is None else h
    s0, s1 = P["y_steel_front"], P["y_steel_front"] + P["steel_len"]
    zs = P["z_sb"]
    zt = zs + h
    w, cw, lp = P["steel_w"], P["carrier_wall"], P["lip"]
    cws = P.get("carrier_side_wall", cw)            # r4.4 fix 2b: side walls (front / rear walls stay cw)
    Ly, Lz = P["L"]
    lv = Body("lever")
    lv.box("steel block SS400 9x%gx%g" % (h, P["steel_len"]), s0, s1, zs, zt, w, rho=RHO_ST)
    # r4.4: side walls up to the steel top, raised by the lip height only where the top snap lips are (lip_segs)
    lv.box("carrier side walls", s0, s1, zs - lp, zt, 2 * cws)
    lv.box("carrier bottom lips", P["lip_front_y"], P["felt_c_y"][0], zs - lp, zs, 2 * (P["lever_w"] / 2 - cws - 3.5))
    for y0_, y1_ in P["lip_segs"]:
        lv.box("carrier side-wall top + top snap lips y%.0f-%.0f" % (y0_, y1_), y0_, y1_, zt, zt + lp, 2 * (cws + P["lip_over"]))
    if P.get("bond_t", 0.0) > 0:
        # r4.4 fix 2b: the MS-polymer film in the two bond lines (bonded area x bond_t)
        sb_ = steel_bond(P)
        lv.box("bond film (MS polymer, 2 x %.2f)" % P["bond_t"], s0, s1, zs, zt, sb_["area"] * P["bond_t"] / ((s1 - s0) * h), rho=P["bond_rho"])
    # r4.4 fix 2: side-wall top wall_drop_pad below the steel top between the lip segments (the pad zone)
    for (a0_, a1_), (b0_, b1_) in zip(sorted(P["lip_segs"])[:-1], sorted(P["lip_segs"])[1:]):
        if P.get("wall_drop_pad", 0.0) > 0 and b0_ > a1_:
            lv.box("carrier side walls lowered in the pad zone y%.0f-%.0f" % (a1_, b0_), a1_, b0_, zt - P["wall_drop_pad"], zt, 2 * cws, fill=-1.0)
    lv.box("front wall + R3 corner", s0 - cw, s0, zs, zt + lp, w)
    lv.box("cap over steel", s0, s0 + 3.0, zt, zt + lp, w - 1.6)
    ft, fh = P["nail_tab"]
    ztab = zt - P["nail_tab_below"]
    lv.box("fingernail tab", s0 - cw - ft, s0 - cw, ztab - fh, ztab, w)
    lv.box("rear wall", s1, s1 + cw, zs - lp, P["rear_wall_top"], w)
    f0, f1 = P["carrier_floor_y"]
    lv.box("rear floor (backs the capstan felt)", f0, f1, zs, zs + P["carrier_floor_t"], w)
    a_hub = math.pi * (P["hub_R"] ** 2 - (P["rod_L"] / 2) ** 2)
    mh = a_hub * P["lever_w"] * RHO_PETG
    lv.point("hub", Ly, Lz, mh, I=mh * (P["hub_R"] ** 2 + 2.0 ** 2) / 2, rho=RHO_PETG)
    Dp, tp = P["spring_pocket"]
    # r4.5: the whole pocket-section removal (pocket, coil / long-leg slot, short-leg groove, web-underside cut) at its centroid;
    # r4.2-r4.4 counted the pocket cylinder only
    ra_, rc_ = pocket_section_removed(P)
    lv.point("spring pocket + slot + short-leg groove (pocket section)", rc_[0], rc_[1], -ra_ * tp * RHO_PETG, rho=RHO_PETG)
    lv.box("web rear wall -> hub", s1 + cw, Ly, Lz + 0.5, Lz + 10.0, P["lever_w"], fill=0.35)
    lv.box("felt strip 2T", P["felt_c_y"][0], P["felt_c_y"][1], zs - P["felt_c"], zs, 7.0, rho=RHO_FELT)
    if P.get("spring_kt", 0.0) > 0:
        # r4.5: the cut MISUMI spring (coil + both legs, spring_mass) on the axis (r4.4: 0.15 g at z +2)
        ms_ = spring_mass(P)[0]
        lv.point("torsion spring (coil + legs)", Ly, Lz, ms_, I=ms_ * P["spring_rm"] ** 2, rho=RHO_SUS)
    return lv
# ============================================================================ kinematics + statics (1 DOF, rigid contact)
class Action:
    """one key + its lever with exact rotation kinematics (key pinned on its rod, lever on the capstan)."""

    def __init__(self, P, kd, y_cap, x_lever, spring=None, h=None, fmul=1.0, cap_dz=0.0, extra=None):
        self.P, self.kd = P, kd
        self.black = kd["black"]
        self.y_cap, self.x_lever = y_cap, x_lever
        self.key = key_body(P, kd, y_cap, x_lever)
        self.lev = lever_body(P, h)
        for where, tag, yy, zz, mm in (extra or []):         # tungsten putty etc.
            (self.key if where == "key" else self.lev).point(tag, yy, zz, mm)
        self.h = P["steel_h"] if h is None else h
        self.K, self.L = P["K"], P["L"]
        self.R = P["cap_R"]
        self.C0 = (y_cap, P["z_c"] - self.R + cap_dz)    # capstan crown centre (key frame, rest); cap_dz = screw turned out
        self.Q0 = (y_cap, P["z_c"])                      # point of the lever felt plane (lever frame, rest)
        self.mk, self.ck, self.Ik = self.key.m, self.key.com, self.key.I_about(self.K)
        self.mL, self.cL, self.IL = self.lev.m, self.lev.com, self.lev.I_about(self.L)
        zt = P["black_top"] if self.black else P["key_top"]
        self.zt = zt
        self.front = (P["y_black_front"] + 1.0, zt) if self.black else (0.0, zt)
        self.dip = P["dip_b"] if self.black else P["dip_w"]
        self.finger = (self.front[0] + P["black_finger_back"], zt) if self.black else (P["y_f13"], zt)
        self.guide = ((sum(P["b_tab_y"]) / 2) if self.black else (sum(P["w_tab_y"]) / 2), P["key_bot"])
        fy = P["b_floor_y"] if self.black else P["w_floor_y"]
        self.stop_pts = [(fy[0], P["key_bot"]), (fy[1], P["key_bot"])]
        zr = P["beam_z"][0] - P["rest_felt"] - P["rest_shim"]
        self.rest_pts = [(P["rest_pad_y"][0], zr), (P["rest_pad_y"][1], zr)]
        cb = P["b_crossbar_y"] if self.black else P["w_crossbar_y"]
        hk = P["b_hook_y"] if self.black else P["w_hook_y"]
        self.keeper_pts = [(max(cb[0], hk[0]), P["key_bot"] + P["crossbar_t"]),
                           (min(cb[1], hk[1]), P["key_bot"] + P["crossbar_t"])]
        self.mag = (P["y_elem"], P["key_bot"])
        s0 = P["y_steel_front"]
        self.cap_c, self.cap_Rb = bump_crown(P)       # up-stop contact = crowned bump on the carrier top
        self.a_dip = self.solve_a(self.front, self.dip)
        self.b_dip = self.solve_b(self.a_dip)
        # r4 torsion assist spring on the lever rod: T(b) = k_t (b - b_free) for b > b_free, pushes the steel down.
        # spring=None -> from P (spring_kt, spring_free_deg); spring=False -> none; or dict(kt=, b_free=rad)
        # r4.5 fix 2: spring=None -> T(b) and the coil-on-rod force N(b) from the pose solver spring_pose (captured short leg:
        # the coil stays centred, N = 0; 'face' mode = the r4.5 float); a dict with 'table' = (b deg, T, N) likewise
        if spring is None:
            spring = dict(kt=P.get("spring_kt", 0.0), b_free=math.radians(P.get("spring_free_deg", 0.0)), table=spring_T_table(P)) if P.get("spring_kt", 0.0) > 0 else False
        self.spring = spring if spring else None
        self.fmul = fmul

    # ---------------------------------------------------------------- rotations
    def kp(self, p, a):
        return rot(p, self.K, a)

    def lp(self, p, b):
        return rot(p, self.L, -b)

    def dkz(self, p, a):
        dy, dz = p[0] - self.K[0], p[1] - self.K[1]
        return dy * math.cos(a) - dz * math.sin(a)

    def dlz(self, p, b):
        dy, dz = p[0] - self.L[0], p[1] - self.L[1]
        return -dy * math.cos(b) - dz * math.sin(b)

    def solve_a(self, p, drop):
        lo, hi = 0.0, 0.35
        for _ in range(80):
            m = (lo + hi) / 2
            if p[1] - self.kp(p, m)[1] < drop:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2

    def cap_top(self, b):
        """highest point of the R3 cap (lever at angle b): world z."""
        c = self.lp(self.cap_c, b)
        return c[1] + self.cap_Rb

    # ---------------------------------------------------------------- capstan / felt-plane contact
    def geo(self, a, b):
        C = self.kp(self.C0, a)
        Q = self.lp(self.Q0, b)
        n = (-math.sin(b), -math.cos(b))
        t = (math.cos(b), -math.sin(b))
        d = (C[0] - Q[0]) * n[0] + (C[1] - Q[1]) * n[1]
        gap = d - self.R
        dC = (-(C[1] - self.K[1]), C[0] - self.K[0])
        g_a = dC[0] * n[0] + dC[1] * n[1]
        dQ = (Q[1] - self.L[1], -(Q[0] - self.L[0]))
        dn = (-math.cos(b), math.sin(b))
        g_b = -(dQ[0] * n[0] + dQ[1] * n[1]) + (C[0] - Q[0]) * dn[0] + (C[1] - Q[1]) * dn[1]
        Pc = (C[0] - self.R * n[0], C[1] - self.R * n[1])
        return gap, g_a, g_b, n, t, Pc

    def solve_b(self, a, b0=0.0):
        b = b0
        for _ in range(60):
            gap, g_a, g_b, *_ = self.geo(a, b)
            step = -gap / g_b
            b += step
            if abs(step) < 1e-13:
                break
        return b

    def j(self, a):
        b = self.solve_b(a)
        gap, g_a, g_b, *_ = self.geo(a, b)
        return -g_a / g_b, b

    def slip_rate(self, a, b, va, vb):
        _, _, _, n, t, Pc = self.geo(a, b)
        vk = (-va * (Pc[1] - self.K[1]), va * (Pc[0] - self.K[0]))
        wl = -vb
        vl = (-wl * (Pc[1] - self.L[1]), wl * (Pc[0] - self.L[0]))
        return (vk[0] - vl[0]) * t[0] + (vk[1] - vl[1]) * t[1]

    # ---------------------------------------------------------------- statics
    def statics(self, a, fpt=None, spring=True):
        """quasi-static finger force at fpt: balance, friction at every contact, DW, UW, m_eff."""
        P = self.P
        fpt = self.finger if fpt is None else fpt
        jj, b = self.j(a)
        Qa = -self.mk * G * self.dkz(self.ck, a)
        Qb = -self.mL * G * self.dlz(self.cL, b)
        if spring and self.spring:
            Qb -= self.spring_T(b)
        dzf = self.dkz(fpt, a)
        F = (Qa + jj * Qb) / dzf
        gap, g_a, g_b, n, t, Pc = self.geo(a, b)
        N = -Qb / g_b
        Rk = math.hypot(-N * n[0], self.mk * G - N * n[1] + F)
        RL = math.hypot(N * n[0], self.mL * G + N * n[1])       # torsion spring = a couple (leg reaction on the wall)
        slip = abs(self.slip_rate(a, b, 1.0, jj))
        dzg = abs(self.dkz(self.guide, a))
        fm = self.fmul
        wf = dict(key_rod=fm * P["mu_kp"] * P["rod_k"] / 2 * Rk,
                  lever_rod=fm * P["mu_Lp"] * P["rod_L"] / 2 * RL * abs(jj),
                  capstan=fm * P["mu_c"] * N * slip,
                  guide=fm * P["guide_drag"] * dzg)
        if spring and self.spring:
            wf["spring_rod"] = fm * self.spring_H(b) * abs(jj)      # r4.5 fix 2: 0 with the captured short leg
        fr = {k: v / abs(dzf) for k, v in wf.items()}
        f = sum(fr.values())
        r = abs(dzf)
        meff = (self.Ik + self.IL * jj ** 2) / r ** 2
        return dict(a=a, b=b, j=jj, BW=F / G, f=f / G, fr={k: v / G for k, v in fr.items()},
                    DW=(F + f) / G, UW=(F - f) / G, N=N, Rk=Rk, RL=RL, meff=meff,
                    meff_key=self.Ik / r ** 2, meff_lev=self.IL * jj ** 2 / r ** 2, r=r, slip=slip)

    # r4 torsion assist spring (couple on the lever, N mm; positive = pushes the steel down)
    def spring_T(self, b):
        sp = self.spring
        if not sp:
            return 0.0
        if sp.get("table") is not None:
            tb = sp["table"]
            return float(np.interp(math.degrees(b), tb[0], tb[1]))
        return sp["kt"] * (b - sp["b_free"]) if b > sp["b_free"] else 0.0

    # r4.5 fix 2: coil-on-rod friction torque of the spring (hysteresis, N mm at friction x1): mu_sr N(b) r_rod
    def spring_H(self, b):
        sp = self.spring
        if not sp or sp.get("table") is None:
            return 0.0
        tb = sp["table"]
        return self.P.get("mu_sr", 0.0) * float(np.interp(math.degrees(b), tb[0], tb[2])) * self.P["rod_L"] / 2

    def mag_travel(self, a=None):
        a = self.a_dip if a is None else a
        return self.mag[1] - self.kp(self.mag, a)[1], self.kp(self.mag, a)[0] - self.mag[0]

# ============================================================================ felt law + 4-DOF dynamics
# Contact law: Hunt-Crossley F = K d^1.5 (1 + chi d'), with the Flores et al. (2011) damping
# chi = 8(1-e_in)/(5 e_in v0).  The coefficient of restitution this law actually produces is NOT e_in
# (e_in 0.35 gives 0.309, independent of mass and speed - checked by felt_effective_e()).  The design
# values below are EFFECTIVE restitutions (what a drop test measures); e_input() converts each one to the
# Flores input that reproduces it.  K, e_eff are assumptions for dense wool felt / bushing cloth / the
# low-rebound up-stop pad; the stage-0 drop test measures them.
V0_FLOOR = 0.02      # m/s: onset speeds below this use this value (quasi-static contacts)


class Felt:
    def __init__(self, KE, vf=None):
        self.K, self.e = KE          # (K, Flores INPUT e)
        self.on, self.chi = False, 0.0
        self.vf = V0_FLOOR if vf is None else vf     # r4: onset-speed floor reported over 0.02-0.1 m/s (r3 minor)

    def force(self, pen, pen_dot):
        if pen <= 0:
            self.on = False
            return 0.0
        if not self.on:
            self.on = True
            v0 = max(abs(pen_dot), self.vf)
            self.chi = 8 * (1 - self.e) / (5 * self.e * v0)
        return max(0.0, self.K * pen ** 1.5 * (1.0 + self.chi * pen_dot))


def felt_effective_e(KE, m=30.0, v=0.5, dt=2e-5):
    """coefficient of restitution of the contact law with (K, Flores input e) - 1-DOF drop."""
    f = Felt(KE)
    x, vv = 0.0, v
    while True:
        Fn = f.force(x, vv)
        vv -= Fn / m * dt
        x += vv * dt
        if x < 0:
            return -vv / v


def e_input(e_eff, K=30.0):
    """Flores input e that gives the effective restitution e_eff."""
    lo, hi = e_eff, 0.999
    for _ in range(40):
        mid = (lo + hi) / 2
        if felt_effective_e((K, mid)) < e_eff:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# design contact data: (K N/mm^1.5, EFFECTIVE restitution).  r4: the up-stop pad is not a Hertz-type felt any more
# (flat foam pad on the steel top, see PadTable)
FELT_EFF = dict(front=(30.0, P["front_e"]), front_b=(20.0, P["front_e"]), rest=(30.0, 0.35), cap=(20.0, 0.35),
                keeper=(20.0, 0.35), cloth=(120.0, 0.30))


def felt_inputs(eff):
    """{name: (K, e_eff)} -> {name: (K, e_input)} for the Dyn model."""
    cache = {}
    out = {}
    for k, (K, e) in eff.items():
        key = round(e, 4)
        if key not in cache:
            cache[key] = e_input(e)
        out[k] = (K, cache[key])
    return out


FELT = felt_inputs(FELT_EFF)


def static_set(KE, F):
    """static compression (mm) of a felt contact under force F (N)."""
    return (max(F, 0.0) / KE[0]) ** (2.0 / 3.0)


def sat(x):
    return -1.0 if x < -1.0 else (1.0 if x > 1.0 else x)


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]




# ============================================================================ r4 up-stop pad (flat foam pad on the steel top)
_trapz = getattr(np, "trapezoid", None) or np.trapz


def foam_sigma(eps, E, eps_D):
    """foam law (MPa): linear-elastic plateau stiffening to densification at eps_D."""
    e = np.minimum(eps, 0.97 * eps_D)
    return E * e / (1.0 - e / eps_D)


class PadTable:
    """r4 up-stop (U3): the exposed steel top of the lever meets a flat low-rebound pad (microcellular urethane +
    1T felt face, thickness h, width w) whose face is a line PARALLEL to the steel top at the truly settled 1 N
    held-bottom lever angle b_face, offset by `gap` along the face normal (gap < 0: the lever meets its pad before
    the key meets its front felt).  The pad covers world y pad_y along the face.  Tabulated against the lever angle:
    d = largest penetration (mm), F_el = normal force (N), u_c = centroid along the face.  The force acts on the lever
    along -n at the centroid (on the face) and on the pad bar / top plate along +n."""

    def __init__(self, A, b_face, gap, E=None, h=None, w=None, pad_y=None, eps_D=None, e_eff=None, n=180):
        P = A.P
        self.A, self.P = A, P
        self.E = P["pad_E"] if E is None else E
        self.h = P["pad_h"] if h is None else h
        self.w = P["pad_w"] if w is None else w
        self.pad_y = P["pad_y"] if pad_y is None else pad_y
        self.eps_D = P["pad_epsD"] if eps_D is None else eps_D
        self.e_eff = P["pad_e"] if e_eff is None else e_eff
        self.b_face, self.gap = b_face, gap
        self.top_l = steel_top_pts(P)
        cb, sb = math.cos(b_face), math.sin(b_face)
        self.t = (cb, -sb)                       # face tangent (toward +y)
        self.n = (sb, cb)                        # face normal (into the pad: up and slightly back)
        yc = 0.5 * (self.pad_y[0] + self.pad_y[1])
        pw = self.world_top(b_face)
        zc = float(np.interp(yc, pw[:, 0], pw[:, 1]))
        self.ref = (yc + gap * self.n[0], zc + gap * self.n[1])
        self.u0 = (self.pad_y[0] - yc) / cb
        self.u1 = (self.pad_y[1] - yc) / cb
        self.us = np.linspace(self.u0, self.u1, 97)
        # first contact angle
        lo, hi = b_face - 0.25, b_face + 0.25
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.pen(mid).max() > 0:
                hi = mid
            else:
                lo = mid
        self.b0 = hi
        bs, ds, Fs, ucs = [self.b0], [0.0], [0.0], [0.0]
        for bb in np.linspace(self.b0, self.b0 + math.radians(10.0), n)[1:]:
            pen = self.pen(bb)
            d = float(pen.max())
            sig = foam_sigma(pen / self.h, self.E, self.eps_D)
            F = float(_trapz(sig, self.us) * self.w)
            uc = float(_trapz(sig * self.us, self.us) * self.w / F) if F > 0 else 0.0
            bs.append(bb); ds.append(d); Fs.append(F); ucs.append(uc)
        self.bs, self.ds, self.Fs, self.ucs = map(np.array, (bs, ds, Fs, ucs))
        L = A.L
        # torque arm of a unit normal force at u (Dyn: Tl += -cross(P - L, F) with F = -n)
        self.arm = lambda u: cross2((self.ref[0] + u * self.t[0] - L[0], self.ref[1] + u * self.t[1] - L[1]), self.n)
        self.c = self.calibrate(self.e_eff)

    def world_top(self, b):
        return np.array([self.A.lp(tuple(p), b) for p in self.top_l])

    def pen(self, b):
        """penetration of the steel top into the (undeflected) pad over the pad's u grid."""
        pw = self.world_top(b)
        rel = pw - np.array(self.ref)
        u = rel @ np.array(self.t)
        v = rel @ np.array(self.n)
        o = np.argsort(u)
        vv = np.interp(self.us, u[o], v[o], left=-1e9, right=-1e9)
        return np.clip(vv, 0.0, None)

    def d_of_b(self, b):
        if b <= self.b0:
            return 0.0
        if b >= self.bs[-1]:
            k = (self.ds[-1] - self.ds[-2]) / (self.bs[-1] - self.bs[-2])
            return float(self.ds[-1] + k * (b - self.bs[-1]))
        return float(np.interp(b, self.bs, self.ds))

    def dd_db(self, b):
        i = int(np.clip(np.searchsorted(self.bs, b), 1, len(self.bs) - 1))
        return float((self.ds[i] - self.ds[i - 1]) / (self.bs[i] - self.bs[i - 1]))

    def F_el(self, d):
        """elastic normal force at largest penetration d (pad profile of the angle with that d)."""
        if d <= 0:
            return 0.0
        if d >= self.ds[-1]:
            k = (self.Fs[-1] - self.Fs[-2]) / (self.ds[-1] - self.ds[-2])
            return float(self.Fs[-1] + 5.0 * k * (d - self.ds[-1]))
        return float(np.interp(d, self.ds, self.Fs))

    def u_c(self, d):
        return float(np.interp(d, self.ds, self.ucs)) if d > 0 else 0.0

    def calibrate(self, e_target, v_front=None):
        """damping coefficient c of F = F_el (1 + c/v0 * d') that gives the EFFECTIVE restitution e_target for the lever
        alone swinging into the pad on a rigid seat at its PLAY angular speed (key front 1.5 m/s)."""
        A = self.A
        v_front = self.P["v_play"] if v_front is None else v_front
        a_ = A.a_dip - 1e-4
        jj = A.j(a_)[0]
        w0 = jj * v_front / (A.K[0] - A.front[0])

        def e_of(c):
            b, wb = self.b0, w0
            on, chi = False, 0.0
            dt = 0.002
            for _ in range(200000):
                d = self.d_of_b(b)
                if d <= 0 and on:
                    return -wb / w0
                ddot = self.dd_db(b) * wb
                if d > 0 and not on:
                    on, chi = True, c / max(abs(ddot), V0_FLOOR)
                F = max(0.0, self.F_el(d) * (1.0 + chi * ddot)) if d > 0 else 0.0
                T = F * self.arm(self.u_c(d))
                wb += T / A.IL * dt
                b += wb * dt
            return 0.0
        lo, hi = 1e-3, 400.0
        for _ in range(40):
            mid = math.sqrt(lo * hi)
            if e_of(mid) > e_target:
                lo = mid
            else:
                hi = mid
        self.e_check = e_of(math.sqrt(lo * hi))
        return math.sqrt(lo * hi)


class PadFace:
    """r4.2: the face geometry of PadTable (ref, t, n) without the force table - used for the end-part keys' own pad
    faces (face parallel to the key's own settled 1 N bottom, design gap), i.e. their wedges."""

    def __init__(self, A, b_face, gap):
        P = A.P
        cb, sb = math.cos(b_face), math.sin(b_face)
        self.t, self.n = (cb, -sb), (sb, cb)
        yc = 0.5 * (P["pad_y"][0] + P["pad_y"][1])
        pw = np.array([A.lp(tuple(p), b_face) for p in steel_top_pts(P)])
        zc = float(np.interp(yc, pw[:, 0], pw[:, 1]))
        self.ref = (yc + gap * self.n[0], zc + gap * self.n[1])
        self.b_face, self.gap = b_face, gap


class PadState:
    """per-run contact state of one pad in series with a massless linear seat (pad bar + top plate + fins)."""

    def __init__(self, tab, k_seat=None, c=None, vf=None):
        self.T = tab
        self.k = tab.P["seat_k"] if k_seat is None else k_seat
        self.c = tab.c if c is None else c
        self.vf = V0_FLOOR if vf is None else vf
        self.on, self.chi, self.u = False, 0.0, 0.0
        self.comp, self.seat = 0.0, 0.0

    def fpad(self, d, ddot):
        if d <= 0:
            return 0.0
        return max(0.0, self.T.F_el(d) * (1.0 + self.chi * ddot))

    def step(self, b, wb, dt):
        """returns (F, point on the face, normal) for the lever at angle b, rate wb."""
        T = self.T
        d = T.d_of_b(b)
        if d <= 0.0:
            self.on, self.u, self.comp = False, 0.0, 0.0
            return 0.0, None, None
        ddot = T.dd_db(b) * wb
        if not self.on:
            self.on = True
            self.chi = self.c / max(abs(ddot), self.vf)
        u0 = self.u
        if self.k is None or self.k <= 0 or self.k > 1e8:
            F = self.fpad(d, ddot)
            self.u = 0.0
        else:
            def g(u):
                return self.fpad(d - u, ddot - (u - u0) / dt) - self.k * u
            if g(0.0) <= 0.0:
                self.u = 0.0
            else:
                lo, hi = 0.0, d
                for _ in range(36):
                    mid = 0.5 * (lo + hi)
                    if g(mid) > 0:
                        lo = mid
                    else:
                        hi = mid
                self.u = 0.5 * (lo + hi)
            F = self.fpad(d - self.u, ddot - (self.u - u0) / dt)
        self.comp = d - self.u
        self.seat = self.u
        uc = T.u_c(d - self.u)
        pt = (T.ref[0] + uc * T.t[0], T.ref[1] + uc * T.t[1])
        return F, pt, T.n
class Dyn:
    TRACK_STEEL = False
    """4-DOF model: key = free planar body (y, z, theta) on the fixed rod through the cloth-lined snap notch (arc
    +-111.5 deg with lips), keeper hook above the crossbar, front felt, rest felt on the rear shelf, capstan (steel
    dome R3.3) on the lever felt; lever = 1 DOF on its rod with the torsion assist spring; r4: the steel top vs the
    flat foam pad (PadTable) in series with the pad seat (seat_k); Coulomb friction at the notch, lever rod, capstan
    and guide.  pad=None: no up-stop (used to find the settled bottom)."""

    def __init__(self, A, z_shelf, pad=None, felt=None, fmul=1.0, gvec=(0.0, -1.0), mu_lip=None, seat_k=None, vf=None, track_steel=None):
        self.A, self.P = A, A.P
        # r4.4: track the carrier -> steel interface forces (steel retention by the snap lips); None = Dyn.TRACK_STEEL
        self.track_steel = Dyn.TRACK_STEEL if track_steel is None else track_steel
        self.pad = pad
        self.seat_k = A.P["seat_k"] if seat_k is None else seat_k
        self.vf = V0_FLOOR if vf is None else vf
        self.felt = dict(FELT) if felt is None else felt
        self.z_shelf = z_shelf
        self.fmul = fmul
        self.g = gvec
        self.mu_lip = A.P["mu_kp"] * fmul if mu_lip is None else mu_lip
        P = self.P
        self.Rn = P["notch_R"] - P["cloth"]
        self.r_rod = P["rod_k"] / 2
        self.arc_half = math.acos(P["block_lift"] / self.Rn)
        self.z_ff = [A.kp(p, A.a_dip)[1] for p in A.stop_pts]      # felt top touches at the dip
        self.z_keep = P["key_bot"] + P["crossbar_t"] + P["keeper_gap"]
        self.Ic = A.Ik - A.mk * ((A.ck[0] - A.K[0]) ** 2 + (A.ck[1] - A.K[1]) ** 2)
        sa = math.sin(self.arc_half)
        ca = math.cos(self.arc_half)
        self.lips = [(A.K[0] - self.Rn * sa, A.K[1] + self.Rn * ca), (A.K[0] + self.Rn * sa, A.K[1] + self.Rn * ca)]

    def run(self, t_end, dt=0.004, finger=None, state=None, record=False, rec_every=25, stop_when=None):
        A, P = self.A, self.P
        fe = self.felt
        mk, Ic, IL, mL = A.mk, self.Ic, A.IL, A.mL
        gy, gz = self.g[0] * G, self.g[1] * G
        if state is None:
            th, b = 0.0, A.solve_b(0.0)
            c = A.ck
            vc, w, wb = (0.0, 0.0), 0.0, 0.0
        else:
            th, b, c, vc, w, wb = state
        vf = self.vf
        f_front = [Felt(fe["front_b"] if A.black else fe["front"], vf) for _ in A.stop_pts]
        f_rest = [Felt(fe["rest"], vf) for _ in A.rest_pts]
        f_cap = Felt(fe["cap"], vf)
        f_up = PadState(self.pad, self.seat_k, vf=vf) if self.pad is not None else None
        f_keep = [Felt(fe["keeper"], vf) for _ in A.keeper_pts]
        f_rod = Felt(fe["cloth"], vf)
        f_lip = [Felt(fe["cloth"], vf) for _ in self.lips]
        self.f_tab = Felt((200.0, 0.3), vf)
        fm = self.fmul
        mu_k, mu_L, mu_c, fg = P["mu_kp"] * fm, P["mu_Lp"] * fm, P["mu_c"] * fm, P["guide_drag"] * fm
        R = A.R
        ck0 = A.ck
        mag_rest = A.mag[1]
        mag_bot = A.kp(A.mag, A.a_dip)[1]
        ev = dict(t40=None, t100=None, lift_max=0.0, sep_max=0.0, land_v=0.0, up_peak=0.0, up_hits=0,
                  front_peak=0.0, rest_peak=0.0, cap_peak=0.0, keep_peak=0.0, keep_gap_min=1e9, rod_peak=0.0,
                  RL_peak=0.0, RL_up_peak=0.0, t_bottom=None, v_bottom=None, b_max=-1.0, pen_up_max=0.0,
                  front_min_after_bottom=None, lip_top_bottom=None, ghost_rise=0.0, ghost_frac=0.0, hist=[],
                  th_max=-1.0, front_z_min=1e9, b_min=1.0, b_min_rel=1.0, ghost_t40=None, ghost_reland=None,
                  th_min_rel=1.0, lip_peak=0.0, lip_pull=0.0, t50=None, ghost_t_arm=None, ghost_v_desc=0.0,
                  seat_max=0.0, pad_comp_max=0.0, v_front_bottom=None, kz_ff=1e9, ky_ff=0.0, kz_over=1e9, ky_over=0.0,
                  frac_tr=[], frac_end=None, mag_travel=mag_rest - mag_bot)
        rKy_, rKz_ = self.A.K[0] - self.A.ck[0], self.A.K[1] - self.A.ck[1]     # r4.4 fix 2: K point of the key frame
        th_lo_ = 0.8 * self.A.a_dip
        rearm = P.get("rearm", 0.40)
        trk = steel_zones(P) if self.track_steel else None
        if trk is not None:
            trk["r43"] = steel_zones(P, segs=((150.0, P["lip_gap_y"][0]), (P["lip_gap_y"][1], P["lip_end_y"])))   # r4.1-r4.3 lips (comparison)
        if trk is not None:
            ev["steel"] = dict(T_front=0.0, T_rear=0.0, B=0.0, V_min=0.0, V_max=0.0, M_min=0.0, M_max=0.0)
        wbd_prev = 0.0
        t = 0.0
        released = finger is None
        t_rel = 0.0 if released else None
        was_up = False
        sep = False
        pen_rod_static = None
        n = int(t_end / dt)
        for i in range(n):
            Ff = finger(t, ev) if finger else 0.0
            if not released and Ff == 0.0 and t > 0:
                released, t_rel = True, t
            cth, sth = math.cos(th), math.sin(th)

            def kw(p):
                rx, rz = p[0] - ck0[0], p[1] - ck0[1]
                rr = (rx * cth - rz * sth, rx * sth + rz * cth)
                return (c[0] + rr[0], c[1] + rr[1]), (vc[0] - w * rr[1], vc[1] + w * rr[0])

            Fk = [mk * gy, mk * gz]
            Tk = 0.0
            rcL = A.lp(A.cL, b)
            Fl = [mL * gy, mL * gz]
            Tl = -cross2((rcL[0] - A.L[0], rcL[1] - A.L[1]), (mL * gy, mL * gz))

            def ak(Pp, F):
                nonlocal Tk
                Fk[0] += F[0]; Fk[1] += F[1]
                Tk += cross2((Pp[0] - c[0], Pp[1] - c[1]), F)

            def al(Pp, F):
                nonlocal Tl
                Fl[0] += F[0]; Fl[1] += F[1]
                Tl += -cross2((Pp[0] - A.L[0], Pp[1] - A.L[1]), F)
            # finger (vertical, down)
            if Ff:
                Pf, _ = kw(A.finger)
                ak(Pf, (0.0, -Ff))
            # ---- notch (cloth arc) on the fixed rod
            Nw, Vn = kw(A.K)
            d = (A.K[0] - Nw[0], A.K[1] - Nw[1])
            dist = math.hypot(d[0], d[1])
            upk = (-sth, cth)                           # key up axis in world
            comp_up = d[0] * upk[0] + d[1] * upk[1]
            Frod = 0.0
            if dist > 1e-9:
                u = (d[0] / dist, d[1] / dist)
                cosphi = u[0] * upk[0] + u[1] * upk[1]
                if cosphi >= math.cos(self.arc_half):
                    pen = dist + self.r_rod - self.Rn
                    Pc = (Nw[0] + self.Rn * u[0], Nw[1] + self.Rn * u[1])
                    # material velocity of the key at Pc
                    rP = (Pc[0] - c[0], Pc[1] - c[1])
                    Vk = (vc[0] - w * rP[1], vc[1] + w * rP[0])
                    pen_dot = -(Vk[0] * u[0] + Vk[1] * u[1])
                    Frod = f_rod.force(pen, pen_dot)
                    if Frod > 0:
                        ak(Pc, (Frod * u[0], Frod * u[1]))
                        tt = (-u[1], u[0])
                        vt = Vk[0] * tt[0] + Vk[1] * tt[1]
                        ff = -mu_k * Frod * sat(vt / 2e-4)
                        ak(Pc, (ff * tt[0], ff * tt[1]))
                else:
                    f_rod.force(-1.0, 0.0)
            lipF = 0.0
            lipV = 0.0
            for lp_, fl_ in zip(self.lips, f_lip):
                Pl, Vl = kw(lp_)
                e_ = (Pl[0] - A.K[0], Pl[1] - A.K[1])
                de = math.hypot(*e_)
                pen = self.r_rod - de
                if pen > 0:
                    ue = (e_[0] / de, e_[1] / de)
                    Fl_ = fl_.force(pen, -(Vl[0] * ue[0] + Vl[1] * ue[1]))
                    ak(Pl, (Fl_ * ue[0], Fl_ * ue[1]))
                    # Coulomb friction at the lip (cloth on the steel rod), same mu as the notch
                    tl = (-ue[1], ue[0])
                    vtl = Vl[0] * tl[0] + Vl[1] * tl[1]
                    fl_t = -self.mu_lip * Fl_ * sat(vtl / 2e-4)
                    ak(Pl, (fl_t * tl[0], fl_t * tl[1]))
                    Frod += Fl_
                    lipF = max(lipF, Fl_)
                    # pull-off load on the snap: lip force (normal + friction) holding the key DOWN along its up axis
                    lipV += -((Fl_ * ue[0] + fl_t * tl[0]) * upk[0] + (Fl_ * ue[1] + fl_t * tl[1]) * upk[1])
                else:
                    fl_.force(-1.0, 0.0)
            # ---- capstan dome on the lever felt plane
            Cw, _ = kw(A.C0)
            Q = A.lp(A.Q0, b)
            nrm = (-math.sin(b), -math.cos(b))
            tng = (math.cos(b), -math.sin(b))
            gap = (Cw[0] - Q[0]) * nrm[0] + (Cw[1] - Q[1]) * nrm[1] - R
            Pc = (Cw[0] - R * nrm[0], Cw[1] - R * nrm[1])
            rP = (Pc[0] - c[0], Pc[1] - c[1])
            Vk = (vc[0] - w * rP[1], vc[1] + w * rP[0])
            Vl = (wb * (Pc[1] - A.L[1]), -wb * (Pc[0] - A.L[0]))
            pen_dot = -((Vk[0] - Vl[0]) * nrm[0] + (Vk[1] - Vl[1]) * nrm[1])
            Nc = f_cap.force(-gap, pen_dot)
            if Nc > 0:
                ak(Pc, (Nc * nrm[0], Nc * nrm[1]))          # nrm points lever -> key (down)
                al(Pc, (-Nc * nrm[0], -Nc * nrm[1]))
                vs = (Vk[0] - Vl[0]) * tng[0] + (Vk[1] - Vl[1]) * tng[1]
                fr = mu_c * Nc * sat(vs / 2e-4)
                ak(Pc, (-fr * tng[0], -fr * tng[1]))
                al(Pc, (fr * tng[0], fr * tng[1]))
                if sep:
                    ev["land_v"] = max(ev["land_v"], abs(pen_dot))
                    sep = False
            elif gap > 1e-3 and t > 1.0:
                sep = True
                ev["sep_max"] = max(ev["sep_max"], gap)
            # ---- front down-stop felt
            ffr = 0.0
            for p_, fe_, zf in zip(A.stop_pts, f_front, self.z_ff):
                Pp, Vp = kw(p_)
                f_ = fe_.force(zf - Pp[1], -Vp[1])
                if f_:
                    ak(Pp, (0.0, f_)); ffr += f_
            # ---- rest felt on the rear shelf
            fre = 0.0
            for p_, fe_ in zip(A.rest_pts, f_rest):
                Pp, Vp = kw(p_)
                f_ = fe_.force(self.z_shelf - Pp[1], -Vp[1])
                if f_:
                    ak(Pp, (0.0, f_)); fre += f_
            # ---- keeper (crossbar top vs keeper felt 0.5 above)
            fk_ = 0.0
            kg = 1e9
            for p_, fe_ in zip(A.keeper_pts, f_keep):
                Pp, Vp = kw(p_)
                kg = min(kg, self.z_keep - Pp[1])
                f_ = fe_.force(Pp[1] - self.z_keep, Vp[1])
                if f_:
                    ak(Pp, (0.0, -f_)); fk_ += f_
            # ---- rear y-stop: crossbar rear face vs guide-tab front face (bare PETG, stiff)
            cb = P["b_crossbar_y"] if A.black else P["w_crossbar_y"]
            ytab = (P["b_tab_y"] if A.black else P["w_tab_y"])[0]
            Pt, Vt = kw((cb[1], P["key_bot"] + P["crossbar_t"] / 2))
            ft = self.f_tab.force(Pt[0] - ytab, Vt[0])
            if ft:
                ak(Pt, (-ft, 0.0))
            # ---- r4 up-stop: exposed steel top vs the flat foam pad (in series with the pad seat)
            fup = 0.0
            if f_up is not None:
                fup, Pu, nu = f_up.step(b, wb, dt)
                if fup:
                    al(Pu, (-fup * nu[0], -fup * nu[1]))
                    ev["pen_up_max"] = max(ev["pen_up_max"], f_up.comp)
                    ev["seat_max"] = max(ev["seat_max"], f_up.seat)
            # ---- r4 torsion assist spring (couple)
            if A.spring:
                Tl -= A.spring_T(b)
                Tl += -fm * A.spring_H(b) * sat(wb / 2e-5)      # r4.5 fix 2: coil-on-rod hysteresis (0 when captured)
            # ---- guide drag
            Pg, Vg = kw(A.guide)
            ak(Pg, (0.0, -fg * sat(Vg[1] / 2e-4)))
            # ---- lever rod friction (reaction from last step's acceleration)
            rc = (rcL[0] - A.L[0], rcL[1] - A.L[1])
            # CW angle b: tangential acceleration (rc_z, -rc_y) * wbd, centripetal -wb^2 rc
            acc = (wbd_prev * rc[1] - wb * wb * rc[0], -wbd_prev * rc[0] - wb * wb * rc[1])
            RLv = (mL * acc[0] - Fl[0], mL * acc[1] - Fl[1])
            RLm = math.hypot(*RLv)
            Tl += -mu_L * P["rod_L"] / 2 * RLm * sat(wb / 2e-5)
            # ---- integrate (semi-implicit Euler)
            vc = (vc[0] + Fk[0] / mk * dt, vc[1] + Fk[1] / mk * dt)
            w += Tk / Ic * dt
            wbd = Tl / IL
            if trk is not None:
                # r4.4: force / moment the carrier must put on the steel (capstan felt and pad act on the steel itself)
                cs_ = A.lp(trk["com"], b)
                rs_ = (cs_[0] - A.L[0], cs_[1] - A.L[1])
                as_ = (wbd * rs_[1] - wb * wb * rs_[0], -wbd * rs_[0] - wb * wb * rs_[1])
                Fe_ = [trk["m"] * gy, trk["m"] * gz]
                Me_ = 0.0
                if Nc > 0:
                    fc_ = (-Nc * nrm[0] + fr * tng[0], -Nc * nrm[1] + fr * tng[1])
                    Fe_[0] += fc_[0]; Fe_[1] += fc_[1]
                    Me_ += cross2((Pc[0] - cs_[0], Pc[1] - cs_[1]), fc_)
                if fup:
                    fu_ = (-fup * nu[0], -fup * nu[1])
                    Fe_[0] += fu_[0]; Fe_[1] += fu_[1]
                    Me_ += cross2((Pu[0] - cs_[0], Pu[1] - cs_[1]), fu_)
                Fcs_ = (trk["m"] * as_[0] - Fe_[0], trk["m"] * as_[1] - Fe_[1])
                Mcs_ = trk["I"] * (-wbd) - Me_
                V_ = Fcs_[0] * math.sin(b) + Fcs_[1] * math.cos(b)            # lever-frame z component (+ = up on the steel)
                zf_ = steel_zone_split(V_, Mcs_, trk)
                es_ = ev["steel"]
                es_["T_front"] = max(es_["T_front"], zf_[0]); es_["T_rear"] = max(es_["T_rear"], zf_[1]); es_["B"] = max(es_["B"], zf_[2])
                zo_ = steel_zone_split(V_, Mcs_, trk["r43"])
                es_["T_front_r43"] = max(es_.get("T_front_r43", 0.0), zo_[0]); es_["T_rear_r43"] = max(es_.get("T_rear_r43", 0.0), zo_[1])
                es_["B_r43"] = max(es_.get("B_r43", 0.0), zo_[2])
                es_["V_min"] = min(es_["V_min"], V_); es_["V_max"] = max(es_["V_max"], V_)
                es_["M_min"] = min(es_["M_min"], Mcs_); es_["M_max"] = max(es_["M_max"], Mcs_)
            wb += wbd * dt
            wbd_prev = wbd
            c = (c[0] + vc[0] * dt, c[1] + vc[1] * dt)
            th += w * dt
            b += wb * dt
            t += dt
            # ---- events
            pen_st = comp_up - (self.Rn - self.r_rod)
            if pen_rod_static is None and t > 0.5:
                pen_rod_static = pen_st if state is None else state_pen(state, self)
            ev["cap_peak"] = max(ev["cap_peak"], Nc)
            ev["front_peak"] = max(ev["front_peak"], ffr)
            ev["rest_peak"] = max(ev["rest_peak"], fre)
            ev["keep_peak"] = max(ev["keep_peak"], fk_)
            ev["keep_gap_min"] = min(ev["keep_gap_min"], kg)
            ev["rod_peak"] = max(ev["rod_peak"], Frod)
            ev["lip_peak"] = max(ev["lip_peak"], lipF)
            ev["lip_pull"] = max(ev["lip_pull"], lipV)
            ev["RL_peak"] = max(ev["RL_peak"], RLm)
            if RLv[1] < 0:
                ev["RL_up_peak"] = max(ev["RL_up_peak"], -RLv[1])
            ev["b_max"] = max(ev["b_max"], b)
            ev["b_min"] = min(ev["b_min"], b)
            ev["th_max"] = max(ev["th_max"], th)
            # r4.4 fix 2 (verifier geometry major 3): where the key's rod point is (notch seated + sinking into its cloth)
            # while the key is near / past its bottom, and while it overshoots above rest after a release
            if th > th_lo_ or (released and th < -0.00087):
                c2_, s2_ = math.cos(th), math.sin(th)
                kzy_ = c[0] + rKy_ * c2_ - rKz_ * s2_ - self.A.K[0]
                kzz_ = c[1] + rKy_ * s2_ + rKz_ * c2_ - self.A.K[1]
                if th > th_lo_ and kzz_ < ev["kz_ff"]:
                    ev["kz_ff"], ev["ky_ff"] = kzz_, kzy_
                if released and th < -0.00087 and kzz_ < ev["kz_over"]:
                    ev["kz_over"], ev["ky_over"] = kzz_, kzy_
            if released:
                ev["b_min_rel"] = min(ev["b_min_rel"], b)
                ev["th_min_rel"] = min(ev["th_min_rel"], th)
            if fup > 0:
                ev["up_peak"] = max(ev["up_peak"], fup)
                if not was_up:
                    ev["up_hits"] += 1
                was_up = True
            else:
                was_up = False
            if t > 2.0 and pen_rod_static is not None:
                ev["lift_max"] = max(ev["lift_max"], pen_rod_static - pen_st)
            mz = kw(A.mag)[0][1]
            frac = (mz - mag_bot) / (mag_rest - mag_bot)
            if ev["t_bottom"] is not None and i % 2500 == 0:
                ev["frac_tr"].append((t, frac))          # r4.5 circuit 2nd: magnet position every 10 ms after the note-on
            if finger and ev["t_bottom"] is None and ffr > 0:
                ev["t_bottom"] = t
                ev["v_bottom"] = abs(kw(A.finger)[1][1])
                ev["v_front_bottom"] = abs(kw(A.front)[1][1])
            if i % 5 == 0:
                ev["front_z_min"] = min(ev["front_z_min"], kw(A.front)[0][1])
            if ev["t_bottom"] is not None and not released:
                lz = kw(A.front)[0][1]
                if ev["lip_top_bottom"] is None or lz < ev["lip_top_bottom"]:
                    ev["lip_top_bottom"] = lz
                if t > ev["t_bottom"] + 3.0:
                    ev["ghost_rise"] = max(ev["ghost_rise"], lz - ev["lip_top_bottom"])
                    ev["ghost_frac"] = max(ev["ghost_frac"], frac)
                    if ev["ghost_t40"] is None and frac >= 0.40:
                        ev["ghost_t40"] = t - ev["t_bottom"]
                    if ev["ghost_t40"] is not None and ev["ghost_reland"] is None and ffr > 0:
                        ev["ghost_reland"] = t - ev["t_bottom"]
                    if ev["ghost_t_arm"] is None and frac >= rearm:
                        ev["ghost_t_arm"] = t - ev["t_bottom"]
                    if frac > 0.05 and ffr == 0.0:
                        # finger-point downward speed on the way back down after the key re-armed (firmware ghost filter)
                        ev["ghost_v_desc"] = max(ev["ghost_v_desc"], -kw(A.finger)[1][1])
            if released:
                tr = t - t_rel
                if ev["t40"] is None and frac >= 0.40:
                    ev["t40"] = tr
                if ev["t50"] is None and frac >= 0.50:
                    ev["t50"] = tr
                if ev["t100"] is None and frac >= 1.0:
                    ev["t100"] = tr
            if record and i % rec_every == 0:
                ev["hist"].append((t, th, b, frac, Nc, gap, Frod, fre, fup, ffr, pen_rod_static - pen_st
                                   if pen_rod_static is not None else 0.0, kg, vc[0], vc[1], w, ft, Ff))
            if stop_when and stop_when(t, ev):
                break
        ev["state"] = (th, b, c, vc, w, wb)
        ev["frac_end"] = frac
        ev["t_run"] = t
        ev["pen_rod_end"] = pen_st
        ev["pen_rod_static"] = pen_rod_static
        return ev


def steel_zones(P, segs=None):
    """r4.4: the steel block (lever frame) and the carrier zones that hold it: top-front = the solid cap over the steel
    front (y_steel_front .. +3, full width) + the front top snap lips, top-rear = the rear top snap lips (both push the
    steel DOWN), bottom = the bottom snap lips (push it UP).  y of each zone = its area centroid."""
    ms = P["steel_w"] * P["steel_h"] * P["steel_len"] * RHO_ST
    sf, sr = P["y_steel_front"], P["y_steel_front"] + P["steel_len"]
    com = ((sf + sr) / 2, P["z_sb"] + P["steel_h"] / 2)
    Is = ms * (P["steel_len"] ** 2 + P["steel_h"] ** 2) / 12
    lo = P["lip_over"]
    segs = sorted(P["lip_segs"] if segs is None else segs)
    fr_ = [q for q in segs if q[0] < (sf + sr) / 2]
    rr_ = [q for q in segs if q[0] >= (sf + sr) / 2]
    # front: cap (sf .. sf+3, width steel_w) + lips beyond the cap (2 x lip_over)
    a_cap = 3.0 * P["steel_w"]
    parts = [((sf + sf + 3.0) / 2, a_cap)] + [((max(y0, sf + 3.0) + y1) / 2, 2 * lo * max(0.0, y1 - max(y0, sf + 3.0))) for y0, y1 in fr_]
    yf = sum(y * a for y, a in parts) / sum(a for y, a in parts)
    yr = sum((y0 + y1) / 2 * (y1 - y0) for y0, y1 in rr_) / sum(y1 - y0 for y0, y1 in rr_)
    yb = (P["lip_front_y"] + P["felt_c_y"][0]) / 2
    return dict(m=ms, I=Is, com=com, yf=yf, yr=yr, yb=yb, L_rear=sum(y1 - y0 for y0, y1 in rr_),
                L_front=sum(y1 - max(y0, sf + 3.0) for y0, y1 in fr_), L_bottom=P["felt_c_y"][0] - P["lip_front_y"])


def steel_zone_split(V, M, z):
    """r4.4: split the carrier -> steel resultant (V up, M CCW about the steel COM, lever frame) into the three unilateral
    zones (T_front, T_rear >= 0 push down, B >= 0 pushes up): the two-zone solution with all forces >= 0 (smallest peak)."""
    yc = z["com"][0]
    df, dr, db = z["yf"] - yc, z["yr"] - yc, z["yb"] - yc
    best = None
    # (T_f, T_r): -T_f - T_r = V ; -T_f df - T_r dr = M
    for sol in ((lambda: _solve2(-1.0, -1.0, -df, -dr, V, M), (0, 1)), (lambda: _solve2(-1.0, 1.0, -df, db, V, M), (0, 2)),
                (lambda: _solve2(-1.0, 1.0, -dr, db, V, M), (1, 2))):
        x = sol[0]()
        if x is None or x[0] < -1e-9 or x[1] < -1e-9:
            continue
        out = [0.0, 0.0, 0.0]
        out[sol[1][0]], out[sol[1][1]] = max(0.0, x[0]), max(0.0, x[1])
        if best is None or max(out) < max(best):
            best = out
    return best if best is not None else [0.0, 0.0, 0.0]


def _solve2(a11, a12, a21, a22, b1, b2):
    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-12:
        return None
    return ((b1 * a22 - a12 * b2) / det, (a11 * b2 - a21 * b1) / det)


def state_pen(state, D):
    """rod penetration of a given state (used as the 'seated' reference when a run starts from a state)."""
    A = D.A
    th, b, c, vc, w, wb = state
    rx, rz = A.K[0] - A.ck[0], A.K[1] - A.ck[1]
    Nw = (c[0] + rx * math.cos(th) - rz * math.sin(th), c[1] + rx * math.sin(th) + rz * math.cos(th))
    d = (A.K[0] - Nw[0], A.K[1] - Nw[1])
    upk = (-math.sin(th), math.cos(th))
    return d[0] * upk[0] + d[1] * upk[1] - (D.Rn - D.r_rod)


# ============================================================================ design solve
DW_TARGET = 51.0        # g at the finger point (white y13, black front + 10), friction included


def dw_target(P, black):
    return P.get("dw_target_b", DW_TARGET) if black else P.get("dw_target_w", DW_TARGET)


def solve_cap_y(P, kd, x_lever, target=None, zc=None):
    """capstan y giving DW = target (statics at the start of motion); default target per colour (P dw_target_w/_b)."""
    target = dw_target(P, kd["black"]) if target is None else target
    P2 = dict(P)
    if zc is not None:
        P2["z_c"] = zc
    lo, hi = 170.0, 194.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if Action(P2, kd, mid, x_lever).statics(1e-4)["DW"] < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def slow_dip_cap_top(A):
    """cap top z at a slow full dip including the static set of the capstan felt (rigid kinematics
    rotated back by the felt compression under the quasi-static capstan force)."""
    s = A.statics(A.a_dip - 1e-5)
    d = static_set(FELT["cap"], s["N"])
    _, _, _, n, t, Pc = A.geo(A.a_dip, A.b_dip)
    arm = abs(Pc[0] - A.L[0])
    db = d / arm
    return A.cap_top(A.b_dip - db), A.cap_top(A.b_dip), d


def held_bottom(A, z_shelf, F=1.0, felt=None, pad=None, t_ramp=120.0, t_hold=1400.0, w_tol=1e-6, seat_k=None):
    """TRULY settled 4-DOF state with the finger holding F at the bottom after a slow ramp (r3 finding #1: the r3
    routine read the state at 320 ms while the lever still turned at 0.58 rad/s): hold t_hold ms and keep going in
    400 ms steps until the lever speed |w| < w_tol rad/ms.  Up-stop absent unless a PadTable is given.
    Returns (state, cap top z, key front top z, |w| at the end)."""
    D = Dyn(A, z_shelf, pad=pad, felt=felt, seat_k=seat_k)
    st0 = D.run(200.0)["state"]
    ev = D.run(t_ramp + t_hold, state=st0, finger=lambda t, ev_: F * min(1.0, t / t_ramp))
    st = ev["state"]
    for _ in range(6):
        if abs(st[5]) < w_tol and abs(st[4]) < w_tol:
            break
        st = D.run(400.0, state=st, finger=lambda t, ev_: F)["state"]
    return st, A.cap_top(st[1]), key_point_world(A, st, A.front)[1], max(abs(st[5]), abs(st[4]))


def solve_design(P, target=None):
    keys, lay = module_layout(P)
    caps = {}
    acts = {}
    for nm in ORDER:
        kd = keys[nm]
        yc = solve_cap_y(P, kd, lay["levers"][nm], target)
        caps[nm] = yc
        acts[nm] = Action(P, kd, yc, lay["levers"][nm])
    tops = {nm: slow_dip_cap_top(acts[nm]) for nm in ORDER}
    return keys, lay, caps, acts, tops


# ============================================================================ scenarios
def key_point_world(A, state, p):
    th, b, c, vc, w, wb = state
    rx, rz = p[0] - A.ck[0], p[1] - A.ck[1]
    return (c[0] + rx * math.cos(th) - rz * math.sin(th), c[1] + rx * math.sin(th) + rz * math.cos(th))


def calibrate_shelf(A, z_us=None, z0=20.0, felt=None):
    """shelf top z so that the settled key front top sits at its nominal height (43.5 / 55.5)."""
    z = z0
    for _ in range(4):
        D = Dyn(A, z, pad=None, felt=felt)
        st = D.run(150.0)["state"]
        err = key_point_world(A, st, A.front)[1] - A.front[1]
        # front rises 1 : (y_rest - y_front)/(y_rest - y_K) per mm of shelf rise
        yr = sum(A.P["rest_pad_y"]) / 2
        z += err * (yr - A.K[0]) / (A.K[0] - A.front[0])
    D = Dyn(A, z, pad=None, felt=felt)
    st = D.run(150.0)["state"]
    return round(z, 3), st


def settle(D):
    return D.run(150.0)["state"]


def press(D, F, state, hold=150.0, after=200.0, record=False, dt=0.004):
    return D.run(hold + after, dt=dt, state=state, finger=lambda t, ev: F if t < hold else 0.0, record=record)


def release_from_bottom(D, state, F=1.0, hold=1200.0):
    """r4: hold F for 1.2 s (truly settled, r3 finding #1) and let go; t40 / t50 / t100 from the release."""
    ev = press(D, F, state, hold=hold, after=200.0)
    return ev


def strike_state(A, state, v0):
    """speed-defined stroke: key (rotating about its rod) and lever (on the capstan) co-moving, the finger
    point going down at v0 (m/s = mm/ms), starting from the settled rest state."""
    th, b, c, vc, w, wb = state
    r = abs(A.dkz(A.finger, th))
    wk = v0 / r
    rc = (c[0] - A.K[0], c[1] - A.K[1])
    vck = (-wk * rc[1], wk * rc[0])
    return (th, b, c, vck, wk, A.j(th)[0] * wk)


def strike(D, state, v0, F_follow=3.0, F_hold=None, t_follow=2.0, t_end=250.0, record=False, rec_every=25):
    """struck note: co-moving start at v0; the finger keeps F_follow until t_follow ms after the key reaches
    its front felt, then either holds F_hold (ghost check) or lets go (F_hold None -> release)."""
    st = strike_state(D.A, state, v0)

    def fin(t, ev):
        if ev["t_bottom"] is None or t < ev["t_bottom"] + t_follow:
            return F_follow
        if F_hold is None:
            return 0.0
        return F_hold
    ev = D.run(t_end, state=st, finger=fin, record=record, rec_every=rec_every)
    # r4.5 circuit 2nd cross-check (item 9): a held note whose key re-armed is run on to t_bottom + ghost_long so that the
    # ghost re-press (if it comes) lands inside the run: ghost_reland, the float after the re-arm, the creep at the end
    tl = D.P.get("ghost_long")
    if (tl and F_hold is not None and not record and ev["t_bottom"] is not None and ev["ghost_frac"] >= D.P.get("rearm", 0.40)
            and t_end < ev["t_bottom"] + tl):
        ev = D.run(ev["t_bottom"] + tl, state=st, finger=fin)
        ev["ghost_long"] = True
    ghost_tail(ev)
    return ev


def ghost_tail(ev, tail=200.0, move=0.01):
    """r4.5 circuit 2nd: from the 10 ms magnet track after the note-on - ghost_settle = the last time (ms after t_bottom) the
    magnet moved more than `move` of its travel in 10 ms (the key has stopped at its float point after that: any later
    motion is the finger's or the model creep), ghost_creep = the magnet's mean downward speed (m/s) over the last `tail` ms,
    ghost_land_est = the extrapolated time (ms after t_bottom) at which that creep would bring it to the bottom."""
    tr = ev.get("frac_tr") or []
    ev["ghost_settle"], ev["ghost_creep"], ev["ghost_land_est"] = None, None, None
    if len(tr) < 3 or ev.get("t_bottom") is None:
        return ev
    tb = ev["t_bottom"]
    st_ = None
    for (t0, f0), (t1, f1) in zip(tr[:-1], tr[1:]):
        if abs(f1 - f0) > move:
            st_ = t1 - tb
    ev["ghost_settle"] = st_
    t_e, f_e = tr[-1]
    k_ = max(i_ for i_, q_ in enumerate(tr) if q_[0] <= t_e - tail + 1e-6) if tr[0][0] <= t_e - tail + 1e-6 else 0
    t_a, f_a = tr[k_]
    if t_e - t_a > 1e-6:
        rate = (f_a - f_e) / (t_e - t_a)                      # travel fraction per ms, + = going down
        ev["ghost_creep"] = rate * ev["mag_travel"]           # mm/ms = m/s at the magnet
        if rate > 1e-9 and f_e > 0:
            ev["ghost_land_est"] = t_e - tb + f_e / rate
    return ev


def ghost(D, state, F_hit, F_hold=2.0, t_hit_extra=2.0, hold=150.0):
    """ff/fff stroke, then the finger relaxes to F_hold and stays: key-front rise after the bottom."""
    def fin(t, ev):
        if ev["t_bottom"] is None or t < ev["t_bottom"] + t_hit_extra:
            return F_hit
        return F_hold if t < 400.0 else 0.0
    ev = D.run(hold + 60.0, state=state, finger=fin)
    return ev




def front_ratio(A):
    """key-front speed / finger-point speed near the bottom (rigid rotation about the rod)."""
    a = A.a_dip
    return abs(A.dkz(A.front, a)) / abs(A.dkz(A.finger, a))


def v0_for_front(D, st, v_front, F_follow=3.0):
    """finger-start speed v0 whose KEY-FRONT speed at the front-felt contact is v_front (m/s).  r4 load envelope:
    measured key speeds are the peak speed of the key front, which the model reaches at the felt contact."""
    A = D.A
    rr_ = front_ratio(A)
    lo, hi = 0.05, 1.3 * v_front / rr_
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        s0 = strike_state(A, st, mid)
        ev = D.run(80.0, state=s0, finger=lambda t, e: F_follow, stop_when=lambda t, e: e["t_bottom"] is not None)
        vf = ev["v_front_bottom"] or 0.0
        if vf < v_front:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
# ============================================================================ geometry checks helpers
def removal_geometry(A, P):
    """r4 single-key removal, tool-free (RET-7 adapted to the top plate): lift the curtain strip, slide out that bay's
    pad bar, lift the own lever by its fingernail tab to the hold angle (one hand), and with the other hand's fingernail
    pull up the 1.0 mm rear lip of the key top (y146-147).  The key first pivots on its tail rest pad (notch leaves the
    rod, front rises) until the crossbar meets the keeper; pulling on, it pivots on the keeper until the REAR notch lip
    clears the rod top by removal_lip_clear; the capstan then needs the lever at >= lever_angle_needed; the key slides
    3 mm forward, tilts and comes out.  Pull forces are given with the lever held by hand (r4 procedure) and resting on
    the capstan (no hand)."""
    zb = P["K"][1] + P["block_lift"]
    h = math.sqrt(P["notch_R"] ** 2 - P["block_lift"] ** 2)
    lip = (P["K"][0] + h, zb)
    pad = (sum(P["rest_pad_y"]) / 2, P["beam_z"][0] - P["rest_felt"] - P["rest_shim"])
    kp_ = (sum(p[0] for p in A.keeper_pts) / 2, A.keeper_pts[0][1])
    # phase 1: rotate about the pad (front up) until the crossbar top reaches the keeper
    ph1 = P["keeper_gap"] / (pad[0] - kp_[0])
    lip1 = rot(lip, pad, -ph1)
    kp1 = rot(kp_, pad, -ph1)
    need_total = P["K"][1] + P["rod_k"] / 2 + P.get("removal_lip_clear", 0.3) - zb
    need2 = need_total - (lip1[1] - lip[1])
    ph2 = need2 / (lip1[0] - kp1[0])
    C = rot(rot(A.C0, pad, -ph1), kp1, ph2)
    cap_rise = C[1] - A.C0[1]
    b = 0.0
    while True:                         # lever angle it rides up to (felt resting on the raised capstan)
        b += 0.0005
        Q = A.lp(A.Q0, b)
        n = (-math.sin(b), -math.cos(b))
        gap = (C[0] - Q[0]) * n[0] + (C[1] - Q[1]) * n[1] - A.R
        if gap > 0.0 or b > 1.2:
            break
    # pull force at the rear lip (y146.5): phase 1 about the pad, phase 2 about the keeper (lever weight N0)
    s = A.statics(1e-4)
    yp = (P["y_body_end"] + P["y_skin_end"]) / 2
    F1 = (A.mk * G * (pad[0] - A.ck[0]) + s["N"] * (pad[0] - A.y_cap)) / (pad[0] - yp)
    F2 = (A.mk * G * (A.ck[0] - kp_[0]) + s["N"] * (A.y_cap - kp_[0])) / (yp - kp_[0])
    F1h = A.mk * G * (pad[0] - A.ck[0]) / (pad[0] - yp)          # lever held up by hand: key weight only
    F2h = A.mk * G * (A.ck[0] - kp_[0]) / (yp - kp_[0])
    # r3 snap notch: the lips engage after ~0.1 of lift (phase 1) and let go when they pass the rod equator (phase 2)
    snap1 = P.get("snap_F", 0.0) * (pad[0] - P["K"][0]) / (pad[0] - yp)
    snap2 = P.get("snap_F", 0.0) * (P["K"][0] - kp_[0]) / (yp - kp_[0])
    F1s, F2s = F1 + snap1, F2 + snap2
    snap_hi = 4.3 / max(P.get("snap_F", 1.0), 1e-9)          # R2.50 coupon (tightest) -> 4.3 N pull-off
    corner = (P["y_steel_rear"], P["z_st"])
    bb = 0.0
    while A.lp(corner, bb)[0] < P["rear_wall"][0] and bb < 1.2:
        bb += 0.0005
    # balance pin: block bottom at the pin after the lift vs the pin top (must clear before the 3 mm slide)
    pin_pt = (P["pin_y"], P.get("block_step_z", zb))
    pin_lift = rot(rot(pin_pt, pad, -ph1), kp1, ph2)[1] - zb
    # fingernail force on the lever tab to hold the lever at the needed angle (lever weight + torsion spring)
    bh = b + math.radians(0.5)
    ft = P["nail_tab"]
    tab = (P["y_lever_front"] - ft[0] / 2, P["z_st"] - P["nail_tab_below"] - ft[1] / 2)
    tabw = A.lp(tab, bh)
    Tw = A.mL * G * (A.L[0] - A.lp(A.cL, bh)[0]) + (A.spring_T(bh) if A.spring else 0.0)
    F_tab = Tw / (A.L[0] - tabw[0])
    return dict(notch_lift_needed=need_total, front_rise_to_keeper=P["keeper_gap"], notch_lift_phase1=lip1[1] - lip[1],
                key_tilt_deg=math.degrees(ph1 + ph2), capstan_rise=cap_rise, lever_angle_needed_deg=math.degrees(b),
                pull_N=max(F1h + snap1, F2h + snap2), pull_N_lever=max(F1s, F2s), pull_N_nosnap=max(F1h, F2h),
                pull_N_snap_hi=max(F1h + snap1 * snap_hi, F2h + snap2 * snap_hi), pull_N_lever_snap_hi=max(F1 + snap1 * snap_hi, F2 + snap2 * snap_hi),
                F_tab=F_tab, tab_world=tabw,
                rear_wall_limit_deg=math.degrees(bb), slide_forward=3.0,
                ph1=ph1, ph2=ph2, pad=pad, kp=kp_, kp1=kp1, pin_lift=pin_lift, pin_clear=pin_lift - P["pin_engage"])


def removal_path(P, g, name, b_hold_deg=12.0, tilt_deg=3.0, removed=(), shift_x=0.0, n=12):
    """collision check of the single-key removal path with the rail, pads and cover removed:
    pull_up  - hook the rear lip and pull up: the key pivots on its tail pad, then on the keeper; the capstan
               lifts the (untouched) lever; the rear notch lip ends removal_lip_clear above the rod, the block clears its pin
    slide_3mm- slide 3 mm forward (crossbar out from under the keeper hook)
    tilt     - hold the own lever up at b_hold by its front; tilt the key nose-up about its tail pad (ribs /
               walls above the guide tab)
    shift    - (black keys only, after the neighbouring white key named in `removed` is out) swing the key's front
               sideways by shift_x (plan yaw about the tail, which stays under its lever) into the white key's place
    draw_out - pull the key out forward along its tilted axis until the tail end is in front of the lever.
    Obstacles: fixed parts left in place, the neighbour keys and levers at rest (keys in `removed` absent, their
    levers resting on the service block = rest angle), the own lever (on the capstan, then held at b_hold)."""
    keys, lay = g["keys"], g["lay"]
    kd = keys[name]
    A = g["Ab"] if kd["black"] else g["Aw"]
    rem = g["removal_b"] if kd["black"] else g["removal_w"]
    xl = lay["levers"][name]
    yc = g["caps"]["black" if kd["black"] else "white"]
    kpr = key_prisms(P, kd, yc, xl)
    removed_parts = ("up-stop pad", "pad wedge", "pad bar", "cover curtain", "fin boss bore")      # r4: the curtain strip and the pad bars are lifted out (r4.4: bores are holes)
    obst = [f for f in fixed_prisms(P, g) if not f[0].startswith(removed_parts)]
    i = ORDER.index(name)
    for j in (i - 2, i - 1, i + 1, i + 2):
        if 0 <= j < 12:
            nm2 = ORDER[j]
            kd2 = keys[nm2]
            yc2 = g["caps"]["black" if kd2["black"] else "white"]
            if nm2 not in removed:
                obst += [(t + " (key %s)" % nm2, x0, x1, poly) for t, x0, x1, poly in key_prisms(P, kd2, yc2, lay["levers"][nm2])]
            bn = g["b_rest_" + ("b" if kd2["black"] else "w")]
            if nm2 in removed:              # r4: a lever whose key is out lies where it fell (no service block)
                bn = math.radians(g["lever_drop"][nm2]["angle_deg"]) if nm2 in g.get("lever_drop", {}) else bn
            obst += [(t + " (lever %s)" % nm2, x0, x1, [rot(p, P["L"], -bn) for p in poly])
                     for t, x0, x1, poly in lever_prisms(P, lay["levers"][nm2], g["collars"][nm2])]
    own_lever = lever_prisms(P, xl, g["collars"][name])
    skip = (("balance block", "balance pin"), ("crossbar", "keeper"), ("rest felt", "rear shelf"), ("thin tail", "rear shelf"))

    yp = yc + 4.0          # yaw pivot (plan) at the rear of the capstan: the tail stays under its lever

    def xyaw(x0, x1, poly, dx):
        """yaw the key in plan about y = yp so that its front edge moves by dx (x-range of the prism widened by
        the shift's variation over the prism's own y-span)."""
        if dx == 0.0:
            return x0, x1
        f0 = P["y_black_front"] if kd["black"] else 0.0
        ys_ = [p[0] for p in poly]
        s0 = dx * max(0.0, (yp - min(ys_)) / (yp - f0))
        s1 = dx * max(0.0, (yp - max(ys_)) / (yp - f0))
        return x0 + min(s0, s1), x1 + max(s0, s1)

    def dist(tf, b_lever, dx=0.0, skip_cap=False):
        kw_ = []
        for t, x0, x1, poly in kpr:
            xa, xb = xyaw(x0, x1, poly, dx)
            kw_.append((t, xa, xb, [tf(p) for p in poly]))
        lv = [(t + " (own lever)", x0, x1, [rot(p, P["L"], -b_lever) for p in poly]) for t, x0, x1, poly in own_lever]
        best = (1e9, None)
        for t, x0, x1, pg in kw_:
            for f in obst + lv:
                if f[1] - x1 > 3 or x0 - f[2] > 3:
                    continue
                if any(t.startswith(u) and f[0].startswith(v) for u, v in skip):
                    continue
                if skip_cap and t == "capstan head" and "own lever" in f[0]:
                    continue
                d, mode = prism_dist((x0, x1), pg, (f[1], f[2]), f[3])
                if d < best[0]:
                    best = (d, "%s vs %s" % (t, f[0]))
        return best
    out = {}
    pad, kp1 = rem["pad"], rem["kp1"]
    ph1, ph2 = rem["ph1"], rem["ph2"]
    b_up = math.radians(rem["lever_angle_needed_deg"])
    b_rest = g["b_rest_" + ("b" if kd["black"] else "w")]
    worst = (1e9, None)
    for k in range(n + 1):
        f = k / n
        if f <= 0.5:
            tf = (lambda p, a=2 * f * ph1: rot(p, pad, -a))
            bl = b_rest
        else:
            tf = (lambda p, a=(2 * f - 1) * ph2: rot(rot(p, pad, -ph1), kp1, a))
            bl = max(b_rest, b_up * (2 * f - 1))
        worst = min(worst, dist(tf, bl, 0.0, True), key=lambda q: q[0])
    out["pull_up"] = worst
    lifted = lambda p: rot(rot(p, pad, -ph1), kp1, ph2)
    worst = (1e9, None)
    for k in range(n + 1):
        dy = -3.0 * k / n
        worst = min(worst, dist(lambda p, dy=dy: (lifted(p)[0] + dy, lifted(p)[1]), b_up, 0.0, True), key=lambda q: q[0])
    out["slide_3mm"] = worst
    bh = math.radians(b_hold_deg)
    base = lambda p: (lifted(p)[0] - 3.0, lifted(p)[1])
    pad_now = base(pad)
    at = math.radians(tilt_deg)
    worst = (1e9, None)
    for k in range(n + 1):
        a = at * k / n
        worst = min(worst, dist(lambda p, a=a: rot(base(p), pad_now, -a), bh), key=lambda q: q[0])
    out["tilt"] = worst
    tilted = lambda p: rot(base(p), pad_now, -at)
    if shift_x:
        worst = (1e9, None)
        for k in range(n + 1):
            worst = min(worst, dist(tilted, bh, shift_x * k / n), key=lambda q: q[0])
        out["shift"] = worst
    L_out = P["y_tail_end"] - P["y_lever_front"] + 3.0
    worst = (1e9, None)
    for k in range(4 * n + 1):
        s_ = L_out * k / (4 * n)
        worst = min(worst, dist(lambda p, s_=s_: (tilted(p)[0] - s_ * math.cos(at), tilted(p)[1] + s_ * math.sin(at)), bh, shift_x),
                    key=lambda q: q[0])
    out["draw_out"] = worst
    out.update(b_hold_deg=b_hold_deg, tilt_deg=tilt_deg, L_out=L_out, shift_x=shift_x, removed=list(removed))
    return out

# ============================================================================ part geometry (prisms: x-range x (y,z) polygon)
def block_lip_y(P):
    """y range of the lip region of the stepped balance block (printed notch half-width + lip wall)."""
    K = P["K"]
    h = math.sqrt(P["notch_R"] ** 2 - P["block_lift"] ** 2)
    return K[0] - h - P["block_lip_wall"], K[0] + h + P["block_lip_wall"]


def notch_block_poly(P):
    K = P["K"]
    zb = K[1] + P["block_lift"]
    zs = P.get("block_step_z", zb)
    R = P["notch_R"]
    h = math.sqrt(R * R - (zb - K[1]) ** 2)
    a0 = math.degrees(math.atan2(zb - K[1], h))
    yl0, yl1 = block_lip_y(P)
    pts = [(P["block_y"][0], zs), (yl0, zs), (yl0, zb), (K[0] - h, zb)]
    pts += arc(K, R, 180 - a0, a0, 16)[1:-1]
    pts += [(K[0] + h, zb), (yl1, zb), (yl1, zs), (P["block_y"][1], zs), (P["block_y"][1], P["block_top"]),
            (P["block_y"][0], P["block_top"])]        # r3: stepped bottom (lip region only reaches below the rod), real top
    return pts


def capstan_poly(P, y_cap):
    zc, R = P["z_c"], P["cap_R"]
    zu = zc - P["cap_k"]
    h = math.sqrt(R * R - (zu - (zc - R)) ** 2)
    a0 = math.degrees(math.atan2(zu - (zc - R), h))
    pts = arc((y_cap, zc - R), R, a0, 180 - a0, 12)
    return pts + [(y_cap - 1.5, P["beam_z_cap"]), (y_cap + 1.5, P["beam_z_cap"])]


def tail_wall_poly(P, y0, zb, zt):
    r0, r1, rz = P["wall_relief"]
    return [(y0, zb), (r0, zb), (r0 + 0.8, rz), (r1 - 0.8, rz), (r1, zb), (P["y_body_end"], zb),
            (P["y_body_end"], zt), (y0, zt)]


def key_prisms(P, kd, y_cap, xl):
    """list of (tag, x0, x1, poly) in the key frame at rest."""
    zb = P["key_bot"]
    wl = P["wall"]
    out = []
    hx0, hx1 = kd["head"]
    tx0, tx1 = kd["tail"]
    gc = kd["guide_c"]
    if not kd["black"]:
        zt = P["key_top"]
        zs = zt - P["skin_w"]
        head_sil = [(1.5, zb), (48.5, zb), (50.0, 40.9), (50.0, zs), (1.5, zs)]
        out += [("skin head", hx0, hx1, rect(0.0, 50.0, zs, zt)),
                ("skin tail", tx0, tx1, rect(50.0, P["y_skin_end"], zs, zt)),
                ("head wall L", hx0, hx0 + wl, head_sil), ("head wall R", hx1 - wl, hx1, head_sil),
                ("front wall", hx0, hx1, rect(1.5, 2.7, zb, zs)),
                ("down-stop floor", hx0 + wl, hx1 - wl, rect(P["w_floor_y"][0], P["w_floor_y"][1], zb, zb + 1.2)),
                ("guide rib L", gc - 5.5, gc - 4.3, rect(P["w_rib_y"][0], P["w_rib_y"][1], zb, zs)),
                ("guide rib R", gc + 4.3, gc + 5.5, rect(P["w_rib_y"][0], P["w_rib_y"][1], zb, zs)),
                ("crossbar", gc - 4.3, gc + 4.3, rect(P["w_crossbar_y"][0], P["w_crossbar_y"][1], zb, zb + P["crossbar_t"])),
                ("tail wall L", tx0, tx0 + wl, tail_wall_poly(P, 48.5, zb, zs)),
                ("tail wall R", tx1 - wl, tx1, tail_wall_poly(P, 48.5, zb, zs)),
                ("rear wall", tx0, tx1, rect(P["y_body_end"] - wl, P["y_body_end"], zb, zs))]
        if hx1 - tx1 > 0.1:
            out.append(("head step R", tx1, hx1, rect(48.8, 50.0, zb, zs)))
        if tx0 - hx0 > 0.1:
            out.append(("head step L", hx0, tx0, rect(48.8, 50.0, zb, zs)))
    else:
        zt = P["black_top"]
        zs = zt - P["skin_b"]
        f0 = P["y_black_front"]
        x0, x1 = kd["head"]
        ins = (P["black_w"] - P["black_top_w"]) / 2
        slope = [(f0, zb), (f0, 43.5), (f0 + 1.0, zt), (f0 + 2.2, zt), (f0 + 1.2, 43.5), (f0 + 1.2, zb)]
        ys_, zs2_ = P.get("black_skin_step", (P["y_skin_end"], zt))
        out += [("skin", x0 + ins, x1 - ins, [(f0 + 0.83, zs), (f0 + 1.0, zt), (ys_, zt), (ys_, zs2_), (P["y_skin_end"], zs2_), (P["y_skin_end"], zs)]),
                ("wall L low", x0, x0 + wl, tail_wall_poly(P, f0, zb, 43.5)),
                ("wall R low", x1 - wl, x1, tail_wall_poly(P, f0, zb, 43.5)),
                ("wall L up", x0 + ins, x0 + ins + wl, rect(f0 + 0.5, P["y_body_end"], 43.5, zs)),
                ("wall R up", x1 - ins - wl, x1 - ins, rect(f0 + 0.5, P["y_body_end"], 43.5, zs)),
                ("front wall", x0 + ins, x1 - ins, slope),
                ("front wall low", x0, x1, rect(f0, f0 + wl, zb, 43.5)),
                ("stop floor", x0 + wl, x1 - wl, rect(P["b_floor_y"][0], P["b_floor_y"][1], zb, zb + 1.2)),
                ("crossbar", gc - 4.3, gc + 4.3, rect(P["b_crossbar_y"][0], P["b_crossbar_y"][1], zb, zb + P["crossbar_t"])),
                ("rear wall", x0, x1, rect(P["y_body_end"] - wl, P["y_body_end"], zb, zs))]
    xc = kd["xc"]
    # r3: interior parts exported like the mass model: magnet boss tube (full height) tied to both walls by a rib at
    # y_elem, stiffening ribs, and the web from the balance block to the top skin
    # r4 (drafter patch): on black keys the boss is merged into the side walls (the r3 +-3.8 boss left two 0.2 slots,
    # narrower than the 0.4 nozzle)
    bh = (P["black_w"] / 2 - wl) if kd["black"] else 3.8
    out.append(("magnet boss", xc - bh, xc + bh, rect(P["y_elem"] - 3.8, P["y_elem"] + 3.8, zb, zs)))
    w0, w1 = (kd["head"] if kd["black"] else kd["tail"])
    out.append(("magnet boss rib", w0 + wl, w1 - wl, rect(P["y_elem"] - 0.6, P["y_elem"] + 0.6, zb, zs)))
    for yr_ in ((100.0, 125.0) if kd["black"] else (40.0, 90.0, 118.0)):
        r0_, r1_ = (kd["head"] if (kd["black"] or yr_ < 50) else kd["tail"])
        out.append(("rib", r0_ + wl, r1_ - wl, rect(yr_ - 0.6, yr_ + 0.6, zs - 8.0, zs)))
    bw = P["beam_w"] / 2
    bx0, bx1 = block_x(P, kd)
    xbc = (bx0 + bx1) / 2
    out.append(("block web", xbc - 0.8, xbc + 0.8, rect(P["block_y"][0], P["block_y"][1], P["block_top"], zs)))
    b0_ = P["beam_z"][0]
    rl_ = P.get("tail_relief", {}).get(kd["name"])

    def _under(ya, yb):
        """underside points from ya to yb (ya < yb) with the r4.4 fix-2 relief"""
        if not rl_ or rl_[1] <= ya or rl_[0] >= yb:
            return [(ya, b0_), (yb, b0_)]
        r0_, r1_ = max(ya, rl_[0]), min(yb, rl_[1])
        pts_ = [(ya, b0_)] if ya < r0_ else []
        pts_ += [(r0_, b0_ + rl_[2])] if ya < r0_ else [(ya, b0_ + rl_[2])]
        pts_ = ([(ya, b0_), (r0_, b0_)] if ya < r0_ else []) + [(r0_, b0_ + rl_[2]), (r1_, b0_ + rl_[2])]
        pts_ += [(r1_, b0_), (yb, b0_)] if r1_ < yb else []
        return pts_
    ub_ = _under(P["y_body_end"], y_cap + 4.0)
    ut_ = _under(y_cap + 4.0, P["y_tail_end"])
    out += [("balance block", bx0, bx1, notch_block_poly(P)),
            ("beam", xl - bw, xl + bw, ub_ + [(y_cap + 4.0, P["beam_z_cap"]), (y_cap - 6.0, P["beam_z_cap"]),
                                        (y_cap - 7.0, P["beam_z"][1]), (P["y_body_end"], P["beam_z"][1])]),
            ("capstan head", xl - P["cap_dk"] / 2, xl + P["cap_dk"] / 2, capstan_poly(P, y_cap)),
            ("thin tail", xl - tail_w(P, kd["black"]) / 2, xl + tail_w(P, kd["black"]) / 2, [ut_[0], (y_cap + 4.0, P["tail_top"]),
                                             (P["y_tail_end"] - P["tail_chamfer"], P["tail_top"]), (P["y_tail_end"], P["tail_top"] - P["tail_chamfer"])] + ut_[::-1][:-1]),
            ("rest felt", rest_pad_x(P, kd["name"], xl, kd["black"])[0][0], rest_pad_x(P, kd["name"], xl, kd["black"])[0][1],
             rect(P["rest_pad_y"][0], P["rest_pad_y"][1], P["beam_z"][0] - P["rest_felt"] - P["rest_shim"], P["beam_z"][0]))]
    foot_ = rest_pad_x(P, kd["name"], xl, kd["black"])[1]
    if foot_:
        # r4.4: printed rest foot = the thin tail widened over the rest-pad y range (same section, chamfered end)
        out.append(("thin tail rest foot", foot_[0], foot_[1], [(P["rest_pad_y"][0], P["beam_z"][0]), (P["rest_pad_y"][0], P["tail_top"]),
                                                               (P["y_tail_end"] - P["tail_chamfer"], P["tail_top"]), (P["y_tail_end"], P["tail_top"] - P["tail_chamfer"]),
                                                               (P["y_tail_end"], P["beam_z"][0])]))
    if kd["black"] and P.get("black_mass", 0.0) > 0:
        my = P["black_mass_pt"][0]
        out.append(("mass pocket (lead)", kd["head"][0] + wl, kd["head"][1] - wl, rect(my - 4.6, my + 4.6, zb, zb + 9.0)))
    return out


def cradle_clear_x(P):
    """x clearance from a balance block to a rod cradle: 1.3 nominal + key play at the block (tab + pin yaw)."""
    return P["cradle_clear"] + P["tab_play"] + P["yaw_pin"] * 1.1 + 0.02


def rail_pockets(P, g, keys, order):
    """r4.4 fix 2: (x0, x1, z_pocket, y_pocket) under every block of a colour that needs a pocket (g['rail_pocket'])."""
    rp = g.get("rail_pocket") or {}
    out = []
    c = cradle_clear_x(P)          # the whole lowered zone beside the block (block +- the cradle clearance incl. key play)
    for nm in order:
        q = rp.get("black" if keys[nm]["black"] else "white")
        if q:
            bx0, bx1 = block_x(P, keys[nm])
            out.append((bx0 - c + 1e-3, bx1 + c - 1e-3, q["z"], q["y"]))
    return out


def rail_saddle(P):
    """saddle of a cradle: (lip z, half-width at the lip, groove arc points)."""
    K = P["K"]
    lip = P["rail_groove_lip"]
    Rg = P["rod_k"] / 2 + 0.05
    cz = K[1] + 0.05
    h = math.sqrt(Rg * Rg - (lip - cz) ** 2)
    a0 = math.degrees(math.atan2(lip - cz, h))
    return lip, h, arc((K[0], cz), Rg, 180 - a0, 360 + a0, 12)


def rail_prisms(P, g, blocks, rail_x, rod_x, ribbon=False, lane=None, pockets=()):
    """r3 balance rail: lowered (top z_rail_low) under every balance block, a cradle with the R2.05 saddle in every
    x-gap between blocks (1.3 + key play from each block), end walls closing the groove, the D4 rod.
    ribbon=True: the module's ribbon lane P['ribbon_x'] under the rail (z5-10); r4.4: lane=(x0, x1) = an end part's
    lead lane (same z5-10)."""
    if ribbon and lane is None:
        lane = tuple(P["ribbon_x"])
    K = P["K"]
    lip, h, groove = rail_saddle(P)
    ry0, ry1 = P["rail_front_y"], P["rail_y"][1]
    zlo = g["z_rail_low"]
    rw = h + 0.8                       # ridge half-width (0.8 flat lip each side of the saddle)
    c = cradle_clear_x(P)
    rx0, rx1 = rail_x
    kx0, kx1 = rod_x
    wall_x0, wall_x1 = rx0 + 1.0, rx1 - 1.0      # groove end walls 1.0

    def bottom(xa, xb):
        return P["lead_lane_z"][1] if (lane is not None and xa >= lane[0] - 1e-6 and xb <= lane[1] + 1e-6) else 5.0

    def cradle(zb):
        return [(ry0, zb), (ry1, zb), (ry1, zlo), (K[0] + rw, zlo), (K[0] + rw, lip), (K[0] + h, lip)] + groove[::-1] + \
               [(K[0] - h, lip), (K[0] - rw, lip), (K[0] - rw, zlo), (ry0, zlo)]
    segs = []                          # (x0, x1, kind)
    bl = sorted(blocks)
    cr = []
    for (a0, a1), (b0, b1) in zip([(None, wall_x0 - c)] + bl, bl + [(wall_x1 + c, None)]):
        x0c, x1c = a1 + c, b0 - c          # includes the spans between the groove end walls and the first / last block
        if x1c - x0c >= 0.8:
            cr.append((x0c, x1c))
    xs = sorted({wall_x0, wall_x1} | {v for q in cr for v in q} |
                ({lane[0], lane[1]} if lane is not None else set()))
    xs = [x for x in xs if wall_x0 <= x <= wall_x1]
    # r3: the groove ends are closed by narrow stop posts on the rod axis (the blocks' snap lips pass beside them)
    post = rect(K[0] - 1.0, K[0] + 1.0, 5.0, K[1] - 0.5)          # r4: 2.0 deep (r3 1.4)
    F = [("balance rail (lowered under the blocks)", rx0, wall_x0, rect(ry0, ry1, 5.0, zlo)),
         ("balance rail (lowered under the blocks)", wall_x1, rx1, rect(ry0, ry1, 5.0, zlo)),
         ("rod end stop post", rx0, wall_x0, post), ("rod end stop post", wall_x1, rx1, post)]
    for xa, xb in zip(xs[:-1], xs[1:]):
        if xb - xa < 1e-6:
            continue
        zb = bottom(xa, xb)
        is_cr = any(q0 - 1e-6 <= xa and xb <= q1 + 1e-6 for q0, q1 in cr)
        if is_cr:
            F.append(("balance rail cradle", xa, xb, cradle(zb)))
        else:
            # r4.4 fix 2 (verifier geometry major 3): pocket behind the pin row under a block whose lip region comes within
            # 1.3 of z_rail_low once the notch settles / sinks on the rod (black keys): top z_pocket from y_pocket back
            pk_ = [q for q in pockets if xa < q[1] - 1e-6 and xb > q[0] + 1e-6]
            if pk_:
                zp_, yp_ = pk_[0][2], pk_[0][3]
                F.append(("balance rail (lowered under the blocks; pocket z%.2f behind y%.1f)" % (zp_, yp_), xa, xb,
                          [(ry0, zb), (ry1, zb), (ry1, zp_), (yp_, zp_), (yp_, zlo), (ry0, zlo)]))
            else:
                F.append(("balance rail (lowered under the blocks)", xa, xb, rect(ry0, ry1, zb, zlo)))
    F.append(("key rod SUS304 D4", kx0, kx1, circle(K, P["rod_k"] / 2, 20)))
    return F




def lever_prisms(P, xl, collars=(0.0, 0.0)):
    """r4 lever (lever frame, b = 0): carrier side walls 0.8 with top snap lips (to lip_end_y) and bottom lips (from
    lip_front_y), front wall with the R3 corner and the fingernail tab, core (steel bottom), rear wall, rear floor
    behind the steel (backs the capstan felt), felt strip, hub with its collars (r4: the r3 C-rings), web."""
    hw = P["lever_w"] / 2
    cw = P["carrier_wall"]
    cws = P.get("carrier_side_wall", cw)             # r4.4 fix 2b: side walls 0.7 (pocket 9.2 = steel + 2 bond lines)
    s0 = P["y_lever_front"]
    sf, sr = P["y_steel_front"], P["y_steel_rear"]
    s1 = sr + cw
    zb = P["z_sb"] - P["lip"]
    zsb = P["z_sb"]
    ztop = P["z_st"] + P["lip"]
    zst = P["z_st"]
    yl = P["lip_front_y"]
    R = P["cap_R_out"]
    capc = arc((s0 + R, ztop - R), R, 90, 180, 8)
    # r4.4: the side-wall top is raised to ztop (and carries the inward top snap lip) only over lip_segs (lever frame);
    # r4.1-r4.3: to lip_end_y with a gap lip_gap_y
    segs_ = sorted(P["lip_segs"])
    top_ = []
    zgap_ = zst - P.get("wall_drop_pad", 0.0)          # r4.4 fix 2: wall top between the lip segments (pad zone)
    for y0_, y1_ in reversed(segs_):
        if y1_ >= sr - 1e-9:
            top_ += [(sr, ztop)]
        else:
            top_ += [(y1_, zgap_), (y1_, ztop)]
        top_ += [(y0_, ztop), (y0_, zgap_)] if y0_ > sf + 1e-9 else []
    sil = [(s0, zsb), (yl, zsb), (yl, zb), (s1, zb), (s1, P["rear_wall_top"])] + ([] if top_ and top_[0][0] >= sr - 1e-9 else [(sr, zst)]) + top_ + capc
    # r4: the core bottom stays at the steel bottom up to the rear wall (the capstan felt runs on under the rear floor)
    core = [(s0, zsb), (s1, zsb), (s1, P["rear_wall_top"]), (sr, zst), (sf + 3.0, zst), (sf + 3.0, ztop)] + capc
    L = P["L"]
    web = lever_web_poly(P)
    fy0, fy1 = P["felt_c_y"]
    ft, fh = P["nail_tab"]
    ztab = P["z_st"] - P["nail_tab_below"]
    f0, f1 = P["carrier_floor_y"]
    # r4.2: the tab fills the R3 corner above its underside (attached along the arc)
    tab = nail_tab_poly(P)
    pw_ = P["spring_pocket"][1] / 2
    out = [("carrier side wall L", xl - hw, xl - hw + cws, sil), ("carrier side wall R", xl + hw - cws, xl + hw, sil),
           ("carrier core (steel bottom)", xl - hw + cws, xl + hw - cws, core),
           ("fingernail tab", xl - hw + cws, xl + hw - cws, tab),
           ("carrier rear floor", xl - hw + cws, xl + hw - cws, rect(f0, f1, zsb, zsb + P["carrier_floor_t"])),
           ("felt strip", xl - 3.5, xl + 3.5, rect(fy0, fy1, P["z_c"], P["z_sb"])),
           # r4.2: hub and web split at the spring pocket (x +-1.5): the pocket section is one C-shaped outline
           ("hub", xl - hw, xl - pw_, circle(L, P["hub_R"], 24)), ("hub", xl + pw_, xl + hw, circle(L, P["hub_R"], 24)),
           ("web", xl - hw, xl - pw_, web), ("web", xl + pw_, xl + hw, web)]
    # r4.5: the pocket section is two pieces (the short-leg groove cuts the ring): A = web side (slot upper face .. groove inner
    # face, web underside cut locally), B = lower ring (groove bearing face .. slot lower face)
    pa_, pb_ = hub_pocket_poly(P, web)
    out += [("hub (spring pocket section A: web, slot, short-leg groove)", xl - pw_, xl + pw_, pa_),
            ("hub (spring pocket section B: lower ring, short-leg bearing face)", xl - pw_, xl + pw_, pb_)]
    cl, cr = collars
    if cl > 0:
        out.append(("hub collar", xl - hw - cl, xl - hw, circle(L, 3.0, 16)))
    if cr > 0:
        out.append(("hub collar", xl + hw, xl + hw + cr, circle(L, 3.0, 16)))
    for sgn in (-1, 1):
        xa, xb = sorted((xl + sgn * 3.5, xl + sgn * (hw - cws)))
        out.append(("bottom lip", xa, xb, rect(yl, fy0, zb, zsb)))      # in front of the felt strip only (the capstan runs under the felt)
    # r4.4 (R44 issue 1): the inward top snap lips (lip_over wide over the steel top, lip thick) as their own prisms, so the
    # sweep and geometry.json see them (r4.1-r4.3 had them only inside the side-wall outline / in the text)
    for y0_, y1_ in P["lip_segs"]:
        for sgn, sd in ((-1, "L"), (1, "R")):
            xa, xb = sorted((xl + sgn * (hw - cws - P["lip_over"]), xl + sgn * (hw - cws)))
            out.append(("carrier top snap lip %s y%.0f-%.0f" % (sd, y0_, y1_), xa, xb, rect(y0_, y1_, zst, ztop)))
    return out


def nail_tab_poly(P):
    """r4.2: fingernail tab (lever frame): y front - tab .. the R3 arc of the front upper corner, z tab underside .. tab top
    (= carrier top).  It fills the corner above its underside so it is one piece with the front wall (r4.1 floated)."""
    s0 = P["y_lever_front"]
    ft, fh = P["nail_tab"]
    ztab = P["z_st"] - P["nail_tab_below"]
    ztop = P["z_st"] + P["lip"]
    R = P["cap_R_out"]
    cy, cz = s0 + R, ztop - R
    zb = ztab - fh
    pts = [(s0 - ft, zb)]
    n = 10
    for i in range(n + 1):                       # arc from the tab underside up to the carrier top (y increasing)
        z = zb + (min(ztab, ztop) - zb) * i / n
        dz = max(0.0, z - cz)
        pts.append((cy - math.sqrt(max(0.0, R * R - dz * dz)) if z > cz else s0, z))
    pts.append((s0 - ft, min(ztab, ztop)))
    return pts


def lever_web_poly(P):
    """lever web (lever frame, b = 0): from the carrier rear wall (0.5 into it) to the hub, top line to the hub top."""
    L = P["L"]
    s1 = P["y_steel_rear"] + P["carrier_wall"]
    return [(s1 - 0.5, L[1]), (s1 - 0.5, 44.0), (L[0], L[1] + P["hub_R"]), (L[0], L[1])]


def spring_rm_w(P, w_deg):
    """r4.5 fix 2: coil mean radius wound w_deg past free: the body closes up, D' = D n / (n + w / 360)."""
    D = P["spring_ID"] + P["spring_d"]
    return D * P["spring_n"] / (P["spring_n"] + max(w_deg, 0.0) / 360.0) / 2


def spring_anchor(P, rm=None):
    """long leg of the torsion spring while loaded (world): tip centre on the rear-wall groove bottom at spring_leg from the
    axis, tangent to the coil's mean circle on the rear side.  r4.5 fix 2: tangent to the coil at its REST wind
    (spring_rm_rest: the loaded coil is held centred on the rod by its captured short leg).  Returns (tip (y, z), phiT, phiQ)
    (rad, world)."""
    L = P["L"]
    rm = P.get("spring_rm_rest", P["spring_rm"]) if rm is None else rm
    d = P["spring_d"]
    sg = P["spring_groove"]
    ytip = sg[0] + sg[4] - d / 2                     # leg centre line on the groove bottom
    rho = P["spring_leg"]
    ztip = L[1] + math.sqrt(rho * rho - (ytip - L[0]) ** 2)
    phiT = math.atan2(ztip - L[1], ytip - L[0])      # world angle of the tip seen from the axis
    phiQ = phiT - math.acos(rm / rho)                 # rear-side tangent point
    return (ytip, ztip), phiT, phiQ


def spring_short_leg_lf(P):
    """r4.5: the short leg in the LEVER frame (= world at b = 0), loaded at b = 0 with the coil centred on the axis.  The wire
    runs CCW (in (y, z)) from the short leg's tangent point to the long leg's; installed at b = 0 it sweeps spring_swept_free +
    (0 - spring_free_deg), so the short leg's tangent point is at alpha_s = phiQ - ((spring_swept_free - spring_free_deg)
    mod 360); the leg is straight and runs along the CW tangent (direction alpha_s - 90 deg) for spring_short_leg.
    r4.5 fix 2: tangent to the coil at its rest-wind mean radius spring_rm_rest.  nrm = unit vector to the tangent point,
    u = leg direction."""
    L = P["L"]
    rm = P.get("spring_rm_rest", P["spring_rm"])
    ls = P["spring_short_leg"]
    _, _, phiQ = spring_anchor(P)
    S = (P["spring_swept_free"] - P["spring_free_deg"]) % 360.0
    a = math.radians((math.degrees(phiQ) - S + P.get("spring_notch_rot", 0.0)) % 360.0)
    nrm = (math.cos(a), math.sin(a))
    u = (math.cos(a - math.pi / 2), math.sin(a - math.pi / 2))
    Q = (L[0] + rm * nrm[0], L[1] + rm * nrm[1])
    T = (Q[0] + ls * u[0], Q[1] + ls * u[1])
    return dict(alpha_s=math.degrees(a), nrm=nrm, u=u, Q=Q, T=T, S_inst=S, dl=0.0, rm=rm,
                tip_r=math.hypot(T[0] - L[0], T[1] - L[1]), tip_ang=math.degrees(math.atan2(T[1] - L[1], T[0] - L[0])) % 360.0)


def spring_notch_geo(P):
    """r4.5 fix 2 (verifier spring major: a short leg that only BEARS on one face lets the coil float 0.44 onto the rod - the
    leg lifts off, the spring unwinds ~11 deg and the coil rubs on the fixed rod with ~2-3 N): the short leg is CAPTURED in a
    narrow blind groove (band = wire d + spring_notch[0] play) that starts inside the pocket (band coordinate spring_notch[1])
    and runs along the leg through the hub wall into the web, ending spring_notch[2] past the leg tip.  The band is the loaded
    leg (tangent at alpha_s, coil centred) turned CW by theta_c so that the leg touches the OUTER face at its tip corner O and
    the INNER face at that face's pocket-edge corner E: the spring couple T is carried by these two contacts,
    F = T / arm (arm = their distance along the band), both on the web-side piece A, and the coil hangs on its own leg, clear
    of the rod.  The coil goes in along the leg (tip first) through the insertion slot (direction slot_deg = the band
    direction reversed).  Band coordinates: p = L + nn * n_g + ss * u_g."""
    L = P["L"]
    d = P["spring_d"]
    play, s0, e_clr = P["spring_notch"]
    Ro, Ri = P["hub_R"], P["spring_pocket"][0] / 2
    sl = spring_short_leg_lf(P)
    rm, ls = sl["rm"], P["spring_short_leg"]
    a0 = math.radians(sl["alpha_s"])
    s_E = math.sqrt(Ri ** 2 - (rm - d / 2) ** 2)          # leg parameter where its inner surface meets the pocket circle
    A_, B_ = d, ls - s_E
    R_ = math.hypot(A_, B_)
    th = math.asin((A_ + play) / R_) - math.atan2(A_, B_)  # d cos th + (ls - s_E) sin th = d + play
    ag = a0 - th
    n_g = (math.cos(ag), math.sin(ag))
    u_g = (math.cos(ag - math.pi / 2), math.sin(ag - math.pi / 2))

    def lg(nn0, s):                                        # leg-frame point (offset along nrm, distance along the leg) -> band
        return nn0 * math.cos(th) + s * math.sin(th), -nn0 * math.sin(th) + s * math.cos(th)

    def p(nn, ss):
        return (L[0] + nn * n_g[0] + ss * u_g[0], L[1] + nn * n_g[1] + ss * u_g[1])
    c_o, ss_to = lg(rm + d / 2, ls)                        # outer face through the tip's outer corner O
    c_i, ss_E = lg(rm - d / 2, s_E)                        # inner face through E (on the pocket circle)
    ss_ti = lg(rm - d / 2, ls)[1]
    ss_tip = max(ss_to, ss_ti)
    ss_end = ss_tip + e_clr
    assert c_i < c_o < Ri < Ro and abs(c_o - c_i - d - play) < 1e-9, "short-leg groove: band"
    ss_bp, ss_bo = math.sqrt(Ri ** 2 - c_o ** 2), math.sqrt(Ro ** 2 - c_o ** 2)
    ss_io = math.sqrt(Ro ** 2 - c_i ** 2)
    ss_xo = -c_o * n_g[1] / u_g[1]                         # outer face meets the web underside z = L_z
    ss_xi = -c_i * n_g[1] / u_g[1]
    band = [p(c_i, s0), p(c_o, s0), p(c_o, ss_end), p(c_i, ss_end)]
    ang = lambda q: math.degrees(math.atan2(q[1] - L[1], q[0] - L[0])) % 360.0
    E, O = p(c_i, ss_E), p(c_o, ss_to)
    arm = ss_to - ss_E
    slot_deg = (math.degrees(ag) + 90.0) % 360.0             # insertion: the spring comes in along +u_g (from -u_g)
    return dict(theta_c=math.degrees(th), n_g=n_g, u_g=u_g, c_o=c_o, c_i=c_i, s0=s0, ss_end=ss_end, ss_tip=ss_tip, ss_E=ss_E, ss_to=ss_to,
                ss_bp=ss_bp, ss_bo=ss_bo, ss_io=ss_io, ss_xo=ss_xo, ss_xi=ss_xi, E=E, O=O, arm=arm, band=band, p=p, short=sl,
                width=c_o - c_i, play=play, slot_deg=slot_deg, s_leg_E=s_E,
                ang_bp=ang(p(c_o, ss_bp)), ang_bo=ang(p(c_o, ss_bo)), ang_E=ang(E), ang_io=ang(p(c_i, ss_io)),
                exit_bearing=p(c_o, ss_bo), exit_inner=p(c_i, ss_io), web_x_outer=p(c_o, ss_xo), web_x_inner=p(c_i, ss_xi),
                end_outer=p(c_o, ss_end), end_inner=p(c_i, ss_end),
                web_cut_depth=max(q[1] for q in band) - L[1], tip_to_end=e_clr,
                # r4.5 names kept for the reports: nn_b / nn_i = outer / inner face offsets, s_e = band end
                nn_b=c_o, nn_i=c_i, s_e=ss_end, face_len=ss_end - ss_bp, leg_on_face=0.0, tip_to_face_end=e_clr)


def hub_pocket_poly(P, web):
    """side outline (lever frame) of the hub's spring-pocket section (lever x +-pocket/2), returned as [A, B].  r4.5 fix 2: the
    hub ring R hub_R around the pocket D spring_pocket[0], merged with the web, is open at the REAR from the insertion slot's
    face on the short-leg side (slot direction spring_notch_geo slot_deg, faces +-spring_slot[1] from the axis: the coil comes
    in along its short leg) round to the long-leg window's upper face (direction spring_window[0], +spring_window[1] from the
    axis: the long leg leaves over the whole lever range), and the captured short-leg groove runs from the pocket through the
    ring into the web (blind).  A = web side (window face .. groove inner face, the web, the web strip under the groove to the
    groove's blind end: both leg contacts are on A); B = lower ring (groove outer face .. insertion-slot face; in 3-D it is
    joined to the full hub on both sides)."""
    L = P["L"]
    Ro, Ri = P["hub_R"], P["spring_pocket"][0] / 2
    N = spring_notch_geo(P)
    thi, fs = N["slot_deg"], P["spring_slot"][2]
    thw, fwu = P["spring_window"][0], P["spring_window"][1]
    a_wu = lambda r: thw + math.degrees(math.asin(fwu / r))
    a_f2 = lambda r: (thi - math.degrees(math.asin(fs / r))) % 360.0
    a_f1 = lambda r: (thi + math.degrees(math.asin(fs / r))) % 360.0
    wy0, wz_top = web[1]
    ang = lambda q: math.degrees(math.atan2(q[1] - L[1], q[0] - L[0])) % 360.0

    def ca(r_, a0, a1, n):
        return [(L[0] + r_ * math.cos(math.radians(a)), L[1] + r_ * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]
    X_o = N["web_x_outer"]
    assert a_wu(Ro) < 90.0 and a_wu(Ri) < N["ang_E"] and N["ang_bo"] < a_f2(Ro) and N["ang_bp"] < a_f2(Ri), "pocket section: layout"
    assert math.hypot(X_o[0] - L[0], X_o[1] - L[1]) > Ro and N["ss_bo"] < N["ss_xo"] < N["ss_end"] and wy0 < X_o[0], "short-leg groove: web crossing"
    assert inside(N["end_outer"], web) and inside(N["end_inner"], web), "short-leg groove: blind end inside the web"
    # the rear opening must contain the insertion slot's other face (the slot strip is inside the opening)
    assert (a_f1(Ri) < a_wu(Ri) or a_f1(Ri) > a_f2(Ri)) and (a_f1(Ro) < a_wu(Ro) or a_f1(Ro) > a_f2(Ro)), "pocket section: slot"
    A = ca(Ro, a_wu(Ro), 90.0, 6)
    A += [(wy0, wz_top), (wy0, L[1]), X_o, N["end_outer"], N["end_inner"], N["E"]]
    A += ca(Ri, N["ang_E"], a_wu(Ri), 16)[1:]
    B = ca(Ro, N["ang_bo"], a_f2(Ro), 14)
    B += ca(Ri, a_f2(Ri), N["ang_bp"], 10)
    return [A, B]


def spring_geometry(P, b, bf=None):
    """r4.2: torsion spring in the lever's hub pocket at lever angle b (rad).  Returns world polylines: coil (mean circle
    + OD), long leg (tangent to the mean circle on the rear side, tip in the rear-wall groove, fixed in the world while
    the spring is loaded; below the free angle it turns with the lever), short leg (turns with the lever), and the long leg's
    lever-frame angle at the hub wall radii (for the window check).  r4.5 fix 2: the short leg is captured in its groove
    (spring_short_leg_lf: straight, tangent at alpha_s, spring_short_leg long); the coil is drawn at its rest-wind radius."""
    L = P["L"]
    rm, d = P.get("spring_rm_rest", P["spring_rm"]), P["spring_d"]
    bf = math.radians(P["spring_free_deg"]) if bf is None else bf
    (ytip, ztip), phiT, phiQ = spring_anchor(P)
    be = max(b, bf)                                   # below the free angle the leg turns with the lever
    Q = (L[0] + rm * math.cos(phiQ), L[1] + rm * math.sin(phiQ))
    T = (ytip, ztip)
    if be != b:
        Q, T = rot(Q, L, -(b - be)), rot(T, L, -(b - be))
    sl = spring_short_leg_lf(P)
    Qs, Ts = rot(sl["Q"], L, -b), rot(sl["T"], L, -b)
    cross = {}
    for r_ in (P["spring_pocket"][0] / 2, P["hub_R"]):
        s_ = math.sqrt(max(0.0, r_ * r_ - rm * rm))
        pw = (Q[0] + s_ * (T[0] - Q[0]) / math.hypot(T[0] - Q[0], T[1] - Q[1]), Q[1] + s_ * (T[1] - Q[1]) / math.hypot(T[0] - Q[0], T[1] - Q[1]))
        pl = rot(pw, L, b)
        cross[r_] = (pl, math.degrees(math.atan2(pl[1] - L[1], pl[0] - L[0])))
    return dict(coil=circle(L, rm + d / 2, 24), coil_rm=rm, long_leg=[Q, T], short_leg=[Qs, Ts], cross=cross, loaded=b >= bf,
                short_bend_deg=0.0, tip_world=(ytip, ztip), phiQ_deg=math.degrees(phiQ), alpha_s_deg=sl["alpha_s"])


def spring_slot_check(P, b_range):
    """r4.2 / r4.5 fix 2: over lever angles b_range (deg), the long leg's centre line where it crosses the hub wall (pocket radius
    and hub radius) must stay inside the rear opening with spring_leg_clear + wire radius to its two bounding faces: the
    long-leg window's upper face (spring_window) and the insertion slot's short-leg-side face.  Returns the worst margin
    (mm, >= 0 = OK) and where, the long leg vs the rear-wall boss, and the short-leg groove data."""
    L = P["L"]
    N = spring_notch_geo(P)
    thw, fwu = P["spring_window"][0], P["spring_window"][1]
    nw = (-math.sin(math.radians(thw)), math.cos(math.radians(thw)))
    thi, fs = math.radians(N["slot_deg"]), P["spring_slot"][2]
    ni = (-math.sin(thi), math.cos(thi))
    worst = (1e9, None)
    for bd in np.arange(b_range[0], b_range[1] + 1e-9, 0.25):
        sg_ = spring_geometry(P, math.radians(bd))
        for r_, (pl, ang) in sg_["cross"].items():
            ow = (pl[0] - L[0]) * nw[0] + (pl[1] - L[1]) * nw[1]
            oi = (pl[0] - L[0]) * ni[0] + (pl[1] - L[1]) * ni[1]
            m_ = min(fwu - ow, oi + fs) - P["spring_d"] / 2 - P["spring_leg_clear"]
            if m_ < worst[0]:
                worst = (m_, dict(b=float(bd), r=r_, offset=ow, angle=ang, face="window" if fwu - ow < oi + fs else "slot"))
    sg0 = spring_geometry(P, 0.0)
    (Q, T) = sg0["long_leg"]
    yb_, zb_ = P["rear_wall"][0] - P["spring_boss"][2], P["spring_boss"][1]
    z_face = Q[1] + (yb_ - Q[0]) * (T[1] - Q[1]) / (T[0] - Q[0])
    y_bot = Q[0] + (zb_ - Q[1]) * (T[0] - Q[0]) / (T[1] - Q[1])
    sg_ = P["spring_groove"]
    leg_ok = (z_face < zb_ and sg_[1] <= zb_ + 1e-9 and sg_[0] <= y_bot <= sg_[0] + sg_[4]) or (z_face >= sg_[1])
    sl = N["short"]
    notch = dict(alpha_s=sl["alpha_s"], S_inst=sl["S_inst"], Q=sl["Q"], T=sl["T"], tip_r=sl["tip_r"], tip_ang=sl["tip_ang"], leg_dir=(sl["alpha_s"] - 90.0) % 360.0,
                 nn=(N["c_i"], N["c_o"]), ss=(N["s0"], N["ss_end"]), band=N["band"], exit_bearing=N["exit_bearing"], exit_inner=N["exit_inner"],
                 end_corner=N["end_outer"], end_inner=N["end_inner"], web_cut_depth=N["web_cut_depth"], face=(N["ss_bp"], N["ss_bo"]), face_len=N["face_len"],
                 leg_on_face=N["leg_on_face"], theta_c=N["theta_c"], band_deg=(sl["alpha_s"] - 90.0 - N["theta_c"]) % 360.0, width=N["width"], play=N["play"],
                 E=N["E"], O=N["O"], arm=N["arm"], ss_E=N["ss_E"], ss_tip=N["ss_tip"], web_x_outer=N["web_x_outer"], slot_deg=N["slot_deg"],
                 window=tuple(P["spring_window"]),
                 angles=dict(bearing_pocket=N["ang_bp"], bearing_hub=N["ang_bo"], inner_pocket=N["ang_E"], inner_hub=N["ang_io"]))
    return dict(margin=worst[0], at=worst[1], short_bend_deg=0.0, range_deg=tuple(b_range), short_tip_to_face_end=N["tip_to_end"],
                leg_z_at_boss_face=z_face, leg_y_at_boss_bottom=y_bot, leg_in_groove=bool(leg_ok), tip=sg0["tip_world"], tangent=Q, notch=notch)


def _wire_rect(a, b, d):
    L_ = math.hypot(b[0] - a[0], b[1] - a[1])
    ny, nz = -(b[1] - a[1]) / L_ * d / 2, (b[0] - a[0]) / L_ * d / 2
    return [(a[0] + ny, a[1] + nz), (b[0] + ny, b[1] + nz), (b[0] - ny, b[1] - nz), (a[0] - ny, a[1] - nz)]


def spring_insert_check(P, dp=0.0, t_max=12.0, dt=0.02, long_len=8.0):
    """r4.5 fix 2: assembly path of the free torsion spring into the lever's pocket section (lever frame, bench, no rod): the
    spring is held so that its short leg lies on the groove's centre line and is slid in ALONG the leg (tip first) through
    the insertion slot, from t = t_max to the seated position t = 0.  dp = groove printed that much wider (+) / narrower (-).
    Returns the smallest gap of each wire outline (coil OD circle, short leg, first long_len of the long leg at its free
    direction) to the two pieces A / B along the path, and whether the path is clear (all > 0)."""
    PP = P if dp == 0.0 else dict(P, spring_notch=(P["spring_notch"][0] + dp,) + tuple(P["spring_notch"][1:]))
    L = PP["L"]
    d, rmf = PP["spring_d"], PP["spring_rm"]
    A, B = hub_pocket_poly(PP, lever_web_poly(PP))
    N = spring_notch_geo(PP)
    ug, ng = N["u_g"], N["n_g"]
    cm = 0.5 * (N["c_o"] + N["c_i"])
    C = (L[0] + (cm - rmf) * ng[0], L[1] + (cm - rmf) * ng[1])
    Q = (C[0] + rmf * ng[0], C[1] + rmf * ng[1])
    ls = PP["spring_short_leg"]
    short = _wire_rect(Q, (Q[0] + ls * ug[0], Q[1] + ls * ug[1]), d)
    coil = circle(C, rmf + d / 2, 48)
    phl = math.atan2(ng[1], ng[0]) + math.radians(PP["spring_swept_free"] % 360.0)
    Ql = (C[0] + rmf * math.cos(phl), C[1] + rmf * math.sin(phl))
    ul = (math.cos(phl + math.pi / 2), math.sin(phl + math.pi / 2))
    longw = _wire_rect(Ql, (Ql[0] + long_len * ul[0], Ql[1] + long_len * ul[1]), d)
    per = {}
    for t in np.arange(0.0, t_max + 1e-9, dt):
        sh = lambda poly: [(q[0] - t * ug[0], q[1] - t * ug[1]) for q in poly]
        for nm_, piece in (("A", A), ("B", B)):
            for wn, w_ in (("short leg", short), ("coil", coil), ("long leg", longw)):
                g_ = poly_dist(sh(w_), piece)
                k_ = "%s|%s" % (wn, nm_)
                if k_ not in per or g_ < per[k_][0] - 1e-12:
                    per[k_] = (g_, float(t))
    gA = min((v for k, v in per.items() if k.endswith("|A")), key=lambda v: v[0])
    gB = min((v for k, v in per.items() if k.endswith("|B")), key=lambda v: v[0])
    ok = all(v[0] > 0.0 for v in per.values())
    return dict(gap_A=gA[0], at_A=gA[1:], gap_B=gB[0], at_B=gB[1:], clear=bool(ok), dp=dp, per=per, short_A=per["short leg|A"],
                long_free_dir=math.degrees(math.atan2(ul[1], ul[0])) % 360.0, slot_deg=N["slot_deg"], width=N["width"])


def spring_pose(P, b_deg, mode=None, it_max=400):
    """r4.5 fix 2 (verifier spring major): equilibrium of the loaded spring at lever angle b (lever frame).  The coil's mean
    radius follows the wind (spring_rm_w); the long leg's tip is fixed on the rear-wall groove floor (reaction along world
    -y, arm = its lever about the coil centre).
      mode 'capture' (r4.5 fix 2): the short leg is held in its narrow groove at the design pose (two contacts, a couple);
        the coil is tangent to that fixed leg line, so its centre is L + (rm_rest - rm(w)) n0 - no net force reaches the rod.
      mode 'face' (r4.5 as first built): the short leg only bears on one face; the net leg force (face force on the short leg
        + groove force on the long leg) pushes the coil onto the rod (radial clearance (ID(w) - rod) / 2), the short leg
        leaves its face and the spring unwinds until the leg's tip corner is back on it; the rod reaction N rubs on the
        fixed rod as the lever turns (hysteresis mu_sr N r_rod).
    Returns w (deg), T (N mm), C (coil centre), theta (short-leg unwind, deg), N_rod, rod gap left, contact forces."""
    mode = P.get("spring_mode", "capture") if mode is None else mode
    L = P["L"]
    d, kt = P["spring_d"], P["spring_kt"]
    b = math.radians(b_deg)
    (ytip, ztip), _, _ = spring_anchor(P)
    Tl = rot((ytip, ztip), L, b)
    ey = (-math.cos(b), -math.sin(b))                  # world -y in the lever frame
    sl = spring_short_leg_lf(P)
    a0 = math.radians(sl["alpha_s"])
    n0 = (math.cos(a0), math.sin(a0))
    rm_r = sl["rm"]
    ls = P["spring_short_leg"]

    def tan_ang(C, rm):
        v = (Tl[0] - C[0], Tl[1] - C[1])
        return math.atan2(v[1], v[0]) - math.acos(rm / math.hypot(*v))

    def wind(C, a, rm):
        return (math.degrees(tan_ang(C, rm) - a) % 360.0) + 1080.0 - P["spring_swept_free"]
    C, th = (L[0], L[1]), 0.0
    w = wind(C, a0, rm_r)
    e = (-n0[0], -n0[1])
    Fs = Fl = Fn = 0.0
    gap = 0.0
    for _ in range(it_max):
        rm = spring_rm_w(P, w)
        gap = rm - d / 2 - P["rod_L"] / 2
        T = kt * math.radians(max(w, 0.0))
        if mode == "capture":
            Cn, thn = (L[0] + (rm_r - rm) * n0[0], L[1] + (rm_r - rm) * n0[1]), 0.0
        else:
            nt = (math.cos(a0 + th), math.sin(a0 + th))
            ut = (math.sin(a0 + th), -math.cos(a0 + th))
            pc = (C[0] + (rm + d / 2) * nt[0] + ls * ut[0], C[1] + (rm + d / 2) * nt[1] + ls * ut[1])
            arm_s = abs((pc[0] - C[0]) * (-n0[1]) - (pc[1] - C[1]) * (-n0[0]))
            arm_l = abs((Tl[0] - C[0]) * ey[1] - (Tl[1] - C[1]) * ey[0])
            Fs, Fl = T / arm_s, T / arm_l
            Fv = (-Fs * n0[0] + Fl * ey[0], -Fs * n0[1] + Fl * ey[1])
            Fn = math.hypot(*Fv)
            if Fn > 1e-9:
                e = (Fv[0] / Fn, Fv[1] / Fn)
            Cn = (L[0] + max(gap, 0.0) * e[0], L[1] + max(gap, 0.0) * e[1])
            dn = (Cn[0] - L[0]) * n0[0] + (Cn[1] - L[1]) * n0[1]
            c_f = P.get("spring_face_off", rm_r + d / 2)
            f = lambda t_: dn + (rm + d / 2) * math.cos(t_) + ls * math.sin(t_) - c_f
            lo, hi = -0.6, 0.9
            for _k in range(70):
                mid = 0.5 * (lo + hi)
                if f(mid) > 0:
                    hi = mid
                else:
                    lo = mid
            thn = 0.5 * (lo + hi)
        wn = wind(Cn, a0 + thn, rm)
        done = abs(wn - w) < 1e-10 and math.hypot(Cn[0] - C[0], Cn[1] - C[1]) < 1e-12
        C, th, w = Cn, thn, (wn if done else 0.5 * (w + wn))
        if done:
            break
    rm = spring_rm_w(P, w)
    T = kt * math.radians(max(w, 0.0))
    off = math.hypot(C[0] - L[0], C[1] - L[1])
    gap_left = rm - d / 2 - P["rod_L"] / 2 - off
    N_rod = Fn if (mode != "capture" and w > 0) else 0.0
    out = dict(b=b_deg, mode=mode, w=w, T=T, C=C, off=off, theta=math.degrees(th), rm=rm, gap=gap, gap_left=gap_left, N_rod=N_rod,
               dir=math.degrees(math.atan2(e[1], e[0])) % 360.0, Fs=Fs, Fl=Fl)
    if mode == "capture":
        N_ = spring_notch_geo(P)
        out.update(F_couple=T / N_["arm"], arm=N_["arm"], Fl=T / abs((Tl[0] - C[0]) * ey[1] - (Tl[1] - C[1]) * ey[0]) if T > 0 else 0.0)
    return out


def spring_capture_tol(P, dp):
    """r4.5 fix 2: the short-leg groove printed dp wider (+) / narrower (-) than drawn (both faces moved dp/2): in the band frame the
    leg lies at theta(p) with d cos theta + (ls - s_E) sin theta = d + p; printed wider it cocks dtheta = theta(play + dp) -
    theta(play) further CCW (the spring unwinds that much: rest torque change -k_t dtheta), narrower it is wound tighter; below
    play + dp = 0 the 0.5 wire does not go in (feasible False).  The coil centre moves <= |dp| / 2 + s_E |dtheta| off the axis
    (rod gap left).  No geometry is rebuilt (the printed band stays where it was drawn)."""
    N0 = spring_notch_geo(P)
    d, ls = P["spring_d"], P["spring_short_leg"]
    play = P["spring_notch"][0]
    sE = N0["s_leg_E"]
    B_ = ls - sE
    R_ = math.hypot(d, B_)

    def th(p):
        return math.degrees(math.asin(min(1.0, (d + p) / R_)) - math.atan2(d, B_))
    feasible = play + dp >= 0.0
    dth = th(max(play + dp, 0.0)) - th(play)
    off = abs(dp) / 2 + sE * abs(math.radians(dth))
    r0 = spring_pose(P, 0.0)
    return dict(dp=dp, feasible=feasible, dtheta=dth, dT=-P["spring_kt"] * math.radians(dth), T0=r0["T"] - P["spring_kt"] * math.radians(dth),
                off=off, gap_left=r0["gap_left"] - off, play=play + dp)


def spring_keyless_leg(P, b_drop, lever_float=0.0, free_tol=(0.0, 5.0, -5.0)):
    """r4.5 fix 2 (verifier spring minors 2): the long leg of a lever whose key is out (lever at b_drop deg).  Below the free angle
    the unloaded spring turns with the lever; unloaded, the captured coil can also (a) slide along its short-leg groove - toward
    the blind end by spring_notch[2], back toward the pocket until the coil (free ID) sits on the rod - and across it by the play,
    (b) cock in the groove by +-theta_c, and (c) slide axially in the pocket ((pocket - (n + 1) d) / 2 each way); the lever
    itself floats axially by lever_float.  Returns per free-angle tolerance the worst y of the leg tip past the groove mouth
    (tip centre - mouth y, > 0 = inside) and, in x, the worst leg-centre offset from the groove centre (x + spring_groove_dx)
    against what the groove catches (half width + lead-in - wire radius)."""
    L = P["L"]
    d, sg = P["spring_d"], P["spring_groove"]
    N = spring_notch_geo(P)
    ug, ng = N["u_g"], N["n_g"]
    play, e_clr = P["spring_notch"][0], P["spring_notch"][2]
    rod_gap = (P["spring_ID"] - P["rod_L"]) / 2                     # free coil on the rod
    a_ax = (P["spring_pocket"][1] - (P["spring_n"] + 1) * d) / 2
    th = N["theta_c"]
    out = {}
    b = math.radians(b_drop)
    for tol in free_tol:
        bf = math.radians(P["spring_free_deg"] + tol)
        worst = None
        for cock in (-th, 0.0, th):
            for s_ in (-rod_gap, 0.0, e_clr):
                for c_ in (-play / 2, 0.0, play / 2):
                    sgk = spring_geometry(P, b, bf=bf)
                    tip = sgk["long_leg"][1]
                    # float in the lever frame: rotate about the coil centre (cock), translate along / across the band
                    tl = rot(tip, L, b)                                 # world -> lever frame
                    tl = rot(tl, L, -math.radians(cock))
                    tl = (tl[0] + s_ * ug[0] + c_ * ng[0], tl[1] + s_ * ug[1] + c_ * ng[1])
                    tw = rot(tl, L, -b)
                    loaded = b >= bf
                    ins = (sg[0] + sg[4] - d / 2 - sg[0]) if loaded else tw[0] - sg[0]
                    if worst is None or ins < worst[0]:
                        worst = (ins, cock, s_, c_, tw)
        out["%+.0f" % tol] = dict(free=P["spring_free_deg"] + tol, loaded=b >= bf, in_mouth=worst[0], cock=worst[1], slide=worst[2], across=worst[3], tip=worst[4])
    catch = sg[3] / 2 + P["spring_lead_in"] - d / 2
    x_off = a_ax + lever_float
    x_off_r44 = x_off + P.get("spring_groove_dx", 0.0)                 # groove on the lever centre (r4.5 as first built)
    return dict(b=b_drop, cases=out, catch=catch, coil_axial=a_ax, lever_float=lever_float, x_off=x_off, x_margin=catch - x_off,
                x_margin_centred_on_lever=catch - x_off_r44, rod_gap=rod_gap, theta_c=th)


_SPRING_TAB = {}


def spring_T_table(P, mode=None):
    """r4.5 fix 2: T(b) and the coil-on-rod force N(b) of spring_pose over b = -45..40 deg (cached per spring geometry)."""
    mode = P.get("spring_mode", "capture") if mode is None else mode
    key = (mode, P["spring_kt"], P["spring_free_deg"], P.get("spring_rm_rest"), P["spring_short_leg"], tuple(P["spring_notch"]), tuple(P["spring_groove"]),
           P["spring_leg"], P["spring_ID"], P["spring_n"], P.get("spring_face_off"), tuple(P["L"]), P.get("spring_notch_rot", 0.0), P.get("spring_rm"))
    if key not in _SPRING_TAB:
        bs = np.arange(-45.0, 40.0 + 1e-9, 0.25)
        rs = [spring_pose(P, float(b_), mode) for b_ in bs]
        _SPRING_TAB[key] = (bs, np.array([r["T"] for r in rs]), np.array([r["N_rod"] for r in rs]))
    return _SPRING_TAB[key]


def pocket_section_removed(P):
    """r4.5: PETG removed from the hub + web over the pocket section (x +-pocket/2) relative to a full hub ring (R hub_R, bore
    rod_L) + the web polygon: pocket, slot, short-leg groove, web-underside cut.  Returns (area mm2, centroid (y, z))."""
    L = P["L"]
    Ro, rb = P["hub_R"], P["rod_L"] / 2
    web = lever_web_poly(P)
    a_ring = math.pi * (Ro ** 2 - rb ** 2)
    aw, cw_ = poly_area_centroid(web)
    aq = math.pi * Ro ** 2 / 4                      # web polygon overlaps the ring's upper-front quadrant (90..180 deg)
    cq = (L[0] - 4 * Ro / (3 * math.pi), L[1] + 4 * Ro / (3 * math.pi))
    full_a = a_ring + aw - aq
    full_m = (a_ring * L[0] + aw * cw_[0] - aq * cq[0], a_ring * L[1] + aw * cw_[1] - aq * cq[1])
    pa, pm = 0.0, [0.0, 0.0]
    for pc in hub_pocket_poly(P, web):
        a_, c_ = poly_area_centroid(pc)
        pa += a_
        pm[0] += a_ * c_[0]
        pm[1] += a_ * c_[1]
    ra = full_a - pa
    return ra, ((full_m[0] - pm[0]) / ra, (full_m[1] - pm[1]) / ra)


def spring_mass(P):
    """r4.5: one cut spring: coil n_body turns on the mean diameter + both legs (g)."""
    rm, d = P["spring_rm"], P["spring_d"]
    l_long = math.sqrt(P["spring_leg"] ** 2 - rm ** 2)
    Lw = P["spring_n"] * 2 * math.pi * rm + l_long + P["spring_short_leg"]
    return Lw * math.pi / 4 * d * d * RHO_SUS, Lw


def _section_z_intervals(poly, y):
    """z intervals where the vertical line at y is inside the polygon (even-odd)."""
    zs = []
    n = len(poly)
    for i in range(n):
        (y0, z0), (y1, z1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            zs.append(z0 + (y - y0) * (z1 - z0) / (y1 - y0))
    zs.sort()
    return [(zs[k], zs[k + 1]) for k in range(0, len(zs) - 1, 2)]


def hub_notch_stress(P, RL, T_sp, Kt=2.0):
    """r4.5 / r4.5 fix 2: strength of the lever's hub / web where the captured short-leg groove runs from the pocket section
    through the hub wall into the web (the carrier prints on its side: x = build direction, so bending in (y, z) is IN the
    layers).  Vertical sections y over the groove (blind end .. pocket): outer hub + web (2 x (lever_w - pocket) / 2 wide,
    full) + the pocket-section pieces (their z intervals); bending moment = |RL| x distance from the rod axis to the
    section's neutral axis + the spring couple; sigma = M c / I (x Kt at the groove's sharp corners), also without the
    groove.  The two leg contacts (F = T / arm, the leg tip on the outer face and the leg on the inner face's pocket edge) are
    both on piece A, in the layer plane; piece B (the lower ring) carries no leg force.  The rod bears on the two full hub
    segments only (the pocket section has no bore contact)."""
    L = P["L"]
    Ro = P["hub_R"]
    hw, pw = P["lever_w"] / 2, P["spring_pocket"][1] / 2
    web = lever_web_poly(P)
    A, B = hub_pocket_poly(P, web)
    N = spring_notch_geo(P)
    y_lo = min(q[0] for q in N["band"]) - 0.3
    y_hi = max(N["E"][0], N["exit_inner"][0]) + 0.8
    worst = None
    for y in np.linspace(y_lo, y_hi, 61):
        full_iv = []
        dz = L[0] - y
        if abs(dz) <= Ro:
            h_ = math.sqrt(Ro ** 2 - dz ** 2)
            full_iv.append((L[1] - h_, L[1] + h_))
        full_iv += _section_z_intervals(web, y)
        lo_, hi_ = min(a for a, _ in full_iv), max(b for _, b in full_iv)
        rects = [(2 * (hw - pw), lo_, hi_)]                          # outer hub + web (both sides)
        for pc in (A, B):
            for a_, b_ in _section_z_intervals(pc, y):
                rects.append((2 * pw, a_, b_))
        rects_full = [(2 * hw, lo_, hi_)]

        def sec(rs):
            Aa = sum(w_ * (b_ - a_) for w_, a_, b_ in rs)
            zc = sum(w_ * (b_ - a_) * (a_ + b_) / 2 for w_, a_, b_ in rs) / Aa
            I_ = sum(w_ * (b_ - a_) ** 3 / 12 + w_ * (b_ - a_) * ((a_ + b_) / 2 - zc) ** 2 for w_, a_, b_ in rs)
            c_ = max(max(abs(b_ - zc), abs(a_ - zc)) for w_, a_, b_ in rs)
            return Aa, zc, I_, c_
        Aa, zc, I_, c_ = sec(rects)
        Af, zf, If, cf = sec(rects_full)
        M = abs(RL) * math.hypot(L[0] - y, L[1] - zc) + abs(T_sp)
        s = M * c_ / I_
        s0 = (abs(RL) * math.hypot(L[0] - y, L[1] - zf) + abs(T_sp)) * cf / If
        tau = 1.5 * abs(RL) / Aa
        q = dict(y=float(y), M=M, sigma=s, sigma_kt=Kt * s, sigma_full=s0, tau=tau, area=Aa, area_full=Af, I=I_, I_full=If, z=(lo_, hi_))
        if worst is None or q["sigma_kt"] > worst["sigma_kt"]:
            worst = q
    aB, _ = poly_area_centroid(B)
    F_c = abs(T_sp) / N["arm"]
    return dict(section=worst, Kt=Kt, piece_B_area=aB, F_short_leg=F_c, F_couple=F_c, arm=N["arm"], tau_B=0.0,
                contact_p=F_c / (P["spring_d"] * P["spring_d"]),
                hub_bearing=abs(RL) / (P["rod_L"] * 2 * (hw - pw)), hub_bearing_fullwidth=abs(RL) / (P["rod_L"] * 2 * hw))


def steel_poly(P):
    """steel block outline (lever frame), sawn square (r4: no chamfer)."""
    return rect(P["y_steel_front"], P["y_steel_rear"], P["z_sb"], P["z_st"])


def hub_collars(lay, P):
    """r4 (A5): the r3 printed C-rings between two levers become collars on the two hubs (half of the ring each);
    rings next to a fin stay the fin's boss.  Returns {lever: (left collar, right collar)}."""
    rings = spacer_rings(lay, P)
    col = {nm: [0.0, 0.0] for nm in lay["levers"]}
    for r in rings:
        a, b = r["between"]
        if a != "fin" and b != "fin":
            # r4.4 fix 2: never below collar_min (the pair sums to >= ring_min); a free gap of >= 0.04 stays between the pair
            cc = min(r["gap"] / 2 - 0.02, max(P.get("collar_min", 0.0), r["length"] / 2 - P.get("collar_short", 0.0)))
            col[a][1] = round(cc, 3)
            col[b][0] = round(cc, 3)
    return {k: tuple(v) for k, v in col.items()}


def lever_float(lay, P, collars):
    """r4.4 fix 2 (verifier geometry major 4): each lever's one-sided axial float on the rod (left, right) from the gap chain
    between the fin bosses of its bay (hub faces incl. collars), and the free gap between two neighbouring levers of a bay
    (their facing collars / hubs): {lever: (float left, float right)}, {(left lever, right lever): gap}."""
    hw = P["lever_w"] / 2
    bl = fin_boss_len(lay, P)
    fins = lay["fins"]
    levs = sorted(lay["levers"].items(), key=lambda kv: kv[1])
    out, pair = {}, {}
    for i in range(len(fins) - 1):
        lo = fins[i][1] + bl[i][1]
        hi = fins[i + 1][0] - bl[i + 1][0]
        bay = [(nm, x) for nm, x in levs if fins[i][1] < x < fins[i + 1][0]]
        if not bay:
            continue
        faces = [(nm, x - hw - collars[nm][0], x + hw + collars[nm][1]) for nm, x in bay]
        gaps = [faces[0][1] - lo] + [faces[k + 1][1] - faces[k][2] for k in range(len(faces) - 1)] + [hi - faces[-1][2]]
        gaps = [max(0.0, q) for q in gaps]
        for k, (nm, a, b) in enumerate(faces):
            out[nm] = (sum(gaps[:k + 1]), sum(gaps[k + 1:]))
        for k in range(len(faces) - 1):
            pair[(faces[k][0], faces[k + 1][0])] = gaps[k + 1]
    return out, pair


def fin_boss_len(lay, P):
    """(left, right) boss length on each fin = the lever-fin ring it replaces (one-sided at the module / part ends)."""
    rings = spacer_rings(lay, P)
    out = []
    for i in range(len(lay["fins"])):
        left = [r["length"] for r in rings if r["between"][1] == "fin" and abs(r["x0"] + r["length"] - lay["fins"][i][0]) < 0.6 * r["gap"] + 0.5]
        right = [r["length"] for r in rings if r["between"][0] == "fin" and abs(r["x0"] - lay["fins"][i][1]) < 1e-6]
        # r4.4 fix 2: every boss boss_extra longer than its ring (the lever floated onto its boss and yawed kept 1.30 to the fin)
        ex_ = P.get("boss_extra", 0.0)
        out.append((left[0] + ex_ if left else 0.0, right[0] + ex_ if right else 0.0))
    return out


def bays(fins):
    """fin bays (x ranges between consecutive fins)."""
    return [(a[1], b[0]) for a, b in zip(fins[:-1], fins[1:])]


def pad_face_z(pt, y):
    """world z of a pad face (PadTable) at world y."""
    t, ref = pt.t, pt.ref
    return ref[1] + (y - ref[0]) * t[1] / t[0]


def pad_polys(P, g, black, pt=None):
    """(pad, wedge) side polygons of one pad (world): foam + felt below the wedge seat, wedge up to the pad bar.
    r4.2: pt = the key's own pad face (end-part keys: face at their own settled bottom, so the wedge differs)."""
    pt = (g["pad_b"] if black else g["pad_w"]) if pt is None else pt
    y0, y1 = P["pad_y"]
    n = pt.n
    h = P["pad_h"]
    zf0, zf1 = pad_face_z(pt, y0), pad_face_z(pt, y1)
    # pad = parallelogram along the face normal
    pad = [(y0, zf0), (y1, zf1), (y1 + h * n[0], zf1 + h * n[1]), (y0 + h * n[0], zf0 + h * n[1])]
    zb = g["z_seat"] - P["pad_bar_t"]
    wedge = [(y0 + h * n[0], zf0 + h * n[1]), (y1 + h * n[0], zf1 + h * n[1]), (y1 + h * n[0], zb), (y0 + h * n[0], zb)]
    return pad, wedge


def front_parts(P, g, keys, order):
    """white front rail + felt, black stop rails / felts / tab bases, guide tabs (+0.5T cloth), keepers."""
    F = []
    (y1, z1), (y2, z2) = g["w_felt_line"]
    kh = P["keeper_half"]
    zk = g["z_keep"]
    for nm in order:
        kd = keys[nm]
        gc = kd["guide_c"]
        if not kd["black"]:
            tw = P["tab_w"] / 2
            F.append(("tab " + nm, gc - tw, gc + tw, rect(P["w_tab_y"][0], P["w_tab_y"][1], z2 - 3.0, zk + P["keeper_felt"] + P["hook_t"])))
            F.append(("keeper hook " + nm, gc - kh, gc + kh, [(P["w_hook_y"][0], zk + P["keeper_felt"]), (P["w_hook_y"][1], zk + P["keeper_felt"]),
                                                              (P["w_tab_y"][0], zk + P["keeper_felt"] - 2.3 + P["hook_t"]),
                                                              (P["w_tab_y"][0], zk + P["keeper_felt"] + P["hook_t"]),
                                                              (P["w_hook_y"][0], zk + P["keeper_felt"] + P["hook_t"])]))
            F.append(("keeper felt " + nm, gc - kh, gc + kh, rect(P["w_hook_y"][0], P["w_hook_y"][1], zk, zk + P["keeper_felt"])))
        else:
            (b1y, b1z), (b2y, b2z) = g["b_felt_line"]
            x0, x1 = kd["head"]
            tw = P["tab_w_b"] / 2
            F.append(("black stop rail " + nm, x0 - 0.5, x1 + 0.5, [(51.0, 5.0), (59.0, 5.0), (59.0, b2z - 3.0), (b2y, b2z - 3.0), (b1y, b1z - 3.0), (51.0, b1z - 3.0)]))
            F.append(("black front felt " + nm, x0, x1, [(b1y, b1z - 3.0), (b2y, b2z - 3.0), (b2y, b2z), (b1y, b1z)]))
            F.append(("black tab base " + nm, gc - 4.0, gc + 4.0, rect(P["b_tab_base_y"][0], P["b_tab_base_y"][1], 5.0, 12.0)))
            F.append(("tab " + nm, gc - tw, gc + tw, rect(P["b_tab_y"][0], P["b_tab_y"][1], 12.0, zk + P["keeper_felt"] + P["hook_t"])))
            F.append(("keeper hook " + nm, gc - kh, gc + kh, rect(P["b_hook_y"][0], P["b_hook_y"][1], zk + P["keeper_felt"], zk + P["keeper_felt"] + P["hook_t"])))
            F.append(("keeper felt " + nm, gc - kh, gc + kh, rect(P["b_hook_y"][0], P["b_hook_y"][1], zk, zk + P["keeper_felt"])))
    return F


def plate_poly(P, g, y_front=None):
    """side section of the top plate: underside (front zone + pad zone flat at the pad-bar seat, then the lever envelope
    + 1.3 capped at plate_rear_max), top z_top, rabbet for the curtain hook at the front top edge."""
    y0 = P["ledge_y0"] if y_front is None else y_front
    zt = g["z_top"]
    hk_y, hk_d = P["curtain_hook"]
    under = [(y, z) for y, z in plate_under_exact(P, g) if y0 <= y <= P["rear_wall"][0]]
    return [(y0, under[0][1]), (y0, zt - hk_d), (y0 + hk_y, zt - hk_d), (y0 + hk_y, zt), (P["rear_wall"][0], zt)] + under[::-1][:-1] + \
           [(under[0][0], under[0][1])]


def plate_under_exact(P, g):
    """r4.2: the sampled plate underside (0.5 mm, used by the FE) with the two steps made vertical faces: channel end at
    y_bar_step (z seat + bar -> z seat) and the pads' rear stop at plate_step_y (z seat -> rear zone).  The drafter measured
    the sampled 0.5 mm ramps as step faces."""
    out = []
    ys_, ps_ = g["y_bar_step"], P.get("plate_step_y", P["pad_bar_y"][1])
    prof = g["plate_under"]
    for i, (y, z) in enumerate(prof):
        out.append((y, z))
        if i + 1 < len(prof):
            y2, z2 = prof[i + 1]
            for yst in (ys_, ps_):
                if y < yst < y2 + 1e-9 and abs(z2 - z) > 1e-6 and abs(y - yst) > 1e-9:
                    if abs(y2 - yst) < 1e-9:
                        out.append((yst, z))          # vertical face at the next sample
                    else:
                        out.append((yst, z))
                        out.append((yst, z2))
                elif abs(y - yst) < 1e-9 and abs(z2 - z) > 1e-6:
                    out.append((y, z2))               # step exactly on a sample: vertical face there
    # drop duplicate consecutive points
    res = [out[0]]
    for q in out[1:]:
        if abs(q[0] - res[-1][0]) > 1e-9 or abs(q[1] - res[-1][1]) > 1e-9:
            res.append(q)
    return res


def usb_slot(P):
    """r4.3: x range of the open slot in the rear shelf over the USB-C plug (plug envelope -+ usb_clear)."""
    return P["usb_x"][0] - P["usb_clear"], P["usb_x"][1] + P["usb_clear"]


def rest_landing(P, g, levers=None):
    """r4.3: part of each key's rest felt (lever x +- beam_w/2, y rest_pad_y) that lands on the rear shelf, which is cut
    by the USB slot.  {key: dict(segs, frac, xc, dx)}; dx = landing centroid - lever x (rest reaction offset)."""
    s0, s1 = usb_slot(P)
    out = {}
    for nm, xl in (g["lay"]["levers"] if levers is None else levers).items():
        # r4.4: the felt's own x range (cut at the slot edge / widened to the tail edge + foot beside the slot)
        (a, b), _ = rest_pad_x(P, nm, xl, g["keys"][nm]["black"])
        segs = [(u, v) for u, v in ((a, min(b, s0)), (max(a, s1), b)) if v - u > 1e-9]
        wd = sum(v - u for u, v in segs)
        xc = sum((u + v) / 2 * (v - u) for u, v in segs) / wd if wd > 0 else xl
        # frac = landed width / the 8.0 felt of the dynamics (the contact law K is per 8.0 felt)
        out[nm] = dict(segs=segs, frac=wd / P["beam_w"], xc=xc, dx=xc - xl, felt=(a, b))
    return out


def board_parts(P):
    """r4.3: the control-board parts of the circuit session's BRD-01 placement as envelopes (inside the generic
    component envelope; the sweep and the fixed-fixed checks see them by name)."""
    zb = P["board_z"][1]
    zx0, zx1, zy0, zy1 = P["zero_xy"]
    rx0, rx1, ry0, ry1, rz0, rz1 = P["usb_rcpt"]
    mx0, mx1, my0, my1 = P["mux_xy"]
    px0, px1, py0, py1 = P["ribbon_pads"]
    ex0, ex1, ey = P["ext_pads"]
    pr_ = P["board_pad_r"]
    rx0_, rx1_ = ribbon_x_under_board(P)
    uz0, uz1 = P["ribbon_under_z"]
    # r4.4 (circuit cross-check 1): J301 soldered from the underside - on top only its joints (<= ribbon_z); the 16-core
    # ribbon runs UNDER the board (z5-9) from the rail's rear face (lane exit) to the block
    return [("board part: RP2040-Zero on pin headers (PCB z%.1f-%.1f, top parts <= z%.1f)" % P["zero_z"], zx0, zx1, rect(zy0, zy1, zb, P["zero_z"][2])),
            ("board part: USB-C receptacle of the RP2040-Zero (centre z%.1f)" % (0.5 * (rz0 + rz1)), rx0, rx1, rect(ry0, ry1, rz0, rz1)),
            ("board part: CD74HC4067 module on pin headers (<= z%.0f)" % P["comp_zmax"], mx0, mx1, rect(my0, my1, zb, P["comp_zmax"])),
            ("board part: J301 ribbon 2x8 pads (ribbon soldered from the underside, joints <= z%.1f)" % P["ribbon_z"], px0 - pr_, px1 + pr_, rect(py0 - pr_, py1 + pr_, zb, P["ribbon_z"])),
            ("board part: J301 %d-core ribbon under the board (z%.0f-%.0f)" % (P["ribbon_cores"], uz0, uz1), rx0_, rx1_, rect(P["rail_y"][1], py1 + pr_, uz0, uz1)),
            ("board part: J302 EXT 1x6 pads (lead from the underside)", ex0 - pr_, ex1 + pr_, rect(ey - pr_, ey + pr_, zb, P["ext_z"]))]


def ribbon_x_under_board(P):
    """r4.4: x envelope of the 16-core ribbon between the lane exit and J301: centred on SB J201 (ribbon_xc) in the lane,
    its last ribbon_j301[1] mm shifted ribbon_j301[0] toward the J301 centre."""
    wr = P["ribbon_cores"] * P["ribbon_pitch"]
    xc = P["ribbon_xc"]
    xj = 0.5 * (P["ribbon_pads"][0] + P["ribbon_pads"][1])
    sh = xj - xc
    return min(xc, xc + sh) - wr / 2, max(xc, xc + sh) + wr / 2


def board_boss_rects(P, z_shelf_under=18.05):
    """r4.4 fix 2b: plan rectangles (x0, x1, y0, y1, z0, z1, kind, x, y, attach) of the four hung control-board bosses: the boss
    D standoff_d over each board hole joined by a bracket to the balance rail's rear face (front) or to the shelf rib's front
    face and the shelf underside (rear)."""
    r = P["standoff_d"] / 2
    zb1 = P["board_z"][1]
    out = []
    for x, y, kind in P["board_standoffs"]:
        if y < 0.5 * (P["board_y"][0] + P["board_y"][1]):
            out.append((x - r, x + r, P["rail_y"][1], y + r, zb1, P["board_boss"][0], kind, x, y, "balance rail rear face y%.1f" % P["rail_y"][1]))
        else:
            out.append((x - r, x + r, y - r, P["rib_y0"], zb1, z_shelf_under, kind, x, y, "shelf rib front face y%.1f + shelf underside z%.2f" % (P["rib_y0"], z_shelf_under)))
    return out


def board_standoff_prisms(P, g=None):
    """r4.4 (circuit cross-check 3): the 4 control-board stand-offs printed with the frame (D6, floor to the board
    underside) and what sits on them: 2 x M3x6 socket-head cap screws (head on the board top) / 2 printed locating pins
    (through the board, board_pin[1] above it).  Prisms are the plan squares around the circles (conservative); the
    exact plan distances are in circuit_c44_checks().
    r4.4 fix 2b (board_mount 'hung'): bosses hanging above the board (board_boss_rects), screws from below (head under the
    board), pins hanging down through the board holes."""
    zf, zb0, zb1 = P["z_floor"][1], P["board_z"][0], P["board_z"][1]
    r = P["standoff_d"] / 2
    hd, hk, _ = P["board_screw"]
    pd, ph = P["board_pin"]
    F = []
    if P.get("board_mount") == "hung":
        zsu = (g["z_shelf"] - 2.0) if g is not None else P["shelf_z"][0]
        for x0, x1, y0, y1, z0, z1, kind, x, y, att in board_boss_rects(P, zsu):
            if kind == "screw":
                F.append(("control-board boss D%.0f hung over the board (frame, bracket to the %s; screw bore D%.1f to z%.1f)" % (P["standoff_d"], att.split(" y")[0].split(" +")[0], P["standoff_bore"][0], P["board_boss"][1]),
                          x0, x1, rect(y0, y1, z0, z1)))
                F.append(("control-board screw M3x6 head D%.1f x %.1f envelope (from below, under the board)" % (hd, hk), x - hd / 2, x + hd / 2, rect(y - hd / 2, y + hd / 2, zb0 - hk, zb0)))
            else:
                F.append(("control-board boss D%.0f hung over the board (frame, bracket to the %s; locating pin)" % (P["standoff_d"], att.split(" y")[0].split(" +")[0]), x0, x1, rect(y0, y1, z0, z1)))
                F.append(("control-board locating pin D%.1f (frame, hanging through the board, tip z%.1f)" % (pd, zb0 - ph), x - pd / 2, x + pd / 2, rect(y - pd / 2, y + pd / 2, zb0 - ph, zb1)))
        return F
    for x, y, kind in P["board_standoffs"]:
        if kind == "screw":
            F.append(("control-board stand-off D%.0f (frame; screw boss, bore D%.1f to z%.1f)" % (P["standoff_d"], P["standoff_bore"][0], P["standoff_bore"][1]),
                      x - r, x + r, rect(y - r, y + r, zf, zb0)))
            F.append(("control-board screw M3x6 head D%.1f x %.1f envelope (ISO 7380 L35 / DIN 912, on the board)" % (hd, hk), x - hd / 2, x + hd / 2, rect(y - hd / 2, y + hd / 2, zb1, zb1 + hk)))
        else:
            F.append(("control-board stand-off D%.0f (frame; with locating pin)" % P["standoff_d"], x - r, x + r, rect(y - r, y + r, zf, zb0)))
            F.append(("control-board locating pin D%.1f (frame, through the board, top z%.1f)" % (pd, zb1 + ph), x - pd / 2, x + pd / 2, rect(y - pd / 2, y + pd / 2, zb0, zb1 + ph)))
    return F


def keel_front(P):
    """r4.5 fix 2 (resume): front edge y of the F|F# (keel) fin = where the keel meets it (fin_y[0] before)."""
    return P.get("fin_keel_front") or P["fin_y"][0]


def fin_poly(P, g, over_board, over_usb, end_notch):
    """fin side section: y152 (0.1 thinner extension to fin_main_y0) .. 209, from the floor (or above the board parts /
    the shelf over the USB plug) up to the plate underside; module-end and seam fins notched over the dovetail zone."""
    zs = g["z_shelf"]
    fy_ext, fy1 = P["fin_y"]
    fy0 = P["fin_main_y0"]
    zlow = P["comp_zmax"] + 1.5 if over_board else P["z_floor"][1]
    yb = P["rib_y0"] if over_board else fy0
    gy = P.get("fin_slot_y") if over_board else None
    # r4.3: a fin over the USB tunnel no longer stands on the (now cut) shelf: it hangs from the plate and the rear wall
    # at max(zlow, plug top + usb_clear) all the way back (F|F# fin: z21.5, 3.2 above the plug)
    zrear = max(zlow, P["usb_z"][1] + P["usb_clear"]) if over_usb else P["z_floor"][1]
    top = [(y, z) for y, z in g["plate_under"] if fy0 <= y <= fy1]
    if end_notch:
        # r4: module-end / seam fins stop 1.3 in front of and 1.7 above the neighbour's dovetail groove (r3 0.3 / 0.6)
        dv = (196.7, 19.0)
        main = [(fy0, P["z_floor"][1]), (dv[0], P["z_floor"][1]), (dv[0], dv[1]), (fy1, dv[1])]
    elif abs(zrear - zlow) < 1e-9:
        main = [(fy0, zlow), (fy1, zlow)]
    else:
        main = [(fy0, zlow), (yb, zlow), (yb, zrear), (fy1, zrear)]
    main = main + top[::-1]
    topx = [(y, z) for y, z in g["plate_under"] if fy_ext <= y <= fy0]
    if gy is not None and P.get("board_hatch") and P.get("fin_keel_front"):
        # r4.5 fix 2 (resume): the F|F# (keel) fin starts at fin_keel_front, full height from the floor underside to the plate
        fy_ext = P["fin_keel_front"]
        zfe = float(np.interp(fy_ext, [q[0] for q in g["plate_under"]], [q[1] for q in g["plate_under"]]))
        topx = [(fy_ext, zfe)] + [(y, z) for y, z in g["plate_under"] if fy_ext + 1e-6 < y <= fy0]
    if gy is not None:
        # r4.1: grounded through the board slot over gy, hung (z21.5) behind it
        # r4.4 fix 2b: the floor under the board is open (board_hatch): the foot runs down to the floor's underside z3 and is
        # grounded by the keel (fixed_prisms) to the balance rail, not by a floor under it
        zft = P["z_floor"][0] if P.get("board_hatch") else P["z_floor"][1]
        ext = [(fy_ext, zft), (gy[1], zft), (gy[1], zlow), (fy0, zlow)] + topx[::-1]
    else:
        ext = [(fy_ext, zlow if over_board else P["z_floor"][1]), (fy0, zlow if over_board else P["z_floor"][1])] + topx[::-1]
    return main, ext


def top_parts(P, g, fins, levers, keys, x_plate, bays_=None, pads=None):
    """r4 up-stop and top: top plate (fused to fins and rear wall), per fin bay one stepped pad bar held by two dovetail
    rails under the plate: its front part (y146.5 - step) runs 1.5 higher in a channel of the plate (clears the lever
    front at ff), its pad part (step - rear) carries one pad per lever on a printed wedge; a 3 mm grip at the front edge;
    the loose curtain strip hooked over the plate's front edge."""
    F = []
    F.append(("top plate (ledge + bridge)", x_plate[0], x_plate[1], plate_poly(P, g)))
    zs_ = g["z_seat"]
    t = P["pad_bar_t"]
    by0, by1 = P["pad_bar_y"]
    ys_ = g["y_bar_step"]
    yj = g["y_bar_joggle"]
    rw, rd = P["bar_rail"]
    lf_t, lf_w, lf_L, lf_pre = P["bar_leaf"]
    ly0, ly1 = P["bar_leaf_y"]
    sl = P["bar_leaf_slot"]
    zlt = zs_ - t - P["bar_leaf_gap"]                  # lip top
    zlb = zs_ - rd                                     # lip / rail bottom
    # r4.2: bar profile with its joggle 1.0 in front of the plate's channel end
    bar_full = [(by0, zs_), (yj - t, zs_), (yj - t, zs_ - t), (by1, zs_ - t), (by1, zs_), (yj, zs_), (yj, zs_ + t), (by0, zs_ + t)]
    bar_front = [(by0, zs_), (yj - t, zs_), (yj - t, zs_ - t), (ly0 - sl, zs_ - t), (ly0 - sl, zs_), (yj, zs_), (yj, zs_ + t), (by0, zs_ + t)]
    for xa, xb in (bays(fins) if bays_ is None else bays_):
        c = P["pad_bar_clear"]
        xa2, xb2 = xa + rw + c, xb - rw - c
        e_ = lf_w + sl                                  # edge strip that holds the leaf window
        F.append(("pad bar", xa2 + e_, xb2 - e_, bar_full))
        for xs0, xs1, xt0, xt1 in ((xa2, xa2 + e_, xa2, xa2 + lf_w), (xb2 - e_, xb2, xb2 - lf_w, xb2)):
            # edge strip: the bar outline minus the through window y(ly0 - slot)..ly1 around the tongue
            F.append(("pad bar (edge strip, front of the leaf window)", xs0, xs1, bar_front))
            F.append(("pad bar (edge strip, behind the leaf window)", xs0, xs1, rect(ly1, by1, zs_ - t, zs_)))
            F.append(("pad bar leaf (printed tongue, installed)", xt0, xt1, leaf_poly(P, g)))
        F.append(("pad bar grip", xa2, xb2, rect(by0, by0 + 1.0, zs_ + t - P["pad_bar_grip"], zs_)))
        # r4.1 (verifier geometry major 2): the rails run forward through the plate channel to y rail_y0; in the channel
        # they hang from its ceiling.  r4.2: L-rails - the web goes down to the lip bottom, the lip runs under the bar edge
        ry0 = P.get("rail_y0", ys_)
        ch_ = P.get("rail_front_chamfer", 0.0)
        rpoly = ([(ry0 + ch_, zlb), (by1, zlb), (by1, zs_), (ys_, zs_), (ys_, zs_ + t), (ry0, zs_ + t)] + ([(ry0, zlb + ch_)] if ch_ > 0 else [])
                 if ry0 < ys_ else rect(ys_, by1, zlb, zs_))
        for xr in (xa, xb - rw):
            F.append(("pad bar rail", xr, xr + rw, rpoly))
        lp = P.get("rail_lip", 0.0)
        if lp > 0:
            ly0_ = P.get("rail_lip_y0", ry0)
            F.append(("pad bar rail lip", xa + rw, xa + rw + lp, rect(ly0_, by1, zlb, zlt)))
            F.append(("pad bar rail lip", xb - rw - lp, xb - rw, rect(ly0_, by1, zlb, zlt)))
    for nm, xl in levers.items():
        pad, wedge = pad_polys(P, g, keys[nm]["black"], pt=(pads or {}).get(nm))
        F.append(("up-stop pad " + nm, xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, pad))
        F.append(("pad wedge " + nm, xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, wedge))
    return F


def leaf_poly(P, g):
    """r4.2: installed side outline of one pad-bar leaf tongue: root at y bar_leaf_y[1] (rear, one piece with the bar's
    rear strip), free tip at bar_leaf_y[0] carrying a bump that rests on the rail lip; the tongue is bent up by the
    preload (cantilever curve) - its bump bottom sits on the lip top z seat - bar - gap."""
    zs_, t = g["z_seat"], P["pad_bar_t"]
    lf_t, lf_w, lf_L, pre = P["bar_leaf"]
    y0, y1 = P["bar_leaf_y"]
    gap = P["bar_leaf_gap"]
    zb0 = zs_ - t                                     # tongue underside at the root
    yb = y0 + P["bar_leaf_bump"]
    zbump = zs_ - t - gap                             # installed bump bottom = lip top (free: gap + preload below)
    w = lambda y: pre * (3 * ((y1 - y) / (y1 - y0)) ** 2 - ((y1 - y) / (y1 - y0)) ** 3) / 2   # cantilever curve, w(tip) = preload
    n = 8
    ys = [y1 - (y1 - yb) * i / n for i in range(n + 1)]
    bot = [(y, zb0 + w(y)) for y in ys]
    top = [(y, zb0 + lf_t + w(y)) for y in ys + [y0]]
    return bot + [(yb, zbump), (y0, zbump)] + top[::-1]


def curtain_parts(P, g, x0, x1, black_x):
    cp = 0.0
    edges = [x0]
    for xc in black_x:
        edges += [xc - P["curtain_notch_half"], xc + P["curtain_notch_half"]]
    edges.append(x1)
    F = []
    zt = g["z_top"]
    hk_y, hk_d = P["curtain_hook"]
    for i in range(len(edges) - 1):
        zbot = g["z_curtain_b"] if i % 2 == 1 else g["z_curtain_w"]
        F.append(("cover curtain", edges[i] - cp, edges[i + 1] + cp, rect(P["curtain_y"][0], P["curtain_y"][1], zbot, zt)))
    F.append(("cover curtain hook", x0, x1, rect(P["curtain_y"][1], P["ledge_y0"] + hk_y, zt - hk_d, zt)))
    return F


def board_prisms(P, fins):
    """control board (stripboard) and its parts; r4.1: an open slot from the front edge for every fin over the board
    (fin +-board_slot_clear, to fin_slot_y[1] + 1), parts / wires keep board_slot_keepout from the fin."""
    bx0, bx1 = P["board_x"]
    by0, by1 = P["board_y"]
    gy = P.get("fin_slot_y")
    slots = [(f0, f1) for f0, f1 in fins if bx0 < 0.5 * (f0 + f1) < bx1] if gy else []
    F = []
    zb0, zb1 = P["board_z"]
    # r4.3 (BRD-01): <= comp_zmax up to comp_rear[0] (r4.2: to y190, then <= z15.5 for the v3 flat RP2040), <= comp_rear[1]
    # in the strip in front of the rear shelf; the named BRD-01 parts are added by board_parts()
    yr, zr = P["comp_rear"]
    yb0 = by0                                            # the stripboard itself starts at the board edge
    by0 = max(by0, P.get("comp_front_y", by0))          # r4.3: components start 1.3 behind the balance rail
    rear_nm = "board components, rear strip (<= z%.1f)" % zr
    if not slots:
        F.append(("control board", bx0, bx1, rect(yb0, by1, zb0, zb1)))
        F.append(("board components (<= z20)", bx0, bx1, rect(by0, yr, zb1, P["comp_zmax"])))
        F.append((rear_nm, bx0, bx1, rect(yr, by1, zb1, zr)))
        return F
    ys1 = P.get("board_slot_y1", gy[1] + 1.0)
    c, k = P["board_slot_clear"], P["board_slot_keepout"]
    xa = bx0
    for f0, f1 in slots:
        F.append(("control board", xa, f0 - c, rect(yb0, by1, zb0, zb1)))
        F.append(("control board (behind the fin slot)", f0 - c, f1 + c, rect(ys1, by1, zb0, zb1)))
        F.append(("board components (<= z20)", xa, f0 - k, rect(by0, yr, zb1, P["comp_zmax"])))
        F.append(("board components (<= z20)", f0 - k, f1 + k, rect(ys1 + k, yr, zb1, P["comp_zmax"])))
        xa = f1 + c
        xk = f1 + k
    F.append(("control board", xa, bx1, rect(yb0, by1, zb0, zb1)))
    F.append(("board components (<= z20)", xk, bx1, rect(by0, yr, zb1, P["comp_zmax"])))
    F.append((rear_nm, bx0, bx1, rect(yr, by1, zb1, zr)))
    if P.get("board_mount") == "hung":
        # r4.4 fix 2b: no component within 1.3 of a hung boss / bracket (square keep-outs; the BRD-01 parts are measured exactly)
        ko = [(q[0] - 1.3, q[1] + 1.3, q[2] - 1.3, q[3] + 1.3) for q in board_boss_rects(P)]
        out = []
        for f in F:
            if not f[0].startswith("board components"):
                out.append(f)
                continue
            ys_ = [p[0] for p in f[3]]
            zs_ = [p[1] for p in f[3]]
            for xa_, xb_, ya_, yb_ in _carve_rect(f[1], f[2], min(ys_), max(ys_), ko):
                out.append((f[0], xa_, xb_, rect(ya_, yb_, min(zs_), max(zs_))))
        F = out
    return F


def _carve_rect(x0, x1, y0, y1, holes):
    """plan rectangle minus rectangular holes -> list of rectangles (x slabs, y intervals)."""
    xs = sorted(set([x0, x1] + [h[0] for h in holes if x0 < h[0] < x1] + [h[1] for h in holes if x0 < h[1] < x1]))
    out = []
    for xa, xb in zip(xs[:-1], xs[1:]):
        xm = 0.5 * (xa + xb)
        iv = [(y0, y1)]
        for hx0, hx1, hy0, hy1 in holes:
            if hx0 < xm < hx1:
                nv = []
                for a, b in iv:
                    if hy1 <= a or hy0 >= b:
                        nv.append((a, b))
                    else:
                        if hy0 > a:
                            nv.append((a, hy0))
                        if hy1 < b:
                            nv.append((hy1, b))
                iv = nv
        out += [(xa, xb, a, b) for a, b in iv if b - a > 1e-6]
    return out


def spring_bosses(P, g, levers):
    """r4.1: printed boss on the rear-wall face around each torsion-spring groove (groove 2.0 deep from the boss face,
    bottom y209.8 unchanged), from z spring_boss[1] up to the plate underside.  r4.5: boss 4.4 wide, groove 2.4 wide x 3.2 deep
    (bottom y211.0, 1.0 of rear wall behind it)."""
    bw, zb, pr_ = P["spring_boss"]
    zu = min(z for y, z in g["plate_under"] if y >= P["rear_wall"][0] - pr_ - 0.5)
    out = []
    dx = P.get("spring_groove_dx", 0.0)            # r4.5 fix 2: boss and groove centred on the long leg (x + 0.8)
    for nm, xl in levers.items():
        out.append(("spring groove boss", xl + dx - bw / 2, xl + dx + bw / 2, rect(P["rear_wall"][0] - pr_, P["rear_wall"][0], zb, zu)))
    return out


def spring_groove_cuts(P, levers):
    """r4.5 fix 2 (drafter): the rear-wall spring-leg groove of every lever as a female cut (x range, side outline (y, z)) and the
    entry chamfer spring_lead_in x 45 deg on the groove's x faces at its open bottom (boss underside z spring_boss[1]) as a
    front outline (x, z); for the export only (the cuts are not solids)."""
    sg, dx, li = P["spring_groove"], P.get("spring_groove_dx", 0.0), P["spring_lead_in"]
    out = []
    for nm, xl in levers.items():
        xc = xl + dx
        out.append(dict(lever=nm, x=(xc - sg[3] / 2, xc + sg[3] / 2), side=rect(sg[0], sg[0] + sg[4], sg[1], sg[2]),
                        chamfer_x=(xc - sg[3] / 2 - li, xc + sg[3] / 2 + li), chamfer_side=rect(sg[0], sg[0] + sg[4], sg[1], sg[1] + li),
                        front=[(xc - sg[3] / 2, sg[2]), (xc - sg[3] / 2, sg[1] + li), (xc - sg[3] / 2 - li, sg[1]), (xc + sg[3] / 2 + li, sg[1]),
                               (xc + sg[3] / 2, sg[1] + li), (xc + sg[3] / 2, sg[2])]))
    return out


def fixed_prisms(P, g, neighbours=False, play=False):
    """all fixed parts of one module (module frame).  g = solved design (build_geo)."""
    keys, lay = g["keys"], g["lay"]
    F = []
    W = P["module_w"]
    if P.get("board_hatch"):
        # r4.4 fix 2b: the floor is open under the control board (the board goes in from below)
        hx0, hx1, hy0, hy1 = P["board_hatch"]
        F.append(("floor", 0.0, hx0, rect(0.0, P["frame_depth"], P["z_floor"][0], P["z_floor"][1])))
        F.append(("floor (in front of the board hatch)", hx0, hx1, rect(0.0, hy0, P["z_floor"][0], P["z_floor"][1])))
        nx0, nx1, ny1 = P.get("board_hatch_notch", (hx0, hx0, hy1))
        for xa_, xb_, ya_ in ((hx0, nx0, hy1), (nx0, nx1, ny1), (nx1, hx1, hy1)):
            if xb_ - xa_ > 1e-9:
                F.append(("floor (behind the board hatch)", xa_, xb_, rect(ya_, P["frame_depth"], P["z_floor"][0], P["z_floor"][1])))
        F.append(("floor", hx1, W, rect(0.0, P["frame_depth"], P["z_floor"][0], P["z_floor"][1])))
    else:
        F.append(("floor", 0.0, W, rect(0.0, P["frame_depth"], P["z_floor"][0], P["z_floor"][1])))
    (y1, z1), (y2, z2) = g["w_felt_line"]
    F.append(("white front rail", 0.5, 164.0, [(1.5, 5.0), (27.0, 5.0), (27.0, z2 - 3.0), (y2, z2 - 3.0), (y1, z1 - 3.0)]))
    F.append(("white front felt 3T", 0.5, 164.0, [(y1, z1 - 3.0), (y2, z2 - 3.0), (y2, z2), (y1, z1)]))
    F += front_parts(P, g, keys, ORDER)
    xs = [0.5]
    for n_, x0 in BLACK:
        xs += [x0 + 5.5 - P["bar_low_half"], x0 + 5.5 + P["bar_low_half"]]
    xs.append(162.9)
    for i in range(0, len(xs) - 1):
        top = P["bar_top_b"] if i % 2 == 1 else P["bar_top_w"]
        F.append(("sensor bar", xs[i], xs[i + 1], rect(P["bar_y"][0], P["bar_y"][1], 8.6, top)))
    blocks = [block_x(P, keys[nm]) for nm in ORDER]
    F += rail_prisms(P, g, blocks, P["rail_x"], P["rod_k_x"], ribbon=True, pockets=rail_pockets(P, g, keys, ORDER))
    zpin = P["block_step_z"] + P["pin_engage"]
    for nm, kd in keys.items():
        bx0, bx1 = block_x(P, kd)
        xp = (bx0 + bx1) / 2
        F.append(("balance pin D2 " + nm, xp - P["pin_d"] / 2, xp + P["pin_d"] / 2,
                  rect(P["pin_y"] - P["pin_d"] / 2, P["pin_y"] + P["pin_d"] / 2, zpin - P["pin_len"], zpin)))
    F += board_prisms(P, lay["fins"])
    F += board_parts(P)                               # r4.3: BRD-01 (RP2040-Zero on headers, 4067, J301, J302)
    F += board_standoff_prisms(P, g)                  # r4.4: stand-offs, M3x6 heads, locating pins (circuit cross-check 3); fix 2b: hung bosses
    F += sb_support_prisms(P, P["sb_board"][:2], P["sb_rib_x"], P["sb_rib_gap"], " SB")     # r4.4: v3 P111-P113 (cross-check 5)
    F += sb_ledge_prisms(P)                           # r4.5 circuit 2nd (item 8): v3 P112 right ledge over the bar's right end
    F.append(("USB-C plug envelope (z%.1f-%.1f)" % tuple(P["usb_z"]), P["usb_x"][0], P["usb_x"][1], rect(P["usb_y"][0], P["usb_y"][1], P["usb_z"][0], P["usb_z"][1])))
    zs = g["z_shelf"]
    # r4.3: open slot over the USB plug (r4.2: 1.5 thin shelf x75.6-92.4, underside z18.55 -> 0.25 above the raised plug)
    s0, s1 = usb_slot(P)
    F.append(("rear shelf", 0.0, s0, rect(P["shelf_y"][0], P["shelf_y"][1], zs - 2.0, zs)))
    F.append(("rear shelf", s1, W, rect(P["shelf_y"][0], P["shelf_y"][1], zs - 2.0, zs)))
    for xr in g["ribs"]:
        F.append(("shelf rib", xr - P["rib_t"] / 2, xr + P["rib_t"] / 2, rect(P["rib_y0"], P["shelf_y"][1], 5.0, zs - 2.0)))
    # fins up to the top plate, each with a printed boss around the lever rod (= the lever-fin rings; r4: no brass)
    bl = fin_boss_len(lay, P)
    ins = P["fin_ext_inset"]
    for i, (f0, f1) in enumerate(lay["fins"]):
        over_board = f1 > P["board_x"][0] and f0 < P["board_x"][1]
        over_usb = f1 > P["usb_wall_open"][0] and f0 < P["usb_wall_open"][1]
        end = i == 0 or i == len(lay["fins"]) - 1
        main, ext = fin_poly(P, g, over_board, over_usb, end)
        F.append(("fin", f0, f1, main))
        F.append(("fin", f0 + ins, f1 - ins, ext))
        rl, rr_ = bl[i]
        F.append(("fin boss", f0 - rl, f1 + rr_, circle(P["L"], P["boss_R"], 16)))
        if over_board and P.get("fin_keel") and P.get("fin_slot_y"):
            # r4.4 fix 2b: the foot's keel = the fin plate continued forward inside the board slot to the balance rail's rear face
            ky, kz0, kz1 = P["fin_keel"]
            F.append(("fin keel (F|F# foot grounded to the balance rail, inside the board slot)", f0 + ins, f1 - ins, rect(ky, keel_front(P), kz0, kz1)))
    F += lever_rod_prisms(P, lay["fins"], bl, plug_side="left")
    F += top_parts(P, g, lay["fins"], lay["levers"], keys, (0.2, W - 0.2))
    F += curtain_parts(P, g, 0.2, W - 0.2, [x0 + 5.5 for _, x0 in BLACK])
    ux0, ux1, uz0, uz1 = P["usb_wall_open"]
    zt = g["z_top"]
    F.append(("rear wall", 0.0, ux0, rect(P["rear_wall"][0], P["rear_wall"][1], 5.0, zt)))
    F.append(("rear wall (over USB opening)", ux0, ux1, rect(P["rear_wall"][0], P["rear_wall"][1], uz1, zt)))
    F.append(("rear wall", ux1, W, rect(P["rear_wall"][0], P["rear_wall"][1], 5.0, zt)))
    F += spring_bosses(P, g, lay["levers"])
    F.append(("rear dovetail (female groove, neighbour male inside)", 0.0, 4.0, rect(198.0, 207.0, 3.0, 17.3)))
    F.append(("rear dovetail male root", W - 4.0, W, rect(198.0, 207.0, 3.0, 17.0)))
    F.append(("front dovetail (female)", 0.0, 4.0, rect(6.5, 15.5, 3.0, 8.8)))
    F.append(("front dovetail male root", W - 4.0, W, rect(6.5, 15.5, 3.0, 8.5)))
    return F
def lever_rod_prisms(P, fins, boss_len, plug_side="left"):
    """r4.4 (R44 issue 1, drafter): the lever rod (D4 SUS304, from 0.3 inside the plug-side end fin to 0.2 inside the
    blind end fin), the bore of every fin boss (printed D3.9, drilled D4.0: through, except the blind end fin whose outer
    wall rod_L_blind stays), and the printed rod-end plug (rod_L_plug long, pressed flush into the plug-side end fin's
    bore) as fixed prisms, so geometry.json and the sweeps carry them.  Module: plug left (x0.2-1.4), blind right
    (bore to x163.1, wall 1.2); rod 1.5-162.9 -> axial play 0.1 + 0.2 (rod 161.4 +- 0.2: 0.1-0.5)."""
    L = P["L"]
    rr_ = P["rod_L"] / 2
    fs = sorted(fins)
    x0 = fs[0][1] - 0.3
    x1 = fs[-1][0] + 0.2
    out = [("lever rod D4 SUS304 (x%.1f-%.1f)" % (x0, x1), x0, x1, circle(L, rr_, 16))]
    bore = circle(L, P.get("boss_bore", 4.0) / 2, 16)
    for i, (f0, f1) in enumerate(fs):
        a, b = f0 - boss_len[i][0], f1 + boss_len[i][1]
        if plug_side == "left" and i == len(fs) - 1:
            b = f1 - P["rod_L_blind"]
        if plug_side == "right" and i == 0:
            a = f0 + P["rod_L_blind"]
        out.append(("fin boss bore D4.0 (printed D3.9, drilled; lever rod inside)", a, b, bore))
    if plug_side == "left":
        out.append(("lever rod end plug (printed, pressed flush)", fs[0][0], fs[0][0] + P["rod_L_plug"], circle(L, rr_, 16)))
    else:
        out.append(("lever rod end plug (printed, pressed flush)", fs[-1][1] - P["rod_L_plug"], fs[-1][1], circle(L, rr_, 16)))
    return out


# ============================================================================ clearance sweep (3D prisms, all poses)
def prism_dist(xa, pa, xb, pb):
    xgap = max(xb[0] - xa[1], xa[0] - xb[1])
    d = poly_dist(pa, pb)
    if xgap < 0:
        return d, "yz"
    if d <= 0:
        return xgap, "x"
    return math.hypot(xgap, d), "xyz"


# designed contacts / designed sliding fits that are not clearances (reported separately)
EXCLUDE = [
    ("down-stop floor", "white front felt"), ("stop floor", "black front felt"), ("rest felt", "rear shelf"),
    ("balance block", "key rod"), ("crossbar", "keeper felt"),
    ("guide rib", "tab "), ("wall L low", "tab "), ("wall R low", "tab "),     # the tab (bushing cloth) is the only guide
    ("hub", "fin"), ("capstan head", "felt strip"),
    ("front wall", "white front felt"), ("front wall", "black front felt"), ("head wall", "white front felt"),
    ("wall L low", "black front felt"), ("wall R low", "black front felt"), ("crossbar", "white front felt"), ("guide rib", "white front felt"),
    ("hub", "fin boss"), ("web", "fin boss"), ("carrier side wall", "fin boss"),   # designed thrust face (boss end = the r3 ring)
    ("balance block", "balance pin"),           # designed fit: pin in the cloth-bushed slot of the block (y checked separately)
    ("carrier core", "fin boss"), ("bottom lip", "fin boss"),   # recessed 0.8 behind the thrust face
    ("crossbar", "tab "),                       # designed rear y-stop (0.8 gap), reported separately
    ("thin tail", "rear shelf"),                # spacing = rest felt + punchings (designed contact), reported separately
    ("carrier core", "up-stop pad"),            # r4 designed contact: the exposed steel top on its pad
    ("hub collar", "hub collar"), ("hub collar", "fin boss"),   # r4: designed thrust faces between hubs (axial play)
    ("hub collar", "hub"), ("hub collar", "web"),               # r4: a neighbour's hub / web sits behind its own collar
    # r4.4: the lever rod runs through every hub / collar / spring-pocket section (designed fit; bores 'fin boss bore'
    # are covered by the 'fin' / 'fin boss' pairs above)
    ("hub", "lever rod D4"), ("hub collar", "lever rod D4"), ("web", "lever rod D4"),
]


def excluded(a, b):
    for u, v in EXCLUDE:
        if (a.startswith(u) and b.startswith(v)) or (b.startswith(u) and a.startswith(v)):
            return True
    return False


def yaw_inflate(P, prisms, kind, black, float_lr=None):
    """attach the play-driven yaw to each prism as (k, y_ref, c): keys pivot (in plan) about the front guide tab with
    +-yaw_pin of play at the balance pin (c = tab play, both sides); levers yaw +-yaw_lever at the carrier front about the
    hub, and r4.4 fix 2: c = the lever's one-sided axial float (left, right) on the rod (lever_float).  The x-shift at world
    y is c + k*|y - y_ref|; the sweep applies it over the y-interval the two parts share."""
    if kind == "key":
        yg = sum(P["b_tab_y"] if black else P["w_tab_y"]) / 2
        yaw = (P["yaw_pin"] / (P["pin_y"] - yg), yg, P.get("tab_play", 0.0))      # r3: + lateral play at the tab
    else:
        yaw = (P["yaw_lever"] / (P["L"][0] - P["y_lever_front"]), P["L"][0], tuple(float_lr) if float_lr is not None else 0.0)
    return [(t, x0, x1, poly, yaw) for t, x0, x1, poly in prisms]


def yaw_shift(yaw, ya, yb):
    """(left, right) x inflation of a prism over the y-interval ya..yb."""
    if yaw is None:
        return (0.0, 0.0)
    k, ref, c = yaw
    s_ = k * max(abs(ya - ref), abs(yb - ref))
    if isinstance(c, tuple):
        return (c[0] + s_, c[1] + s_)
    return (c + s_, c + s_)


def with_bar_play(P, F):
    """r4.4 fix 2: the pad bar (and everything on it: pads, wedges, edge strips, leaves, grip) moves +-pad_bar_clear
    sideways between its rails; the rails / rail lips are frame."""
    c = P["pad_bar_clear"]
    out = []
    for f in F:
        nm = f[0]
        if nm.startswith(("up-stop pad", "pad wedge", "pad bar")) and not nm.startswith("pad bar rail"):
            out.append(tuple(f[:4]) + ((0.0, 0.0, (c, c)),))
        else:
            out.append(f)
    return out


def pair_dist(A, B):
    """prism distance with the yaw of both parts applied over their common y-interval."""
    ta, xa0, xa1, pa = A[:4]
    tb, xb0, xb1, pb = B[:4]
    ya = (min(p[0] for p in pa), max(p[0] for p in pa))
    yb = (min(p[0] for p in pb), max(p[0] for p in pb))
    y0, y1 = max(ya[0], yb[0]), min(ya[1], yb[1])
    if y0 > y1:                     # no common y: use the facing ends
        y0 = y1 = (ya[1] if ya[1] < yb[0] else ya[0]) if True else 0.0
        y0, y1 = min(ya[1], yb[1]), max(ya[0], yb[0])
    da = yaw_shift(A[4] if len(A) > 4 else None, y0, y1)
    db = yaw_shift(B[4] if len(B) > 4 else None, y0, y1)
    return prism_dist((xa0 - da[0], xa1 + da[1]), pa, (xb0 - db[0], xb1 + db[1]), pb)


def clearance_sweep(P, g, poses_key, poses_lever, neighbours=2, extra_moving=None):
    """min clearance for every (part, part) combination: key-key, key-lever, lever-lever, moving-fixed,
    with each moving body in each of its poses (neighbours independent, own key+lever coupled).
    poses_key: dict name -> {pose: a}; poses_lever: dict name -> {pose: b}; coupled own pairs use the
    same pose label.  Returns list of records sorted by clearance."""
    keys, lay, caps = g["keys"], g["lay"], g["caps"]
    fixed = fixed_prisms(P, g, play=True) if extra_moving is None else extra_moving["fixed"]
    fixed = with_bar_play(P, fixed)                  # r4.4 fix 2: pad-bar lateral play
    K, L = P["K"], P["L"]
    bodies = []      # (id, kind, name, dx, prisms)
    if extra_moving is None:
        flo, pgap = lever_float(lay, P, g["collars"])        # r4.4 fix 2: axial float of every lever
        for nm in ORDER:
            kd = keys[nm]
            yc = caps["black" if kd["black"] else "white"]
            bodies.append((("key", nm, 0), "key", nm, 0.0, yaw_inflate(P, key_prisms(P, kd, yc, lay["levers"][nm]), "key", kd["black"])))
            bodies.append((("lever", nm, 0), "lever", nm, 0.0, yaw_inflate(P, lever_prisms(P, lay["levers"][nm], g["collars"][nm]), "lever", kd["black"], flo[nm])))
        # neighbour modules across the seams (B, A# of the left module; C, C# of the right module)
        for nm, dx in (("B", -P["module_w"]), ("A#", -P["module_w"]), ("C", P["module_w"]), ("C#", P["module_w"])):
            kd = keys[nm]
            yc = caps["black" if kd["black"] else "white"]
            bodies.append((("key", nm, dx), "key", nm, dx, yaw_inflate(P, key_prisms(P, kd, yc, lay["levers"][nm]), "key", kd["black"])))
            bodies.append((("lever", nm, dx), "lever", nm, dx, yaw_inflate(P, lever_prisms(P, lay["levers"][nm], g["collars"][nm]), "lever", kd["black"], flo[nm])))
        xlev = dict(lay["levers"])
    else:
        bodies = extra_moving["bodies"]
        pgap = extra_moving.get("pair_gap", {})
        xlev = extra_moving.get("xlev", {})
    cache = {}

    def tp(body, pose):
        key = (body[0], pose)
        if key not in cache:
            bid, kind, nm, dx, prs = body
            if kind == "key":
                a = poses_key[nm][pose]
                sh = poses_key[nm].get("_shift", {}).get(pose, (0.0, 0.0))     # r4.4 fix 2: notch seated / sinking on the rod
                cache[key] = [(pr[0], pr[1] + dx, pr[2] + dx, [(q[0] + sh[0], q[1] + sh[1]) for q in (rot(p, K, a) for p in pr[3])]) + tuple(pr[4:]) for pr in prs]
            else:
                b = poses_lever[nm][pose]
                cache[key] = [(pr[0], pr[1] + dx, pr[2] + dx, [rot(p, L, -b) for p in pr[3]]) + tuple(pr[4:]) for pr in prs]
        return cache[key]

    def xr(prs):
        return min(p[1] for p in prs), max(p[2] for p in prs)
    recs = []

    def add(cls, n1, p1, t1, n2, p2, t2, d, mode):
        recs.append(dict(cls=cls, a=n1, pose_a=p1, part_a=t1, b=n2, pose_b=p2, part_b=t2, d=d, mode=mode))

    def compare(cls, A_, pa, B_, pb, na, nb, own=False):
        best = None
        for PA in A_:
            ta, xa0, xa1, pga = PA[:4]
            for PB in B_:
                tb, xb0, xb1, pgb = PB[:4]
                if xb0 - xa1 > 6 or xa0 - xb1 > 6:
                    continue
                if excluded(ta, tb) or (own and excluded(ta, tb)):
                    continue
                if own and ((ta == "capstan head" and tb == "felt strip") or (tb == "capstan head" and ta == "felt strip")):
                    continue
                if own:
                    # r4.4 fix 2: the own lever floats on the rod against its (guided) key
                    fa_ = PA[4][2] if len(PA) > 4 and isinstance(PA[4][2], tuple) else (0.0, 0.0)
                    fb_ = PB[4][2] if len(PB) > 4 and isinstance(PB[4][2], tuple) else (0.0, 0.0)
                    d, mode = prism_dist((xa0 - fa_[0], xa1 + fa_[1]), pga, (xb0 - fb_[0], xb1 + fb_[1]), pgb)
                else:
                    d, mode = pair_dist(PA, PB)
                if best is None or d < best[0]:
                    best = (d, mode, ta, tb)
        if best is not None:
            add(cls, na, pa, best[2], nb, pb, best[3], best[0], best[1])
    kposes = ["rest", "dip", "dip_rigid", "ff", "over"]      # r4.4: + the rigid kinematic bottom (dip = settled 1 N with the pad)
    lposes = ["rest", "dip", "dip_rigid", "ff", "over"]
    # moving vs moving
    for i, bA in enumerate(bodies):
        for bB in bodies[i + 1:]:
            if bA[0][2] != 0 and bB[0][2] != 0:
                continue
            xa = xr(bA[4]); xa = (xa[0] + bA[3], xa[1] + bA[3])
            xb = xr(bB[4]); xb = (xb[0] + bB[3], xb[1] + bB[3])
            if xb[0] - xa[1] > 6 or xa[0] - xb[1] > 6:
                continue
            own = bA[2] == bB[2] and bA[3] == bB[3]
            cls = "-".join(sorted([bA[1], bB[1]]))
            # r4.4 fix 2: two neighbouring levers of one bay can close only their own free gap (not both floats)
            adj_ = None
            if bA[1] == "lever" and bB[1] == "lever" and bA[3] == bB[3] and bA[2] != bB[2]:
                lft, rgt = (bA, bB) if xlev.get(bA[2], 0.0) < xlev.get(bB[2], 0.0) else (bB, bA)
                if (lft[2], rgt[2]) in pgap:
                    adj_ = (lft[0], rgt[0], pgap[(lft[2], rgt[2])])
            na = "%s %s%s" % (bA[1], bA[2], "" if bA[3] == 0 else ("(left module)" if bA[3] < 0 else "(right module)"))
            nb = "%s %s%s" % (bB[1], bB[2], "" if bB[3] == 0 else ("(left module)" if bB[3] < 0 else "(right module)"))
            if own:
                for pz in ("rest", "q1", "q2", "q3", "dip", "dip_rigid", "ff", "over"):
                    compare("own key-lever", tp(bA, pz), pz, tp(bB, pz), pz, na, nb, own=True)
            else:
                for pa in (kposes if bA[1] == "key" else lposes):
                    for pb in (kposes if bB[1] == "key" else lposes):
                        PA_, PB_ = tp(bA, pa), tp(bB, pb)
                        if adj_ is not None:
                            def _fl(prs, lr):
                                return [pr[:4] + ((pr[4][0], pr[4][1], lr),) for pr in prs]
                            PA_ = _fl(PA_, (0.0, adj_[2]) if bA[0] == adj_[0] else (0.0, 0.0))
                            PB_ = _fl(PB_, (0.0, adj_[2]) if bB[0] == adj_[0] else (0.0, 0.0))
                        compare(cls, PA_, pa, PB_, pb, na, nb)
    # moving vs fixed (own module only; neighbour-module moving parts vs own fixed parts too)
    for bA in bodies:
        for pa in (kposes if bA[1] == "key" else lposes):
            prs = tp(bA, pa)
            na = "%s %s%s" % (bA[1], bA[2], "" if bA[3] == 0 else ("(left module)" if bA[3] < 0 else "(right module)"))
            for f in fixed:
                best = None
                for PA in prs:
                    ta, xa0, xa1, pga = PA[:4]
                    if f[1] - xa1 > 6 or xa0 - f[2] > 6:
                        continue
                    if excluded(ta, f[0]):
                        continue
                    d, mode = pair_dist(PA, f)
                    if best is None or d < best[0]:
                        best = (d, mode, ta)
                if best is not None:
                    add(bA[1] + "-fixed", na, pa, best[2], f[0], "-", "", best[0], best[1])
    recs.sort(key=lambda r: r["d"])
    return recs


def summarize_clearances(recs):
    """worst record per (a, b) pair class and flags."""
    seen = {}
    for r in recs:
        k = (r["cls"], r["a"], r["b"])
        if k not in seen:
            seen[k] = r
    out = sorted(seen.values(), key=lambda r: r["d"])
    for r in out:
        r["after_tol"] = r["d"] - TOL
        r["ok"] = r["after_tol"] >= CLEAR_MIN - 1e-9
    return out



def rail_keel_root(P, fins, x_keel, rail_top, supports=None, dx=0.5):
    """r4.5 fix 2 (verifier fixes minor): stiffness of the balance rail's rear face at x_keel, where the F|F# fin keel is
    joined to it, as the 2x2 matrix on (w, dw/dy) of the keel root.  The rail + the floor strip under it (y rail_front_y ..
    rail_y[1], z floor bottom .. rail_top; over the ribbon lane the rail runs from the lane top and the 2 mm floor strip under
    the lane is a separate plate - not composite) is a beam along x: bending EI(x), St-Venant torsion GJ(x); supports
    'fins' = the fin lines left / right of the keel (simply supported, twist held), 'hatch' = clamped at the board-hatch
    edges.  The rear face is e = half the rail depth behind the twist axis: w_face = w_c + e theta, slope = theta.
    Returns (K, info)."""
    supports = P.get("keel_rail", "fins") if supports is None else supports
    E, NU = E_PETG, 0.38
    G_ = E / (2 * (1 + NU))
    y0, y1 = P["rail_front_y"], P["rail_y"][1]
    b = y1 - y0
    zf0, zf1 = P["z_floor"]
    lane = tuple(P.get("ribbon_x", (0.0, 0.0)))
    zl = P["lead_lane_z"][1]

    def J(a, t):
        a, t = max(a, t), min(a, t)
        return (1.0 / 3.0 - 0.21 * (t / a) * (1 - t ** 4 / (12 * a ** 4))) * a * t ** 3

    sk = P.get("rail_skirt")                 # r4.5 fix 2: (y front, z top, x0, x1) solid skirt in front of the rail

    def comp(rs):
        A_ = sum((y1_ - y0_) * (z1_ - z0_) for y0_, y1_, z0_, z1_ in rs)
        zc_ = sum((y1_ - y0_) * (z1_ - z0_) * 0.5 * (z0_ + z1_) for y0_, y1_, z0_, z1_ in rs) / A_
        yc_ = sum((y1_ - y0_) * (z1_ - z0_) * 0.5 * (y0_ + y1_) for y0_, y1_, z0_, z1_ in rs) / A_
        I_ = sum((y1_ - y0_) * (z1_ - z0_) ** 3 / 12 + (y1_ - y0_) * (z1_ - z0_) * (0.5 * (z0_ + z1_) - zc_) ** 2 for y0_, y1_, z0_, z1_ in rs)
        return I_, yc_

    def sec(x):
        on_sk = sk is not None and sk[2] <= x <= sk[3]
        if lane[0] < x < lane[1]:
            up = [(y0, y1, zl, rail_top)] + ([(sk[0], y0, zl, sk[1])] if on_sk else [])
            fl = [((sk[0] if on_sk else y0), y1, zf0, zf1)]
            Iu, yc_ = comp(up)
            If, _ = comp(fl)
            Ju = J(b, rail_top - zl) + (J(y0 - sk[0], sk[1] - zl) if on_sk else 0.0)
            return E * (Iu + If), G_ * (Ju + J(fl[0][1] - fl[0][0], zf1 - zf0)), yc_
        rs = [(y0, y1, zf0, rail_top)] + ([(sk[0], y0, zf0, sk[1])] if on_sk else [])
        I_, yc_ = comp(rs)
        return E * I_, G_ * (J(b, rail_top - zf0) + (J(y0 - sk[0], sk[1] - zf0) if on_sk else 0.0)), yc_
    fc = sorted(0.5 * (f0 + f1) for f0, f1 in fins)
    inner = []
    if supports == "hatch":
        xa, xb = P["board_hatch"][0], P["board_hatch"][1]
    elif supports == "fins_span":
        xa = max(x for x in fc if x < x_keel - 1.0)
        xb = min(x for x in fc if x > x_keel + 1.0)
    else:
        # 'fins': the rail is continuous over every fin line of the part (end fins included), simply supported at each
        # (the fins stand on the floor strip that carries the rail) except the keel's own fin
        xa, xb = fc[0], fc[-1]
        inner = [x for x in fc[1:-1] if abs(x - x_keel) > 1.0]
    n = int(round((xb - xa) / dx))
    xs = np.linspace(xa, xb, n + 1)
    Kb = np.zeros((2 * (n + 1), 2 * (n + 1)))
    Kt = np.zeros((n + 1, n + 1))
    EIs, GJs = [], []
    for i in range(n):
        L_ = xs[i + 1] - xs[i]
        EI, GJ, _ = sec(0.5 * (xs[i] + xs[i + 1]))
        EIs.append(EI)
        GJs.append(GJ)
        kb = EI / L_ ** 3 * np.array([[12, 6 * L_, -12, 6 * L_], [6 * L_, 4 * L_ * L_, -6 * L_, 2 * L_ * L_],
                                       [-12, -6 * L_, 12, -6 * L_], [6 * L_, 2 * L_ * L_, -6 * L_, 4 * L_ * L_]])
        idx = [2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3]
        Kb[np.ix_(idx, idx)] += kb
        Kt[np.ix_([i, i + 1], [i, i + 1])] += GJ / L_ * np.array([[1, -1], [-1, 1]])
    k_ = int(np.argmin(abs(xs - x_keel)))
    fixed_b = [0, 2 * n] + ([1, 2 * n + 1] if supports == "hatch" else []) + [2 * int(np.argmin(abs(xs - x))) for x in inner]
    free_b = [i for i in range(2 * (n + 1)) if i not in fixed_b]
    fb = np.zeros(2 * (n + 1))
    fb[2 * k_] = 1.0
    ub = np.zeros(2 * (n + 1))
    ub[free_b] = np.linalg.solve(Kb[np.ix_(free_b, free_b)], fb[free_b])
    fixed_t = [0, n] + [int(np.argmin(abs(xs - x))) for x in inner]
    free_t = [i for i in range(n + 1) if i not in fixed_t]
    ft = np.zeros(n + 1)
    ft[k_] = 1.0
    ut = np.zeros(n + 1)
    ut[free_t] = np.linalg.solve(Kt[np.ix_(free_t, free_t)], ft[free_t])
    cw, cp = ub[2 * k_], ut[k_]
    e = y1 - sec(x_keel + 2.0)[2]              # rear face behind the section's centroid (twist axis)
    C = np.array([[cw + e * e * cp, e * cp], [e * cp, cp]])
    return np.linalg.inv(C), dict(kv=1.0 / cw, kr=1.0 / cp, e=e, span=(xa, xb), inner=inner, supports=supports, EI=(min(EIs), max(EIs)), GJ=(min(GJs), max(GJs)),
                                  k_face=1.0 / C[0, 0], rail_top=rail_top)


# ============================================================================ r4 top plate (ledge + bridge) grillage FE
def plate_fe(P, fins, loads, t_of_y, z_under_of_y, board_x=None, y0=None, y1=None, s=1.0, x0=0.2, x1=164.3,
             hung_bottom=None, fin_front=None, rail_top=None):
    """printed top plate of the frame (r4: the r3 bridge extended forward to y146.5 = 'ledge'; the pad bars bear on
    its underside).  Grillage of beam members on a 1 mm grid (plate bending D = E t^3 / 12(1-nu^2), torsion with
    (1-nu)); supports:
      - every fin that reaches the floor: vertical line springs E t s / H (fin stretch over its height H);
      - fins over the control board (they hang above the parts, z >= comp_zmax + 1.5): a Timoshenko DEEP BEAM along y
        (depth H = underside - hung_bottom, thickness t) that shares w and the slope with the plate nodes and is
        grounded where it reaches the floor behind the board (line springs as above);
      - the rear wall (3 thick) along the rear edge.
    The plate prints flat (layers horizontal): plate bending is IN the layer plane; fin and wall tension is ACROSS
    layers.  loads: list of cases, each [(x, y, F up, wy, wx)].  Returns per case: max plate stress, deflection field,
    per-fin line loads (N/mm) and top-junction tension (MPa), wall line load, and the grid."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    E, NU = E_PETG, 0.38
    Gm = E / (2 * (1 + NU))
    board_x = P["board_x"] if board_x is None else board_x
    y0 = P["ledge_y0"] if y0 is None else y0
    y1 = P["rear_wall"][0] if y1 is None else y1
    hung_bottom = P["comp_zmax"] + 1.5 if hung_bottom is None else hung_bottom
    fin_front = P["fin_y"][0] if fin_front is None else fin_front
    xs = np.arange(x0, x1 + 1e-9, s)
    ys = np.arange(y0, y1 + 1e-9, s)
    nx, ny = len(xs), len(ys)
    nid = lambda i, j: i * ny + j
    ndof = 3 * nx * ny
    rows, cols, vals = [], [], []

    def add(idx, k):
        for a in range(len(idx)):
            for b in range(len(idx)):
                if k[a, b] != 0.0:
                    rows.append(idx[a]); cols.append(idx[b]); vals.append(k[a, b])

    def beam(L, EI, GJ, GA=None):
        k = np.zeros((6, 6))
        phi = 0.0 if GA is None else 12 * EI / (GA * L * L)
        c = EI / (L ** 3 * (1 + phi))
        kb = c * np.array([[12, 6 * L, -12, 6 * L], [6 * L, (4 + phi) * L * L, -6 * L, (2 - phi) * L * L],
                           [-12, -6 * L, 12, -6 * L], [6 * L, (2 - phi) * L * L, -6 * L, (4 + phi) * L * L]])
        ib = [0, 1, 3, 4]
        for a in range(4):
            for b in range(4):
                k[ib[a], ib[b]] += kb[a, b]
        kt = GJ / L
        k[2, 2] += kt; k[5, 5] += kt; k[2, 5] -= kt; k[5, 2] -= kt
        return k
    Dm = lambda t: E * t ** 3 / (12 * (1 - NU ** 2))
    T = np.array([t_of_y(y) for y in ys])
    for i in range(nx):
        for j in range(ny):
            t = T[j]
            if i < nx - 1:
                k = beam(s, Dm(t) * s, Dm(t) * (1 - NU) * s)
                n1, n2 = nid(i, j), nid(i + 1, j)
                add([3 * n1, 3 * n1 + 2, 3 * n1 + 1, 3 * n2, 3 * n2 + 2, 3 * n2 + 1], k)
            if j < ny - 1:
                tm = 0.5 * (t + T[j + 1])
                k = beam(s, Dm(tm) * s, Dm(tm) * (1 - NU) * s)
                n1, n2 = nid(i, j), nid(i, j + 1)
                add([3 * n1, 3 * n1 + 1, 3 * n1 + 2, 3 * n2, 3 * n2 + 1, 3 * n2 + 2], k)
    spring = np.zeros(nx * ny)
    keels = []                               # r4.4 fix 2b: (fin index, keel element, fin node, t, depth, length, root dof)
    n_extra = [0]                            # r4.5 fix 2: extra dofs (keel root w, slope) on the rail spring
    keel_info = {}
    fin_springs = []                         # (fin index, j, node, k)
    fin_beams = []                           # (fin index, j, j+1, element stiffness 6x6 in the plate dofs)
    for fi, (fa, fb) in enumerate(fins):
        t_f = fb - fa
        xc = 0.5 * (fa + fb)
        i = int(np.argmin(abs(xs - xc)))
        over_board = board_x[0] < xc < board_x[1]
        # r4.3: a board fin over the USB tunnel is hung above the plug behind the board too (the shelf under it is cut);
        # r4.2 grounded it behind y196.8 (it stood on the 1.5 thin shelf over the tunnel, modelled as the floor)
        over_usb = over_board and P["usb_wall_open"][0] < xc < P["usb_wall_open"][1] and "usb_clear" in P
        # r4.1 (physics major 2): the fin over the board reaches the floor through a slot in the stripboard over
        # fin_slot_y (front part of the board, in front of the RP2040-Zero); hung (deep beam) only behind it
        gy = P.get("fin_slot_y")
        # r4.5 fix 2 (resume): the keel fin runs down to z3 from its own front edge (fin_keel_front) through the board slot
        if over_board and gy is not None and P.get("fin_keel") is not None and P.get("board_hatch") is not None and P.get("fin_keel_front"):
            gy = (min(gy[0], P["fin_keel_front"]), gy[1])
        slot_ = lambda y: gy is not None and gy[0] - 1e-9 <= y <= gy[1] + 1e-9
        hung_ = lambda y: (y < P["rib_y0"] or over_usb) and not slot_(y)
        # r4.4 fix 2b: with the floor open under the board the foot is not grounded under itself; it is a deep beam down to z3 and
        # the keel (fin plate z3-18 continued forward to the balance rail's rear face, clamped there) holds its front end
        keel_ = over_board and gy is not None and P.get("fin_keel") is not None and P.get("board_hatch") is not None
        keel_done = False
        ff_ = min(fin_front, keel_front(P)) if keel_ else fin_front
        for j, y in enumerate(ys):
            if y < ff_ - 1e-9:
                continue
            tt = t_f if y >= P["fin_main_y0"] else t_f - 2 * P["fin_ext_inset"]
            if keel_ and not keel_done:
                ky_, kz0_, kz1_ = P["fin_keel"]
                Lk_, hk_ = y - ky_, kz1_ - kz0_
                kk_ = beam(Lk_, E * tt * hk_ ** 3 / 12.0, 0.0, Gm * tt * hk_ * 5.0 / 6.0)
                nk_ = nid(i, j)
                if rail_top is not None and P.get("keel_rail"):
                    # r4.5 fix 2: root on the rail spring (w, slope dofs of its own)
                    Kr_, info_ = rail_keel_root(P, fins, xc, rail_top)
                    r0_ = 3 * nx * ny + 2 * n_extra[0]
                    n_extra[0] += 1
                    ix4 = [0, 1, 3, 4]
                    add([r0_, r0_ + 1, 3 * nk_, 3 * nk_ + 1], kk_[np.ix_(ix4, ix4)])
                    add([r0_, r0_ + 1], Kr_)
                    keel_info[fi] = info_
                else:
                    r0_ = None
                    add([3 * nk_, 3 * nk_ + 1], kk_[3:5, 3:5])
                keel_done = True
                keels.append((fi, kk_, nk_, tt, hk_, Lk_, r0_))
            if over_board and j < ny - 1:
                # hung fin: deep beam along its whole length (clamped by its grounded part behind the board)
                H = max(4.0, z_under_of_y(y) - (hung_bottom if hung_(y) else (P["z_floor"][0] if keel_ else P["z_floor"][1])))
                EIf = E * tt * H ** 3 / 12.0
                fw_, ft_ = P.get("hung_fin_flange", (0.0, 0.0))
                if fw_ > tt and ft_ > 0 and y < P["rib_y0"]:
                    # r4: bottom flange of the fin over the board (between the two keys' beams): T section
                    Aw_, Af_ = tt * H, (fw_ - tt) * ft_
                    zc_ = (Aw_ * H / 2 + Af_ * ft_ / 2) / (Aw_ + Af_)
                    EIf = E * (tt * H ** 3 / 12 + Aw_ * (H / 2 - zc_) ** 2 + (fw_ - tt) * ft_ ** 3 / 12 + Af_ * (ft_ / 2 - zc_) ** 2)
                GAf = Gm * tt * H * 5.0 / 6.0
                k = beam(s, EIf, 0.0, GAf)
                n1, n2 = nid(i, j), nid(i, j + 1)
                add([3 * n1, 3 * n1 + 1, 3 * n1 + 2, 3 * n2, 3 * n2 + 1, 3 * n2 + 2], k)
                fin_beams.append((fi, j, k, n1, n2))
            if over_board and (hung_(y) or (keel_ and slot_(y))):
                continue
            H = z_under_of_y(y) - P["z_floor"][1]
            k = E * tt * s / H
            spring[nid(i, j)] += k
            fin_springs.append((fi, j, nid(i, j), k, tt))
    jr = ny - 1
    kw_ = E * (P["rear_wall"][1] - P["rear_wall"][0]) * s / (z_under_of_y(ys[jr]) - P["z_floor"][1])
    for i in range(nx):
        spring[nid(i, jr)] += kw_
    for n in range(nx * ny):
        if spring[n] > 0:
            rows.append(3 * n); cols.append(3 * n); vals.append(spring[n])
    ndof_t = ndof + 2 * n_extra[0]
    K = sp.csc_matrix((vals, (rows, cols)), shape=(ndof_t, ndof_t))
    lu = spla.splu(K)
    out = []
    for case in loads:
        f = np.zeros(ndof_t)
        for (x, y, F, wy, wx) in case:
            sel = [(i, j) for i in range(nx) for j in range(ny) if abs(xs[i] - x) <= wx / 2 + 1e-9 and abs(ys[j] - y) <= wy / 2 + 1e-9]
            for (i, j) in sel:
                f[3 * nid(i, j)] += F / len(sel)
        u = lu.solve(f)
        w = u[:ndof][0::3]
        W = w.reshape(nx, ny)
        kxx = np.zeros_like(W); kyy = np.zeros_like(W); kxy = np.zeros_like(W)
        kxx[1:-1, :] = (W[2:, :] - 2 * W[1:-1, :] + W[:-2, :]) / s ** 2
        kyy[:, 1:-1] = (W[:, 2:] - 2 * W[:, 1:-1] + W[:, :-2]) / s ** 2
        kxy[1:-1, 1:-1] = (W[2:, 2:] - W[2:, :-2] - W[:-2, 2:] + W[:-2, :-2]) / (4 * s * s)
        TT = np.tile(T, (nx, 1))
        Dd = E * TT ** 3 / (12 * (1 - NU ** 2))
        mx = -Dd * (kxx + NU * kyy)
        my = -Dd * (kyy + NU * kxx)
        mxy = -Dd * (1 - NU) * kxy
        r_ = np.sqrt((0.5 * (mx - my)) ** 2 + mxy ** 2)
        sig = 6 * np.maximum(abs(0.5 * (mx + my) + r_), abs(0.5 * (mx + my) - r_)) / TT ** 2
        # load footprint halo excluded (point-load singularity of the grillage): report outside +-2 mm of the pads
        mask = np.ones_like(sig, dtype=bool)
        for (x, y, F, wy, wx) in case:
            mask &= ~((abs(xs[:, None] - x) <= wx / 2 + 2) & (abs(ys[None, :] - y) <= wy / 2 + 2))
        sig_out = float(sig[mask].max()) if mask.any() else float(sig.max())
        fin_q = {}
        for (fi, j, n, k, tt) in fin_springs:
            fin_q.setdefault(fi, []).append((ys[j], k * w[n] / s, tt))
        for (fi, j, k, n1, n2) in fin_beams:
            ue = np.array([u[3 * n1], u[3 * n1 + 1], u[3 * n1 + 2], u[3 * n2], u[3 * n2 + 1], u[3 * n2 + 2]])
            fe = k @ ue
            t_f = fins[fi][1] - fins[fi][0]
            fin_q.setdefault(fi, []).append((ys[j], fe[0] / s, t_f))
            fin_q[fi].append((ys[j] + s, fe[3] / s, t_f))
        fins_out = {}
        for fi, lst in fin_q.items():
            acc = {}
            for y, q, tt in lst:
                acc.setdefault(round(y, 3), [0.0, tt])
                acc[round(y, 3)][0] += q
            qmax = max(v[0] for v in acc.values())
            top = max(v[0] / v[1] for v in acc.values())
            fins_out[fi] = dict(q_max=qmax, top=top, N=sum(v[0] * s for v in acc.values() if v[0] > 0))
        kq_ = {}
        for (fi, kk_, nk_, tk_, hk_, Lk_, r0_) in keels:
            ur_ = (u[r0_], u[r0_ + 1]) if r0_ is not None else (0.0, 0.0)
            fe_ = kk_ @ np.array([ur_[0], ur_[1], 0.0, u[3 * nk_], u[3 * nk_ + 1], 0.0])
            Zk_ = tk_ * hk_ ** 2 / 6.0
            kq_[fi] = dict(V=float(fe_[0]), M_root=float(fe_[1]), M_fin=float(fe_[4]), sigma=float(max(abs(fe_[1]), abs(fe_[4])) / Zk_),
                           tau=float(1.5 * abs(fe_[0]) / (tk_ * hk_)), t=tk_, h=hk_, L=Lk_, w_root=float(ur_[0]), slope_root=float(ur_[1]),
                           rail=keel_info.get(fi))
        out.append(dict(w=W, sigma=float(sig.max()), sigma_out=sig_out, fins=fins_out,
                        fin_top=max(v["top"] for v in fins_out.values()), wall_q=float(kw_ * W[:, jr].max() / s), keel=kq_))
    return xs, ys, out


def seat_at(xs, ys, W, x, y, wx, wy):
    """mean plate deflection over a pad footprint."""
    sel = W[(abs(xs - x) <= wx / 2 + 1e-9)][:, (abs(ys - y) <= wy / 2 + 1e-9)]
    return float(sel.mean())


# ============================================================================ assemble the solved design
def lever_top_profile(P, bs, y0, y1, n=69, skip=()):
    """max z of the lever outline over world y-bins, for all angles bs."""
    ys = [y0 + (y1 - y0) * i / (n - 1) for i in range(n)]
    zmax = [-1e9] * n
    for b in bs:
        for t, x0, x1, poly in lever_prisms(P, 0.0):
            if skip and t.startswith(skip):
                continue
            pts = [rot(p, P["L"], -b) for p in poly]
            m_ = len(pts)
            for i in range(m_):
                p, q = pts[i], pts[(i + 1) % m_]
                nk = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / 0.05))
                for k in range(nk + 1):
                    s_ = k / nk
                    yy, zz = p[0] + (q[0] - p[0]) * s_, p[1] + (q[1] - p[1]) * s_
                    j = int(round((yy - y0) / (y1 - y0) * (n - 1)))
                    if 0 <= j < n:
                        zmax[j] = max(zmax[j], zz)
    for j in range(1, n):
        if zmax[j] < -1e8:
            zmax[j] = zmax[j - 1]
    for j in range(n - 2, -1, -1):
        if zmax[j] < -1e8:
            zmax[j] = zmax[j + 1]
    zs_ = [max(zmax[max(0, j - 1):j + 2]) for j in range(n)]
    return ys, zs_


def b_at_cap(A, z):
    lo, hi = 0.0, 0.6
    for _ in range(60):
        m = (lo + hi) / 2
        if A.cap_top(m) < z:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def plate_profile(P, g):
    """top-plate underside (y, z): front channel (pad-bar front part) at z_seat + bar_t, pad zone at z_seat (= bar top),
    behind the pad bar the lever envelope at the service angle + 1.35 (never thinner than... never deeper than
    plate_rear_max below the top), and >= 1.3 over the torsion-spring leg tips."""
    zs_, zt = g["z_seat"], g["z_top"]
    ps_ = P.get("plate_step_y", P["pad_bar_y"][1] + 0.5)
    ys, env = lever_top_profile(P, [g["b_service_design"], g["held_b_w"] + math.radians(3.0)], ps_ - 0.5, P["rear_wall"][0], n=53)
    envf = lambda y: float(np.interp(y, ys, env))
    sg = P["spring_groove"]
    out = []
    y = P["ledge_y0"]
    while y <= P["rear_wall"][0] + 1e-9:
        if y < g["y_bar_step"]:
            z = zs_ + P["pad_bar_t"]
        elif y <= ps_ + 1e-9:
            z = zs_
        else:
            z = max(envf(y) + TOL + CLEAR_MIN + 0.05, zt - P["plate_rear_max"])
            if y >= P["L"][0] - 1.0:
                z = max(z, sg[2] + TOL + CLEAR_MIN)
            z = min(zs_, z)
        out.append((round(y, 2), round(z, 3)))
        y += 0.5
    return out


def plate_seat_k(P, g, fins, levers, y_load, keys_black, x_range=(0.2, 164.3), extra_fins=()):
    """per-key pad-seat stiffness (N/mm) from the plate FE: 100 N on each pad footprint in turn."""
    prof = g["plate_under"]
    yy = [p[0] for p in prof]
    zz = [p[1] for p in prof]
    zu = lambda y: float(np.interp(y, yy, zz))
    tof = lambda y: g["z_top"] - zu(y)
    cases = [[(x, y_load[keys_black[n]], 100.0, P["pad_y"][1] - P["pad_y"][0], P["pad_w"])] for n, x in levers.items()]
    xs, ys, out = plate_fe(P, list(fins) + list(extra_fins), cases, tof, zu, x0=x_range[0], x1=x_range[1], rail_top=min(g.get("z_rail_low", 99.0), P["rail_top_est"]))
    ks = {}
    for (n, x), o in zip(levers.items(), out):
        ks[n] = 100.0 / seat_at(xs, ys, o["w"], x, y_load[keys_black[n]], P["pad_w"], P["pad_y"][1] - P["pad_y"][0])
    return ks, (xs, ys, out, tof, zu)


def build_geo(P, z_shelf=None, seat_fe=True):
    """static part of the solved design: layout, capstans, shelf, the TRULY settled 1 N held bottom, pad tables and pad
    faces, pad-bar seat and top plate, per-key seat stiffness (plate FE), front felt lines, keeper, removal geometry."""
    keys, lay, caps_all, acts, tops = solve_design(P)
    caps = dict(white=round(sum(caps_all[n] for n in ORDER if not keys[n]["black"]) / 7, 2),
                black=round(sum(caps_all[n] for n in ORDER if keys[n]["black"]) / 5, 2))
    Aw = Action(P, keys["D"], caps["white"], lay["levers"]["D"])
    Ab = Action(P, keys["C#"], caps["black"], lay["levers"]["C#"])
    top_w_set, rig_w, set_w = slow_dip_cap_top(Aw)
    top_b_set, rig_b, set_b = slow_dip_cap_top(Ab)
    g = dict(keys=keys, lay=lay, caps=caps, caps_all=caps_all, Aw=Aw, Ab=Ab, acts=acts,
             rigid_top_w=rig_w, rigid_top_b=rig_b, set_w=set_w, set_b=set_b, top_w_set=top_w_set, top_b_set=top_b_set,
             z_keep=P["key_bot"] + P["crossbar_t"] + P["keeper_gap"], collars=hub_collars(lay, P))
    fw = [Aw.kp(p, Aw.a_dip) for p in Aw.stop_pts]
    sl = (fw[1][1] - fw[0][1]) / (fw[1][0] - fw[0][0])
    g["w_felt_line"] = ((P["w_felt_y"][0], fw[0][1] + sl * (P["w_felt_y"][0] - fw[0][0])),
                        (P["w_felt_y"][1], fw[0][1] + sl * (P["w_felt_y"][1] - fw[0][0])))
    fb = [Ab.kp(p, Ab.a_dip) for p in Ab.stop_pts]
    sl = (fb[1][1] - fb[0][1]) / (fb[1][0] - fb[0][0])
    g["b_felt_line"] = ((P["b_felt_y"][0], fb[0][1] + sl * (P["b_felt_y"][0] - fb[0][0])),
                        (P["b_felt_y"][1], fb[0][1] + sl * (P["b_felt_y"][1] - fb[0][0])))
    if z_shelf is None:
        z_shelf, _ = calibrate_shelf(Aw)
    g["z_shelf"] = round(z_shelf, 3)
    # r4 (U1): pad faces from the TRULY settled state held at 1 N at the bottom (no pad present)
    stw, top_w, frw, ww = held_bottom(Aw, g["z_shelf"], 1.0)
    stb, top_b, frb, wb_ = held_bottom(Ab, g["z_shelf"], 1.0)
    g.update(held_state_w=stw, held_state_b=stb, top_w=top_w, top_b=top_b, held_front_w=frw, held_front_b=frb,
             held_b_w=stw[1], held_b_b=stb[1], held_w_end=max(ww, wb_))
    g["pad_w"] = PadTable(Aw, stw[1], P["gap_us_w"])
    g["pad_b"] = PadTable(Ab, stb[1], P["gap_us_b"])
    for c, pt in (("w", g["pad_w"]), ("b", g["pad_b"])):
        g["pad_ref_" + c] = pt.ref
        g["pad_tilt_" + c] = stw[1] if c == "w" else stb[1]
        g["pad_b0_" + c] = pt.b0
        g["pad_c_" + c] = pt.c
        g["pad_e_check_" + c] = pt.e_check
    # pad bar seat (bar top in the pad zone): wedge >= pad_wedge_min over the thickest-backed pad
    backs = []
    for pt in (g["pad_w"], g["pad_b"]):
        for y in P["pad_y"]:
            backs.append(pad_face_z(pt, y) + P["pad_h"] * pt.n[1])
    g["z_seat"] = math.ceil((max(backs) + P["pad_wedge_min"] + P["pad_bar_t"]) * 20) / 20
    g["z_top"] = round(g["z_seat"] + P["plate_t"], 2)
    g["y_bar_step"] = P["pad_y"][0] - 2.0
    g["y_bar_joggle"] = g["y_bar_step"] - P.get("bar_joggle_clear", 0.0)      # r4.2: bar top step (bottom step 1.5 further forward)
    g["wedge_range"] = dict(w=(g["z_seat"] - P["pad_bar_t"] - max(pad_face_z(g["pad_w"], y) + P["pad_h"] * g["pad_w"].n[1] for y in P["pad_y"]),
                               g["z_seat"] - P["pad_bar_t"] - min(pad_face_z(g["pad_w"], y) + P["pad_h"] * g["pad_w"].n[1] for y in P["pad_y"])),
                            b=(g["z_seat"] - P["pad_bar_t"] - max(pad_face_z(g["pad_b"], y) + P["pad_h"] * g["pad_b"].n[1] for y in P["pad_y"]),
                               g["z_seat"] - P["pad_bar_t"] - min(pad_face_z(g["pad_b"], y) + P["pad_h"] * g["pad_b"].n[1] for y in P["pad_y"])))
    g["b_service_design"] = math.radians(16.0)
    g["plate_under"] = plate_profile(P, g)
    g["z_curtain_w"] = P["key_top"] + P["curtain_gap_w"]
    g["z_curtain_b"] = P["black_top"] + P["curtain_gap_b"]
    g["ribs"] = list(P["ribs"])
    # pad force centroid (y) at a typical compression, per colour
    g["y_load_w"] = g["pad_w"].ref[0] + g["pad_w"].u_c(1.0) * g["pad_w"].t[0]
    g["y_load_b"] = g["pad_b"].ref[0] + g["pad_b"].u_c(1.0) * g["pad_b"].t[0]
    if seat_fe:
        yl = {False: g["y_load_w"], True: g["y_load_b"]}
        ks, fe = plate_seat_k(P, g, lay["fins"], lay["levers"], yl, {n: keys[n]["black"] for n in ORDER})
        g["seat_k_keys"] = ks
        g["seat_k"] = math.floor(min(ks.values()) / 10) * 10
    else:
        g["seat_k_keys"] = {}
        g["seat_k"] = P["seat_k"]
    g["removal_w"], g["removal_b"] = removal_geometry(Aw, P), removal_geometry(Ab, P)
    return g


def dyn_for(g, A, seat_k=None, pad=None, **kw):
    """Dyn of the solved design for key action A (its colour's pad table, the weakest seat unless given)."""
    pt = pad if pad is not None else (g["pad_b"] if A.black else g["pad_w"])
    return Dyn(A, g["z_shelf"], pad=pt, seat_k=g["seat_k"] if seat_k is None else seat_k, **kw)


def ev_summary(ev):
    keys_ = ("v_bottom", "v_front_bottom", "lift_max", "sep_max", "land_v", "up_peak", "up_hits", "pen_up_max", "seat_max", "front_peak",
             "rest_peak", "cap_peak", "keep_gap_min", "keep_peak", "RL_peak", "RL_up_peak", "th_max", "b_max", "b_min", "b_min_rel",
             "th_min_rel", "front_z_min", "ghost_rise", "ghost_frac", "ghost_t40", "ghost_reland", "t40", "t100", "rod_peak",
             "lip_peak", "lip_pull", "t50", "ghost_t_arm", "ghost_v_desc", "steel", "kz_ff", "ky_ff", "kz_over", "ky_over",
             "ghost_long", "t_run", "frac_end", "ghost_settle", "ghost_creep", "ghost_land_est", "mag_travel", "t_bottom")
    return {k: ev.get(k) for k in keys_}


HOLDS_PLAY = (None, 0.45, 0.5, 0.55, 0.6, 0.8, 1.0, 2.0)
HOLDS_ABUSE = (None, 0.45, 0.6, 1.0, 2.0)


def hl(h):
    return "rel" if h is None else "h%.2f" % h


def dyn_cases(P, g, felt=None, fmul=1.0, seat_k=None, vf=None, pads=None, holds_play=HOLDS_PLAY, holds_abuse=HOLDS_ABUSE, full=True, v_play=None):
    v_front_play = P["v_play"] if v_play is None else v_play
    """all dynamic cases for the representative white (D) and black (C#) key.  r4 envelopes: PLAY = key-front speed 1.5
    m/s at the felt contact, fingers released or held 0.45-2 N; ABUSE = 2.5 m/s; 'ff' = 1.0 m/s; 'cons' = 1.5 m/s at the
    FINGER at the start (front ~1.8-1.9 m/s at the felt: a margin check).  Constant-force presses 0.8-6 N and the
    release from a truly settled 1 N hold (1.2 s)."""
    out = {}
    for A, col in ((g["Aw"], "white"), (g["Ab"], "black")):
        pad = None if pads is None else pads[col]
        D = dyn_for(g, A, felt=felt, fmul=fmul, seat_k=seat_k, vf=vf, pad=pad)
        st = D.run(300.0)["state"]
        r = dict(rest_state=st, rest_b=st[1], rest_th=st[0])
        v0p = v0_for_front(D, st, v_front_play)
        v_ab = v0_for_front(D, st, P["v_abuse"])
        v_ff = v0_for_front(D, st, P["v_ff"]) if full else None
        v_ch = v0_for_front(D, st, P["v_abuse_chord"]) if full else None
        r.update(v0_play=v0p, v0_abuse=v_ab, v0_ff=v_ff, v0_chord=v_ch, v_front_play=v_front_play)
        for h in holds_play:
            r["play_" + hl(h)] = ev_summary(strike(D, st, v0p, F_hold=h, t_end=320.0))
        for h in holds_abuse:
            r["abuse_" + hl(h)] = ev_summary(strike(D, st, v_ab, F_hold=h, t_end=320.0))
        if full:
            for F, lab in ((0.8, "pp"), (1.5, "mf"), (3.0, "ff_push"), (6.0, "push6")):
                r[lab] = ev_summary(press(D, F, st))
            for h in (None, 1.0):
                r["ff_" + hl(h)] = ev_summary(strike(D, st, v_ff, F_hold=h, t_end=320.0))
                r["chord20_" + hl(h)] = ev_summary(strike(D, st, v_ch, F_hold=h, t_end=320.0))
            for h in (None, 0.45, 1.0):
                r["cons_" + hl(h)] = ev_summary(strike(D, st, 1.5, F_hold=h, t_end=320.0))
            r["release"] = ev_summary(release_from_bottom(D, st))
        out[col] = r
    return out


def extremes(dc):
    """pose extremes over all dynamic cases of one colour."""
    cases = [v for k, v in dc.items() if isinstance(v, dict) and "b_max" in v]
    return dict(b_max=max(c["b_max"] for c in cases), b_min_rel=min(c["b_min_rel"] for c in cases),
                th_max=max(c["th_max"] for c in cases), th_min_rel=min(c["th_min_rel"] for c in cases),
                pen_max=max(c["pen_up_max"] for c in cases), up_peak=max(c["up_peak"] for c in cases),
                rest_b=dc["rest_b"], rest_th=dc["rest_th"],
                kz_ff=min(c.get("kz_ff") or 1e9 for c in cases), kz_over=min(c.get("kz_over") or 1e9 for c in cases))


def finish_geo(P, g, dyn):
    """poses from the dynamic extremes (sweep), balance-rail lowering under the blocks, removal hold angle."""
    ew, eb = extremes(dyn["white"]), extremes(dyn["black"])
    g["ext"] = dict(white=ew, black=eb)
    margin = math.radians(0.25)
    g["b_ff_w"], g["b_ff_b"] = ew["b_max"] + margin, eb["b_max"] + margin
    g["b_over_w"], g["b_over_b"] = ew["b_min_rel"] - margin, eb["b_min_rel"] - margin
    g["b_rest_w"], g["b_rest_b"] = ew["rest_b"], eb["rest_b"]
    g["a_ff_w"], g["a_ff_b"] = ew["th_max"] + math.radians(0.1), eb["th_max"] + math.radians(0.1)
    g["a_over_w"], g["a_over_b"] = min(ew["th_min_rel"], 0.0), min(eb["th_min_rel"], 0.0)
    rem_w, rem_b = g["removal_w"], g["removal_b"]
    need_deg = max(rem_w["lever_angle_needed_deg"], rem_b["lever_angle_needed_deg"])
    g["b_hold_removal"] = math.radians(max(12.0, round(need_deg + 0.5, 1)))
    zb_ = P["K"][1] + P["block_lift"]
    zs_ = P["block_step_z"]
    yl0_, yl1_ = block_lip_y(P)
    zmin = 1e9
    for a_ in (g["a_ff_w"], g["a_ff_b"], g["a_over_w"], g["a_over_b"], g["Aw"].a_dip, g["Ab"].a_dip):
        for pt_ in ((yl0_, zb_), (yl1_, zb_), (P["block_y"][0], zs_), (P["block_y"][1], zs_)):
            zmin = min(zmin, rot(pt_, P["K"], a_)[1])
    g["z_block_min"] = zmin
    g["z_rail_low"] = math.floor((zmin - P["cradle_clear"] - 0.05) * 10) / 10
    g["pad_comp_ratio_w"] = ew["pen_max"] / P["pad_h"]
    g["pad_comp_ratio_b"] = eb["pen_max"] / P["pad_h"]
    return g


def poses_for(P, g):
    """sweep poses.  keys: rest / dip (truly settled 1 N bottom WITH the pad) / dip_rigid (rigid kinematic bottom) / ff /
    over.  levers: settled rest / dip (settled 1 N bottom with the pad) / dip_rigid / ff (max angle over all cases incl.
    the 2.5 m/s abuse) / over (return overshoot).
    r4.4 (R44 issue 3): the key 'dip' is the settled 1 N bottom for BOTH colours (r4.3 took max(held, rigid), i.e. the
    rigid 6.22 deg for the black keys whose lever meets the pad first); the rigid bottom is its own pose 'dip_rigid'
    (swept too).  r4.4 (R44 issue 2): g['over_key'] = {key: (a_over, b_over)} overrides the colour's overshoot pose with
    the key's own (F / F# land on part of their rest felt beside the USB slot and overshoot further)."""
    keys = g["keys"]
    pk, pl = {}, {}
    for nm in ORDER:
        blk = keys[nm]["black"]
        A = g["Ab"] if blk else g["Aw"]
        c = "b" if blk else "w"
        hs = g["held_pad_b"] if blk else g["held_pad_w"]
        ov = g.get("over_key", {}).get(nm)
        pk[nm] = dict(rest=0.0, dip=hs[0], ff=g["a_ff_" + c], over=g["a_over_" + c] if ov is None else min(ov[0], g["a_over_" + c]), dip_rigid=A.a_dip)
        pl[nm] = dict(rest=g["b_rest_" + c], dip=hs[1], ff=g["b_ff_" + c], over=g["b_over_" + c] if ov is None else min(ov[1], g["b_over_" + c]),
                      rigid0=A.solve_b(0.0), dip_rigid=A.b_dip)
        for q, f in (("q1", 0.25), ("q2", 0.5), ("q3", 0.75)):
            pk[nm][q] = f * A.a_dip
            pl[nm][q] = A.solve_b(f * A.a_dip)
        if g.get("key_shift"):
            # r4.4 fix 2 (verifier geometry major 3): translation of the key after the rotation about K (notch seated on /
            # sinking into its cloth on the rod): rest / dip exact planar states, ff / over the dynamic extremes
            sh_ = dict(g["key_shift"][c])
            if ov is not None and "over_key" in g["key_shift"] and nm in g["key_shift"]["over_key"]:
                sh_["over"] = g["key_shift"]["over_key"][nm]
            pk[nm]["_shift"] = sh_
    return pk, pl


def key_pose_shifts(P, g, dyn, extra_kz=None):
    """r4.4 fix 2 (verifier geometry major 3): per colour, the translation of the key after its rotation about K for each sweep
    pose: rest = the dynamic rest state, dip = the settled 1 N bottom with the pad (exact, = export), dip_rigid / q1-q3 =
    the rest seating, ff = the lowest rod point over every dynamic case near / past the bottom, over = the lowest rod point
    while the key overshoots above rest.  Also the balance-rail pocket under a colour's blocks when its lip region comes
    within 1.3 of z_rail_low in any of these poses."""
    K = P["K"]
    out = {}
    zb_ = K[1] + P["block_lift"]
    yl0_, yl1_ = block_lip_y(P)
    pocket = {}
    for col, c, A in (("white", "w", g["Aw"]), ("black", "b", g["Ab"])):
        rest = key_point_world(A, dyn[col]["rest_state"], K)
        t_rest = (rest[0] - K[0], rest[1] - K[1])
        hd = key_point_world(A, g["held_pad_" + c], K)
        ex = extremes(dyn[col])
        xk_ = (extra_kz or {}).get(col, {})
        kz_ff = min(ex["kz_ff"], xk_.get("ff", 1e9))
        kz_ov = min(ex["kz_over"], xk_.get("over", 1e9))
        kz_ff = kz_ff if kz_ff < 1e8 else t_rest[1]
        kz_ov = min(kz_ov if kz_ov < 1e8 else t_rest[1], t_rest[1])
        sh = dict(rest=t_rest, dip=(hd[0] - K[0], hd[1] - K[1]), dip_rigid=t_rest, q1=t_rest, q2=t_rest, q3=t_rest,
                  ff=(0.0, min(kz_ff, t_rest[1])), over=(0.0, kz_ov))
        out[c] = sh
        # lowest point of the block's lip region (its front / rear bottom corners) in the swept poses
        pk_ = dict(dip=(g["held_pad_" + c][0], sh["dip"]), ff=(g["a_ff_" + c], sh["ff"]), over=(g["a_over_" + c], sh["over"]),
                   dip_rigid=(A.a_dip, sh["dip_rigid"]))
        lo = []
        for pz, (a_, t_) in pk_.items():
            for pt_ in ((yl0_, zb_), (yl1_, zb_)):
                q_ = rot(pt_, K, a_)
                lo.append((q_[1] + t_[1], q_[0] + t_[0], pz))
        zmin, ymin, pz_min = min(lo)
        need = zmin - P["cradle_clear"]
        if need < g["z_rail_low"] - 1e-9:
            zp = math.floor((need - 0.02) * 20) / 20
            # the pocket's front edge: the z_rail_low top must stay >= 1.3 (+0.02) from the lowest front corner
            yp = 1e9
            for zc, yc_, pz in lo:
                dz_ = zc - g["z_rail_low"]
                if dz_ < P["cradle_clear"] + 0.02:
                    yp = min(yp, yc_ - math.sqrt(max(0.0, (P["cradle_clear"] + 0.02) ** 2 - dz_ ** 2)))
            yp = min(P.get("rail_pocket_y0", 137.4), math.floor(yp * 10) / 10)
            pocket[col] = dict(z=zp, y=yp, zmin=zmin, pose=pz_min)
        else:
            pocket[col] = None
    g["key_shift"] = out
    g["rail_pocket"] = pocket
    return out, pocket
def carrier_wall_plate(P, F_wall, a_contact=0.5, h=0.5, clamp_ends=False, zone=None, E=E_PETG, nu=0.35):
    """r4.4 fix 2 (verifier physics majors 1-2): one carrier side wall as a plate (grillage of 0.5 mm beams, Kirchhoff
    equivalents EI = E h t^3/12, GJ = G h t^3/6) in the lever frame, w = outward.  Supports: w = 0 along the front wall
    (y150, z33-53) and the rear wall (y190, z32-50) (pinned, or clamped), the full-width front cap ties the wall top over
    y150-153; the steel side face stops inward motion (unilateral, iterated).  Load: the bottom-lip line load F_wall over
    the bottom-lip zone (or `zone`) applied a_contact inside the wall's inner face, i.e. a line moment F/L (t/2 + a) at the
    wall's bottom edge (the vertical force itself is in the wall plane).  Returns the outward spread of the lip line (max /
    mean), its rotation (flank), the wall bending stress at the lip root (6 m / t^2) and the plate's max bending stress."""
    import scipy.sparse as sp_, scipy.sparse.linalg as spl_
    t = P.get("carrier_side_wall", P["carrier_wall"])
    y0, y1 = P["y_steel_front"], P["y_steel_rear"]
    lf, lr = zone if zone is not None else (P["lip_front_y"], P["felt_c_y"][0])
    zst, zsb, lp = P["z_st"], P["z_sb"], P["lip"]
    segs = sorted(P["lip_segs"])
    dr = P.get("wall_drop_pad", 0.0)

    def ztop(y):
        for a, b in segs:
            if a - 1e-9 <= y <= b + 1e-9:
                return zst + lp
        return zst - dr

    def zbot(y):
        return zsb - lp if y >= lf - 1e-9 else zsb
    ys = np.arange(y0, y1 + 1e-9, h)
    zs = np.arange(zsb - lp, zst + lp + 1e-9, h)
    nodes, pts = {}, []
    for i, y in enumerate(ys):
        for j, z in enumerate(zs):
            if zbot(y) - 1e-9 <= z <= ztop(y) + 1e-9:
                nodes[(i, j)] = len(pts)
                pts.append((y, z))
    ndof = 3 * len(pts)
    G_ = E / (2 * (1 + nu))
    rows, cols, vals = [], [], []

    def beam(a, b, L, wdt, along):
        EI, GJ = E * wdt * t ** 3 / 12.0, G_ * wdt * t ** 3 / 6.0
        kb = EI / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L], [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        if along == "y":
            idx, T = [3 * a, 3 * a + 2, 3 * b, 3 * b + 2], np.diag([1, -1, 1, -1])
            kb, ti = T @ kb @ T, [3 * a + 1, 3 * b + 1]
        else:
            idx, ti = [3 * a, 3 * a + 1, 3 * b, 3 * b + 1], [3 * a + 2, 3 * b + 2]
        for p_ in range(4):
            for q_ in range(4):
                rows.append(idx[p_]); cols.append(idx[q_]); vals.append(kb[p_, q_])
        kt = GJ / L
        for p_, q_, v_ in ((0, 0, kt), (0, 1, -kt), (1, 0, -kt), (1, 1, kt)):
            rows.append(ti[p_]); cols.append(ti[q_]); vals.append(v_)
    for (i, j), a in nodes.items():
        if (i + 1, j) in nodes:
            beam(a, nodes[(i + 1, j)], h, h if ((i, j + 1) in nodes and (i, j - 1) in nodes) else h / 2, "y")
        if (i, j + 1) in nodes:
            beam(a, nodes[(i, j + 1)], h, h if ((i + 1, j) in nodes and (i - 1, j) in nodes) else h / 2, "z")
    Km = sp_.csr_matrix((vals, (rows, cols)), shape=(ndof, ndof))
    Fv = np.zeros(ndof)
    q = F_wall / (lr - lf)
    e = t / 2 + a_contact
    edge = []
    for (i, j), a in nodes.items():
        y, z = pts[a]
        if lf - 1e-9 <= y <= lr + 1e-9 and (i, j - 1) not in nodes:
            Fv[3 * a + 1] += -q * e * (h if (lf + 1e-9 < y < lr - 1e-9) else h / 2)
            edge.append(a)
    fixed = set()
    for a, (y, z) in enumerate(pts):
        if (abs(y - y0) < 1e-6 and z >= zsb - 1e-9) or (abs(y - y1) < 1e-6 and z <= P["rear_wall_top"] + 1e-9):
            fixed.add(3 * a)
            if clamp_ends:
                fixed.add(3 * a + 2)
        if y <= y0 + 3.0 + 1e-9 and z >= zst - 1e-9:
            fixed.add(3 * a)
    contact = set()
    u = np.zeros(ndof)
    for _ in range(30):
        fx = sorted(fixed | {3 * a for a in contact})
        free = np.setdiff1d(np.arange(ndof), fx)
        u = np.zeros(ndof)
        u[free] = spl_.spsolve(Km[free][:, free].tocsc(), Fv[free])
        Rr = Km @ u - Fv
        new = set(a for a in contact if Rr[3 * a] >= 0)
        new |= set(a for a, (y, z) in enumerate(pts) if zsb <= z <= zst and u[3 * a] < -1e-6)
        if new == contact:
            break
        contact = new
    smax = 0.0
    for (i, j), a in nodes.items():
        for di, dj in ((1, 0), (0, 1)):
            if (i + di, j + dj) in nodes and (i - di, j - dj) in nodes:
                k2 = (u[3 * nodes[(i + di, j + dj)]] - 2 * u[3 * a] + u[3 * nodes[(i - di, j - dj)]]) / h ** 2
                smax = max(smax, E * abs(k2) * t / 2)
    wl = [u[3 * a] for a in edge]
    return dict(spread_max=float(max(wl)), spread_mean=float(np.mean(wl)), flank_deg=math.degrees(max(abs(u[3 * a + 1]) for a in edge)),
                s_root=6 * q * e / t ** 2, s_plate=smax, q=q, e=e, n_nodes=len(pts), clamp=clamp_ends)


def steel_bond(P):
    """r4.4 fix 2: the bonded side faces (both, lever frame): the steel's 19 x 40 faces where the wall covers them
    (y150-190, z33 to the wall top; the pad-zone strip above the lowered wall is not bonded).  Returns area, centroid, polar
    moment (y-z plane) and the farthest point."""
    sf, sr, zsb, zst = P["y_steel_front"], P["y_steel_rear"], P["z_sb"], P["z_st"]
    segs = sorted(P["lip_segs"])
    rects = []
    y_ = sf
    for (a0, a1), nxt in zip(segs, segs[1:] + [None]):
        rects.append((max(a0, sf), min(a1, sr), zsb, zst))
        if nxt is not None and nxt[0] > a1:
            rects.append((a1, nxt[0], zsb, zst - P.get("wall_drop_pad", 0.0)))
    A_ = sum((b - a) * (d - c) for a, b, c, d in rects)
    cy = sum((b - a) * (d - c) * (a + b) / 2 for a, b, c, d in rects) / A_
    cz = sum((b - a) * (d - c) * (c + d) / 2 for a, b, c, d in rects) / A_
    J_ = sum((b - a) * (d - c) * (((b - a) ** 2 + (d - c) ** 2) / 12 + ((a + b) / 2 - cy) ** 2 + ((c + d) / 2 - cz) ** 2) for a, b, c, d in rects)
    rmax = max(math.hypot(y - cy, z - cz) for a, b, c, d in rects for y in (a, b) for z in (c, d))
    return dict(area=2 * A_, area_face=A_, c=(cy, cz), J=2 * J_, rmax=rmax, rects=rects)


def bond_thermal(P, dT, G=None, t_a=None):
    """r4.4 fix 2b (verifier physics major 1): edge shear stress in the side-face bond from the PETG / steel thermal mismatch.
    Shear lag of a thin flexible adherend (the side wall, E_PETG x carrier_side_wall per unit width) on a rigid one (the steel)
    over a long overlap (40 mm >> 1/lambda): tau = dalpha dT sqrt(G E_w t_w / t_a); 1/lambda = sqrt(E_w t_w t_a / G)."""
    G = P["bond_G"] if G is None else G
    t_a = P["bond_t"] if t_a is None else t_a
    tw = P.get("carrier_side_wall", P["carrier_wall"])
    lam = math.sqrt(G / (E_PETG * tw * t_a))
    return dict(tau=(P["cte_petg"] - P["cte_steel"]) * dT * math.sqrt(G * E_PETG * tw / t_a), lag=1.0 / lam,
                slip_k=G * steel_bond(P)["area"] / t_a)


def beam_fe(xs_support, loads, L0, L1, EI, n_el=400):
    """continuous beam x in [L0, L1] on pinned supports; point loads [(x, F up>0)].
    Returns reactions (list), max |M| (N mm), max |deflection| (mm)."""
    xs = np.linspace(L0, L1, n_el + 1)
    nn = len(xs)
    Kg = np.zeros((2 * nn, 2 * nn))
    for e in range(n_el):
        h = xs[e + 1] - xs[e]
        k = EI / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                    [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        Kg[np.ix_(idx, idx)] += k
    f = np.zeros(2 * nn)
    for x, F in loads:
        i = int(np.argmin(abs(xs - x)))
        f[2 * i] += F
    sup = [int(np.argmin(abs(xs - x))) for x in xs_support]
    fixed = [2 * i for i in sup]
    free = [i for i in range(2 * nn) if i not in fixed]
    u = np.zeros(2 * nn)
    u[free] = np.linalg.solve(Kg[np.ix_(free, free)], f[free])
    R = Kg @ u - f
    reac = [float(-R[2 * i]) for i in sup]          # support force on the beam (+ = pulls down / holds)
    # moments from element end rotations
    Mmax = 0.0
    for e in range(n_el):
        h = xs[e + 1] - xs[e]
        v1, t1, v2, t2 = u[2 * e], u[2 * e + 1], u[2 * e + 2], u[2 * e + 3]
        M1 = EI / h ** 2 * (-6 * v1 - 4 * h * t1 + 6 * v2 - 2 * h * t2)
        Mmax = max(Mmax, abs(M1))
    return reac, Mmax, float(np.max(np.abs(u[0::2])))



def rest_stresses(P, g):
    """constant (rest) stresses in the printed parts: tails, hidden beam, notch section, cloth / hub / boss bearing,
    rear shelf, torsion-spring leg on the rear-wall groove.  r4: no preloaded joint left (no screws, no disc springs)."""
    out = {}
    for A in (g["Aw"], g["Ab"]):
        nm = "black" if A.black else "white"
        s = A.statics(1e-4)
        N0 = s["N"]
        yr = sum(P["rest_pad_y"]) / 2
        Mg = A.mk * G * (A.K[0] - A.ck[0])
        Rs = (N0 * (A.y_cap - A.K[0]) - Mg) / (yr - A.K[0])
        Rk = A.mk * G + N0 - Rs
        t_tail = P["tail_top"] - P["beam_z"][0]
        s_tail = Rs * (yr - (A.y_cap + 4.0)) / (tail_w(P, A.black) * t_tail ** 2 / 6)
        hb = P["beam_z"][1] - P["beam_z"][0]
        M_beam = abs(N0 * (A.y_cap - P["y_body_end"]) - Rs * (yr - P["y_body_end"]))
        s_beam = M_beam / (P["beam_w"] * hb ** 2 / 6)
        hcap = P["beam_z_cap"] - P["beam_z"][0]
        s_beam_cap = abs(Rs * (yr - (A.y_cap - 6.0))) / (P["beam_w"] * hcap ** 2 / 6)
        hn = P["block_top"] - (P["K"][1] + P["notch_R"])
        s_notch = Mg / (P["beam_w"] * hn ** 2 / 6)
        p_cloth = Rk / (P["rod_k"] * P["beam_w"])
        p_hub = s["RL"] / (P["rod_L"] * P["lever_w"])
        out[nm] = dict(capstan_N=N0, shelf_R=Rs, rod_R=Rk, lever_rod_R=s["RL"], tail=s_tail, beam=s_beam,
                       beam_at_capstan=s_beam_cap, notch_section=s_notch, cloth_p=p_cloth, hub_p=p_hub,
                       spring_T_rest=A.spring_T(s["b"]) if A.spring else 0.0)
    ribs = sorted(g["ribs"] + [(f0 + f1) / 2 for f0, f1 in g["lay"]["fins"]])
    spans = [b - a - P["rib_t"] for a, b in zip(ribs[:-1], ribs[1:])]
    Lsp = max(spans)
    Rs_max = max(out["white"]["shelf_R"], out["black"]["shelf_R"])
    dshelf = P["shelf_y"][1] - P["shelf_y"][0]
    Z = dshelf * 2.0 ** 2 / 6
    out["shelf"] = dict(max_span=Lsp, static=Rs_max * Lsp / 4 / Z, spans=spans, ribs=ribs)
    # torsion spring long leg on the rear-wall groove: leg force = torque / leg length, bearing on the 0.8 groove flank
    T0 = max(out["white"]["spring_T_rest"], out["black"]["spring_T_rest"])
    F_leg = T0 / P["spring_leg"]
    out["spring_leg"] = dict(T_rest=T0, F_leg=F_leg, groove_p=F_leg / (P["spring_d"] * 1.0))
    out["max"] = max(out["white"]["tail"], out["black"]["tail"], out["white"]["beam"], out["black"]["beam"],
                     out["white"]["beam_at_capstan"], out["black"]["beam_at_capstan"],
                     out["white"]["notch_section"], out["black"]["notch_section"], out["shelf"]["static"])
    return out


def lever_rod_loads(P, g, RLw, RLb, fins, levers, keys):
    """lever rod (plain SUS304 D4, cold drawn) between the fins: 6 adjacent levers at their peak rod reaction (chord), or
    the worst single lever; bending stress vs yield, deflection, fin reaction -> printed fin-boss bearing (no bushing)."""
    fc = [(f0 + f1) / 2 for f0, f1 in fins]
    EIl = P["E_rod_L"] * math.pi * P["rod_L"] ** 4 / 64
    Z = math.pi * P["rod_L"] ** 3 / 32
    bl = fin_boss_len(g["lay"], P)
    boss_len = min((f1 - f0) + a + b for (f0, f1), (a, b) in zip(fins, bl))
    best = None
    for s0 in range(0, 7):
        names = ORDER[s0:s0 + 6]
        loads = [(levers[n], RLb if keys[n]["black"] else RLw) for n in names]
        reac, Mmax, dmax = beam_fe(fc, loads, fc[0], fc[-1], EIl)
        if best is None or Mmax > best["M"]:
            best = dict(keys=names, M=Mmax, sigma=Mmax / Z, defl=dmax, fin_R=max(abs(r) for r in reac))
    single = None
    for n, x in levers.items():
        reac, Mmax, dmax = beam_fe(fc, [(x, RLb if keys[n]["black"] else RLw)], fc[0], fc[-1], EIl)
        if single is None or Mmax > single["M"]:
            single = dict(key=n, M=Mmax, sigma=Mmax / Z, defl=dmax, fin_R=max(abs(r) for r in reac))
    for q in (best, single):
        q["boss_bearing"] = q["fin_R"] / (P["rod_L"] * boss_len)
        q["hub_bearing"] = max(RLw, RLb) / (P["rod_L"] * P["lever_w"])
    return dict(chord=best, single=single, boss_len=boss_len, RL=(RLw, RLb))


def plate_loads(P, g, Fw, Fb, fins, levers, keys, x_range=(0.2, 164.3), extra_fins=(), chords=True):
    """top plate under the pad forces (plate FE): every single key at its colour's peak, and every 6-key chord struck at
    once; plate bending stress (in the layer plane), fin top-junction tension (across layers), rear-wall line load,
    seat deflection under each key and, for chords, the deflection of each chord key's seat (chord-equivalent seat)."""
    prof = g["plate_under"]
    yy = [p[0] for p in prof]
    zz = [p[1] for p in prof]
    zu = lambda y: float(np.interp(y, yy, zz))
    tof = lambda y: g["z_top"] - zu(y)
    wy = P["pad_y"][1] - P["pad_y"][0]
    yl = lambda n: g["y_load_b"] if keys[n]["black"] else g["y_load_w"]
    Fk = lambda n: Fb if keys[n]["black"] else Fw
    names = list(levers)
    cases, labels = [], []
    for n in names:
        cases.append([(levers[n], yl(n), Fk(n), wy, P["pad_w"])])
        labels.append(("single", [n]))
    if chords and len(names) >= 6:
        for s0 in range(0, len(names) - 5):
            ch = names[s0:s0 + 6]
            cases.append([(levers[n], yl(n), Fk(n), wy, P["pad_w"]) for n in ch])
            labels.append(("chord", ch))
    elif chords:
        cases.append([(levers[n], yl(n), Fk(n), wy, P["pad_w"]) for n in names])
        labels.append(("chord", names))
    xs, ys, out = plate_fe(P, list(fins) + list(extra_fins), cases, tof, zu, x0=x_range[0], x1=x_range[1], rail_top=min(g.get("z_rail_low", 99.0), P["rail_top_est"]))
    res = {}
    for (kind, ks), o in zip(labels, out):
        seats = {n: seat_at(xs, ys, o["w"], levers[n], yl(n), P["pad_w"], wy) for n in ks}
        r = res.setdefault(kind, dict(sigma=0.0, fin_top=0.0, w_max=0.0, wall_q=0.0, k_eq=1e9, total=0.0, seat_max=0.0, keel_sigma=0.0, keel_V=0.0))
        for kq_ in o.get("keel", {}).values():
            if kq_["sigma"] > r["keel_sigma"]:
                r["keel_sigma"], r["keel_V"], r["keel_tau"], r["keel_keys"] = kq_["sigma"], abs(kq_["V"]), kq_["tau"], ks
            r["keel_L"], r["keel_h"] = kq_["L"], kq_["h"]              # r4.5 fix 2 (resume): FE keel length / depth
            if abs(kq_.get("w_root", 0.0)) > abs(r.get("keel_w_root", 0.0)):
                r["keel_w_root"], r["keel_rail"] = kq_["w_root"], kq_.get("rail")
        for k, v in (("sigma", o["sigma_out"]), ("fin_top", o["fin_top"]), ("w_max", float(o["w"].max())), ("wall_q", o["wall_q"]),
                     ("total", sum(Fk(n) for n in ks)), ("seat_max", max(seats.values()))):
            if v > r[k]:
                r[k] = v
                r[k + "_keys"] = ks
        k_eq = min(Fk(n) / seats[n] for n in ks if seats[n] > 1e-9)
        if k_eq < r["k_eq"]:
            r["k_eq"] = k_eq
            r["k_eq_keys"] = ks
            r["k_eq_seats"] = {n: float(seats[n]) for n in ks}          # r4.5 fix 2: per-seat deflection of the weakest chord
    return res


# ============================================================================ masses, print plan
def petg_mass(body):
    return sum(e["m"] for e in body.el if e["rho"] == RHO_PETG)


def lever_carrier_mass(P):
    return petg_mass(lever_body(P))


def poly_area(poly):
    return abs(poly_area_centroid(poly)[0])


def plate_area(P, g, y0=None):
    return poly_area(plate_poly(P, g, y0))


def frame_mass(P, g, fins=None, width=164.1):
    """printed frame of one module (volumes x infill): v3 frame minus the v3 spine rail and leaf back-stop rail, plus the
    balance rail (front extended for the pins), rear shelf, ribs, 5 fins with rod bosses and the pad-bar rails, the
    top plate (r4: the r3 bridge extended forward to y146.5, carrying the pad bars), taller rear wall."""
    rho = RHO_PETG
    fins = g["lay"]["fins"] if fins is None else fins
    v3_frame = 175.0
    spine_rail = 13 * 163.5 * 15.7 * 0.35 * rho
    back_stop = 6 * 163.5 * 14.7 * 0.35 * rho
    bal = (P["rail_y"][1] - P["rail_front_y"]) * 163.9 * (P["rail_groove_lip"] - 5.0) * 0.35 * rho
    s0_, s1_ = usb_slot(P)
    shelf = (P["shelf_y"][1] - P["shelf_y"][0]) * (164.5 - (s1_ - s0_)) * 2.0 * rho      # r4.3: minus the USB slot
    ribs = len(g["ribs"]) * P["rib_t"] * (P["shelf_y"][1] - P["rib_y0"]) * (g["z_shelf"] - 2.0 - 5.0) * rho
    zu = np.mean([z for y, z in g["plate_under"] if P["fin_y"][0] <= y <= P["fin_y"][1]])
    fins_g = sum((f1 - f0) for f0, f1 in fins) * (P["fin_y"][1] - P["fin_y"][0]) * (zu - 5.0) * 0.9 * rho
    bosses = len(fins) * math.pi * (P["boss_R"] ** 2 - (P["rod_L"] / 2) ** 2) * (P["fin_t"] + 2 * P["ring_min_lf"]) * rho
    plate = plate_area(P, g) * width * 0.75 * rho              # 75 % fill (4 walls, 5 top/bottom layers, 25 % infill)
    rails = 2 * (len(fins) - 1) * (P["bar_rail"][0] * P["bar_rail"][1] + P["rail_lip"] * P["rail_lip_t"]) * (P["pad_bar_y"][1] - P["rail_y0"]) * rho
    wall = (g["z_top"] - 56.5) * 3.0 * 164.5 * rho
    parts = dict(v3_frame=v3_frame, minus_spine_rail=-spine_rail, minus_back_stop=-back_stop, balance_rail=bal,
                 rear_shelf=shelf, shelf_ribs=ribs, fins=fins_g, fin_bosses=bosses, top_plate=plate, bar_rails=rails,
                 taller_rear_wall=wall)
    if P.get("board_hatch") and width > 100:
        # r4.4 fix 2b: floor opened under the board, keel of the F|F# foot, four hung bosses (the floor stand-offs are gone)
        hx0, hx1, hy0, hy1 = P["board_hatch"]
        nx0, nx1, ny1 = P.get("board_hatch_notch", (0.0, 0.0, hy1))
        a_h = (hx1 - hx0) * (hy1 - hy0) + (nx1 - nx0) * (ny1 - hy1) - (P["fin_t"] - 2 * P["fin_ext_inset"]) * (P["fin_y"][0] - hy0)
        ky, kz0, kz1 = P["fin_keel"]
        # r4.5 fix 2 (resume): keel to keel_front + the F|F# fin's forward extension (keel_front .. fin_y[0], z3 to the plate)
        v_keel = (P["fin_t"] - 2 * P["fin_ext_inset"]) * ((keel_front(P) - ky) * (kz1 - kz0) + (P["fin_y"][0] - keel_front(P)) * (zu - kz0))
        v_boss = sum((q[1] - q[0]) * (q[3] - q[2]) * (q[5] - q[4]) for q in board_boss_rects(P, g["z_shelf"] - 2.0))
        v_so = len(P["board_standoffs"]) * math.pi / 4 * P["standoff_d"] ** 2 * (P["board_z"][0] - P["z_floor"][1])
        parts.update(floor_board_hatch=-a_h * (P["z_floor"][1] - P["z_floor"][0]) * rho, fin_keel=v_keel * rho, board_bosses=(v_boss - v_so) * rho)
    if width > 100:
        # r4.5: the 12 torsion-spring bosses on the rear-wall face minus their grooves (boss spring_boss[0] x spring_boss[2] from z
        # spring_boss[1] to the plate underside; groove spring_groove[3] wide over z spring_groove[1..2], spring_groove[4] deep from
        # the boss face, i.e. partly into the rear wall) - not in the frame mass before r4.5
        bw_, zb_, pr_ = P["spring_boss"]
        sgm_ = P["spring_groove"]
        zu_ = min(z for y, z in g["plate_under"] if y >= P["rear_wall"][0] - pr_ - 0.5)
        n_lev = len(g["lay"]["levers"]) if "lay" in g else 12
        parts.update(spring_bosses=n_lev * (bw_ * pr_ * (zu_ - zb_) - sgm_[3] * sgm_[4] * (sgm_[2] - sgm_[1])) * rho)
    return sum(parts.values()), parts


def plate_support_mass(P, g, width=164.1):
    """tree supports under the top plate (frame printed upright): from the floor / shelf up to the plate underside,
    between the fins, ~12 % of the enclosed volume."""
    area = 0.0
    prof = g["plate_under"]
    for (y0, z0), (y1, z1) in zip(prof[:-1], prof[1:]):
        zbase = g["z_shelf"] if y0 >= P["shelf_y"][0] else P["z_floor"][1]
        area += (y1 - y0) * ((z0 + z1) / 2 - zbase)
    return area * width * 0.12 * RHO_PETG


def pad_bar_mass(P, g, bay_w):
    """one printed pad bar (stepped plate + grip + wedges for 3 pads)."""
    t = P["pad_bar_t"]
    L = P["pad_bar_y"][1] - P["pad_bar_y"][0]
    w = bay_w - 2 * (P["bar_rail"][0] + P["pad_bar_clear"])
    wedge = max(g["wedge_range"]["w"][1], g["wedge_range"]["b"][1])
    v = w * L * t + w * 1.0 * P["pad_bar_grip"] + w * t * t + 3 * P["pad_w"] * (P["pad_y"][1] - P["pad_y"][0]) * wedge * 0.8
    return v * 0.8 * RHO_PETG


def curtain_mass(P, g, width=164.1):
    v = width * P["curtain_t"] * (g["z_top"] - g["z_curtain_w"]) + width * P["curtain_hook"][0] * P["curtain_hook"][1]
    return v * 0.9 * RHO_PETG


def support_mass(P, black):
    """tree supports under the hidden beam/tail when the key is printed top-down (v3 orientation)."""
    h = (P["black_top"] if black else P["key_top"]) - P["beam_z"][1]
    return (P["y_tail_end"] - P["y_body_end"]) * P["beam_w"] * h * 0.20 * RHO_PETG


def pad_mass(P):
    """one pad: foam (0.3 g/cm3) + 1T felt."""
    a = P["pad_w"] * (P["pad_y"][1] - P["pad_y"][0])
    return a * P["pad_foam"] * 0.3e-3 + a * P["pad_felt"] * RHO_FELT


# ============================================================================ service checks (key out, pad bar out)
def fixed_fixed_checks(P, g):
    """checks between fixed parts that the moving-part sweep does not cover: seams, USB plug, dovetail zone vs end fins,
    pad-bar rails vs fins."""
    out = {}
    out["seam_gap_plates"] = (P["module_w"] + 0.2) - (P["module_w"] - 0.2)
    out["seam_gap_end_fins"] = (P["module_w"] + g["lay"]["fins"][0][0]) - g["lay"]["fins"][-1][1]
    F = fixed_prisms(P, g)
    plug = [f for f in F if f[0].startswith("USB-C plug")][0]
    best = (1e9, None)
    per = {}
    for f in F:
        if f[0].startswith(("rear shelf", "fin", "shelf rib", "rear wall")):
            d, mode = prism_dist((f[1], f[2]), f[3], (plug[1], plug[2]), plug[3])
            k_ = f[0].split(" (")[0]
            per[k_] = min(per.get(k_, 1e9), d)
            if d < best[0]:
                best = (d, f[0])
    out["usb_plug_min"] = best
    out["usb_plug_each"] = per
    # r4.3: printed frame parts vs the BRD-01 parts and the component envelope (purchased / hand-built, fixed)
    # r4.4: + the control-board stand-offs / locating pins (frame) and the M3x6 heads (on the board)
    frame = [f for f in F if f[0].startswith(("rear shelf", "fin", "shelf rib", "rear wall", "balance rail", "spring groove boss",
                                              "control-board stand-off", "control-board locating pin", "control-board screw", "control-board boss"))]
    bparts = [f for f in F if f[0].startswith(("board part", "board components"))]
    res = {}
    for b in bparts:
        bb = (1e9, None)
        for f in frame:
            if f[2] < b[1] - 6 or f[1] > b[2] + 6:
                continue
            if b[0].startswith("board part: J301") and "ribbon under the board" in b[0] and f[0].startswith("balance rail"):
                continue                      # the ribbon passes under the rail in its lane (lane margins below)
            if b[0].startswith("board components") and f[0].startswith("control-board"):
                continue                      # r4.4: the 4 stand-off spots are reserved in BRD-01 (named parts checked)
            d, mode = prism_dist((f[1], f[2]), f[3], (b[1], b[2]), b[3])
            if d < bb[0]:
                bb = (d, f[0])
        res[b[0]] = bb if b[0] not in res or bb[0] < res[b[0]][0] else res[b[0]]
    out["board_vs_frame"] = res
    named = {k: v for k, v in res.items() if k.startswith("board part")}
    out["board_parts_min"] = min(named.values(), key=lambda q: q[0]) if named else (1e9, None)
    out["board_parts_min_name"] = min(named, key=lambda k: named[k][0]) if named else None
    # r4.3: the 16-core ribbon in the lane under the balance rail (x walls of the lane)
    wr = P["ribbon_cores"] * P["ribbon_pitch"]
    xc = P.get("ribbon_xc", 0.5 * (P["ribbon_pads"][0] + P["ribbon_pads"][1]))     # r4.4: centred on SB J201 in the lane
    out["ribbon_lane"] = dict(width=wr, lane=tuple(P["ribbon_x"]), left=(xc - wr / 2) - P["ribbon_x"][0], right=P["ribbon_x"][1] - (xc + wr / 2),
                              height=10.0 - P["z_floor"][1])
    dz = [f for f in F if f[0].startswith("rear dovetail (female")][0]
    best = (1e9, None)
    for f in F:
        if f[0] == "fin":
            d, mode = prism_dist((f[1], f[2]), f[3], (dz[1], dz[2]), dz[3])
            if d < best[0]:
                best = (d, f[0])
    out["dovetail_zone_vs_end_fin"] = best
    return out


def _circ_rect_dist(cx, cy, r, x0, x1, y0, y1):
    """plan distance from a circle (centre, radius) to an axis-aligned rectangle (< 0 = overlap)."""
    dx = max(x0 - cx, 0.0, cx - x1)
    dy = max(y0 - cy, 0.0, cy - y1)
    if dx == 0.0 and dy == 0.0:
        return -r - min(cx - x0, x1 - cx, cy - y0, y1 - cy)
    return math.hypot(dx, dy) - r


def _box_of(f):
    ys = [q[0] for q in f[3]]
    zs = [q[1] for q in f[3]]
    return f[1], f[2], min(ys), max(ys), min(zs), max(zs)


def _rect_rect_dist(a, b):
    """plan distance between rectangles (x0, x1, y0, y1)."""
    dx = max(0.0, b[0] - a[1], a[0] - b[1])
    dy = max(0.0, b[2] - a[3], a[2] - b[3])
    return math.hypot(dx, dy)


def _box_box_dist(a, b):
    """distance between boxes (x0, x1, y0, y1, z0, z1)."""
    dx = max(0.0, b[0] - a[1], a[0] - b[1])
    dy = max(0.0, b[2] - a[3], a[2] - b[3])
    dz = max(0.0, b[4] - a[5], a[4] - b[5])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _clip_below(poly, zc):
    """part of a (y, z) polygon with z <= zc (Sutherland-Hodgman, one edge)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        pin, qin = p[1] <= zc + 1e-9, q[1] <= zc + 1e-9
        if pin:
            out.append(p)
        if pin != qin:
            t = (zc - p[1]) / (q[1] - p[1])
            out.append((p[0] + t * (q[0] - p[0]), zc))
    return out


def board_insert_check(P, g):
    """r4.4 fix 2b (verifier geometry critical): the control board's way in.  With the frame upside down (or on its side) the
    board with every BRD-01 part on it moves straight along z from outside the floor through the board hatch to its seat
    under the hung bosses (its slot sliding along the F|F# foot and keel).  A straight z path meets a fixed part only where
    they overlap in plan, so along the path the clearance of a board prism to a fixed prism is their plan distance, counted
    for the part of the fixed prism below the board prism's top at the seat (clipped y-z outline); a fixed part overlapping a
    board prism in plan must lie wholly above it (a stop: the hung bosses, contact 0 by design).  Only the frame is there
    (board first in the assembly).  The flexible ribbon / leads under the board follow the board.  Locating pins: radial
    play (hole - pin) / 2."""
    F = fixed_prisms(P, g)
    brd = [f for f in F if f[0].startswith("control board") or (f[0].startswith("board part") and "under the board" not in f[0])]
    skip = ("control board", "board part", "board components", "control-board screw", "control-board locating pin", "USB-C plug",
            "pad bar", "pad wedge", "up-stop pad", "cover curtain", "lever rod", "fin boss bore", "balance pin", "sensor board SB",
            "white front felt", "rear dovetail", "front dovetail")
    frame = [f for f in F if not f[0].startswith(skip)]
    rows, stops = [], []
    for b in brd:
        bys = [p[0] for p in b[3]]
        bzs = [p[1] for p in b[3]]
        bt = max(bzs)
        for f in frame:
            cl = _clip_below(f[3], bt - 1e-6)
            if len(cl) < 3:
                if _rect_rect_dist((b[1], b[2], min(bys), max(bys)), (f[1], f[2], min(p[0] for p in f[3]), max(p[0] for p in f[3]))) < 1e-9:
                    stops.append((b[0], f[0], min(p[1] for p in f[3]) - bt))
                continue
            cy0, cy1 = min(p[0] for p in cl), max(p[0] for p in cl)
            ox = min(b[2], f[2]) - max(b[1], f[1])
            oy = min(max(bys), cy1) - max(min(bys), cy0)
            if ox > 1e-6 and oy > 1e-6:
                rows.append((-min(ox, oy), b[0], f[0]))
            else:
                rows.append((_rect_rect_dist((b[1], b[2], min(bys), max(bys)), (f[1], f[2], cy0, cy1)), b[0], f[0]))
    rows.sort()
    worst = {}
    for d, a, b in rows:
        worst.setdefault(b, (d, a))
    return dict(min=rows[0][0], pair=rows[0][1:], by_fixed=sorted(((v[0], k, v[1]) for k, v in worst.items()))[:12],
                stops=sorted(set((round(z, 3), a, b) for a, b, z in stops)), n=len(rows),
                pin_play=(P["board_hole"] - P["board_pin"][0]) / 2, hatch=tuple(P.get("board_hatch", ())), notch=tuple(P.get("board_hatch_notch", ())))


def _circ_box_dist(cx, cy, r, z0, z1, box):
    """3D distance between a vertical cylinder (plan circle, z0..z1) and an axis-aligned box."""
    x0, x1, y0, y1, bz0, bz1 = box
    dpl = _circ_rect_dist(cx, cy, r, x0, x1, y0, y1)
    dz = max(bz0 - z1, z0 - bz1, 0.0)
    if dpl <= 0.0:
        return dz if dz > 0 else dpl
    return math.hypot(dpl, dz)


def circuit_c44_checks(P, g, ep):
    """r4.4: the circuit session's cross-check requests on the r4.3 model (hardware/pcb README 'W1 기구 쪽에 요청한 것'),
    measured on this model: stand-offs / M3x6 heads / locating pins (plan-exact circles), the ribbon under the board and
    in its lane, the USB plug envelope over its whole y range, the RP2040-Zero over the keep-out, the SB rear-rib gap, the
    end parts' sensor-board support, rear-rib gaps, lead lanes and rear-wall notches."""
    out = {}
    F = fixed_prisms(P, g)
    zf = P["z_floor"][1]
    zb0, zb1 = P["board_z"]
    bx0, bx1 = P["board_x"]
    by0, by1 = P["board_y"]
    rail = (P["rail_x"][0], P["rail_x"][1], P["rail_front_y"], P["rail_y"][1])
    ribs = [(xr - P["rib_t"] / 2, xr + P["rib_t"] / 2, P["rib_y0"], P["shelf_y"][1]) for xr in g["ribs"]]
    hd, hk, hl = P["board_screw"]
    pd, ph = P["board_pin"]
    rs = P["standoff_d"] / 2
    named = [f for f in F if f[0].startswith("board part")]
    fins = [f for f in F if f[0] == "fin" or f[0].startswith("fin keel")]
    so = []
    hung = P.get("board_mount") == "hung"
    boss_ = {(q[7], q[8]): q for q in board_boss_rects(P, g["z_shelf"] - 2.0)} if hung else {}
    for x, y, kind in P["board_standoffs"]:
        tr = hd / 2 if kind == "screw" else pd / 2
        tz = (zb1, zb1 + hk) if kind == "screw" else (zb0, zb1 + ph)
        if hung:
            # r4.4 fix 2b: head under the board / pin hanging through it; the boss + bracket above the board
            tz = (zb0 - hk, zb0) if kind == "screw" else (zb0 - ph, zb1)
            bq = boss_[(x, y)]
            bb = (bq[0], bq[1], bq[2], bq[3], bq[4], bq[5])
            parts = {}
            for f in named:
                b = _box_of(f)
                parts[f[0].replace("board part: ", "")] = min(_circ_box_dist(x, y, tr, tz[0], tz[1], b), _box_box_dist(bb, b))
            pmin = min(parts, key=parts.get)
            fin_d = min(min(_circ_box_dist(x, y, tr, tz[0], tz[1], _box_of(f)), _box_box_dist(bb, _box_of(f))) for f in fins)
            rib_axis = [q[2] - (y + tr) for q in ribs if q[0] < x + tr and q[1] > x - tr]
            so.append(dict(x=x, y=y, kind=kind, top_r=tr, top_z=tz, hung=True, boss=bb, attach=bq[9],
                           rail_top=_circ_rect_dist(x, y, tr, *rail), rail_standoff=_rect_rect_dist(bb[:4], rail),
                           rib_top=min(_circ_rect_dist(x, y, tr, *q) for q in ribs), rib_top_axis=min(rib_axis) if rib_axis else None,
                           rib_standoff=min(_rect_rect_dist(bb[:4], q) for q in ribs),
                           in_board=min(x - tr - bx0, bx1 - (x + tr), y - tr - by0, by1 - (y + tr)),
                           standoff_past_board=max(bx0 - bb[0], bb[1] - bx1, by0 - bb[2], bb[3] - by1, 0.0),
                           part_min=(parts[pmin], pmin), fin=fin_d,
                           hatch=min(x - tr - P["board_hatch"][0], P["board_hatch"][1] - (x + tr), y - tr - P["board_hatch"][2], P["board_hatch"][3] - (y + tr)),
                           edge_ring=(min(x - bx0, bx1 - x, y - by0, by1 - y) - 1.6) if kind == "screw" else None))
            continue
        rib_axis = [q[2] - (y + tr) for q in ribs if q[0] < x + tr and q[1] > x - tr]
        parts = {}
        for f in named:
            b = _box_of(f)
            d = min(_circ_box_dist(x, y, tr, tz[0], tz[1], b), _circ_box_dist(x, y, rs, zf, zb0, b))
            parts[f[0].replace("board part: ", "")] = d
        pmin = min(parts, key=parts.get)
        fin_d = min(min(_circ_box_dist(x, y, tr, tz[0], tz[1], _box_of(f)), _circ_box_dist(x, y, rs, zf, zb0, _box_of(f))) for f in fins)
        so.append(dict(x=x, y=y, kind=kind, top_r=tr, top_z=tz,
                       rail_top=_circ_rect_dist(x, y, tr, *rail), rail_standoff=_circ_rect_dist(x, y, rs, *rail),
                       rib_top=min(_circ_rect_dist(x, y, tr, *q) for q in ribs), rib_top_axis=min(rib_axis) if rib_axis else None,
                       rib_standoff=min(_circ_rect_dist(x, y, rs, *q) for q in ribs),
                       in_board=min(x - tr - bx0, bx1 - (x + tr), y - tr - by0, by1 - (y + tr)),
                       standoff_past_board=max(bx0 - (x - rs), (x + rs) - bx1, by0 - (y - rs), (y + rs) - by1, 0.0),
                       part_min=(parts[pmin], pmin), fin=fin_d,
                       edge_ring=(min(x - bx0, bx1 - x, y - by0, by1 - y) - 1.6) if kind == "screw" else None))   # board left around the D3.2 screw hole
    out["standoffs"] = so
    out["screw"] = dict(length=hl, stack=(zb1 - zb0, zb0 - zf, zf - P["standoff_bore"][1]), tip_z=zb1 - hl,
                        bore_below_tip=(zb1 - hl) - P["standoff_bore"][1], floor_under_bore=P["standoff_bore"][1] - P["z_floor"][0],
                        engage=zb0 - (zb1 - hl))
    if P.get("board_mount") == "hung":
        # r4.4 fix 2b: M3x6 from below: head under the board, board 1.6, then into the hung boss's D2.5 blind bore (top board_boss[1])
        tip_ = zb0 + hl
        out["screw"] = dict(length=hl, stack=(zb1 - zb0, hl - (zb1 - zb0)), tip_z=tip_, bore_top=P["board_boss"][1], bore_above_tip=P["board_boss"][1] - tip_,
                            cap_over_bore=min(P["board_boss"][0], g["z_shelf"] - 2.0) - P["board_boss"][1], engage=hl - (zb1 - zb0),
                            head_z=(zb0 - P["board_screw_real"][1], zb0), head_env_z=(zb0 - hk, zb0), below_hatch=zb0 - hk - P["z_floor"][0], mount="hung")
        out["pins"] = dict(d=pd, hole=P["board_hole"], play=(P["board_hole"] - pd) / 2, tip_z=zb0 - ph)
    # 2. ribbon: in the lane (centred on SB J201) and under the board (last mm shifted to J301)
    wr = P["ribbon_cores"] * P["ribbon_pitch"]
    xc = P["ribbon_xc"]
    xj = 0.5 * (P["ribbon_pads"][0] + P["ribbon_pads"][1])
    lx0, lx1 = P["ribbon_x"]
    ux0, ux1 = ribbon_x_under_board(P)
    rb = [f for f in named if "ribbon under the board" in f[0]][0]
    rbb = _box_of(rb)
    so_rb = min(_circ_box_dist(x, y, rs, zf, zb0, rbb) for x, y, k in P["board_standoffs"])
    if P.get("board_mount") == "hung":
        so_rb = min(_circ_box_dist(x, y, (hd if k == "screw" else pd) / 2, zb0 - (hk if k == "screw" else ph), zb0, rbb) for x, y, k in P["board_standoffs"])
    fin_rb = min(prism_dist((f[1], f[2]), f[3], (rb[1], rb[2]), rb[3])[0] for f in F if f[0] == "fin" or f[0].startswith("fin keel"))
    fb = [f for f in g["lay"]["fins"] if bx0 < 0.5 * (f[0] + f[1]) < bx1][0]
    kx0, kx1 = fb[0] - P["board_slot_keepout"], fb[1] + P["board_slot_keepout"]
    out["ribbon"] = dict(width=wr, xc=xc, j301_c=xj, shift=xj - xc, lane=(lx0, lx1), lane_margins=(xc - wr / 2 - lx0, lx1 - (xc + wr / 2)),
                         under=(ux0, ux1), under_z=tuple(P["ribbon_under_z"]), under_y=(P["rail_y"][1], P["ribbon_pads"][3] + P["board_pad_r"]),
                         to_standoff=so_rb, to_fin=fin_rb, to_keepout=kx0 - ux1, height_under=zb0 - zf,
                         sb_gap=tuple(P["sb_rib_gap"]), sb_gap_margins=(xc - wr / 2 - P["sb_rib_gap"][0], P["sb_rib_gap"][1] - (xc + wr / 2)),
                         sb_gap_r43=(60.0, 82.0), sb_gap_margins_r43=(xc - wr / 2 - 60.0, 82.0 - (xc + wr / 2)),
                         j201_margins=(P["sb_j201"][0] - P["board_pad_r"] - P["sb_rib_gap"][0], P["sb_rib_gap"][1] - (P["sb_j201"][1] + P["board_pad_r"])))
    # 3. USB plug envelope over its whole y range and the receptacle
    s0, s1 = usb_slot(P)
    ux0_, ux1_ = P["usb_x"]
    uy0, uy1 = P["usb_y"]
    uz0, uz1 = P["usb_z"]
    wo = P["usb_wall_open"]
    rx0, rx1, ry0, ry1, rz0, rz1 = P["usb_rcpt"]
    rib_l = max(q[1] for q in ribs if q[1] <= ux0_)
    rib_r = min(q[0] for q in ribs if q[0] >= ux1_)
    out["usb"] = dict(y=(uy0, uy1), y_r43=(195.5, 220.5), slot=(s0, s1), slot_margins=(ux0_ - s0, s1 - ux1_), slot_y=tuple(P["shelf_y"]),
                      plug_under_shelf_y=(max(uy0, P["shelf_y"][0]), min(uy1, P["shelf_y"][1])),
                      ribs=(rib_l, rib_r), rib_margins=(ux0_ - rib_l, rib_r - ux1_),
                      wall_open=tuple(wo), wall_x_margins=(ux0_ - wo[0], wo[1] - ux1_), wall_z_margin=wo[3] - uz1, wall_y=tuple(P["rear_wall"]),
                      passage=(215.0, 258.0, 22.0), bend=25.0, passage_spare=258.0 - (uy1 + 25.0), passage_top=22.0 - uz1,
                      rcpt=(rx0, rx1, ry0, ry1, rz0, rz1), rcpt_slot_margins=(rx0 - s0, s1 - rx1), rcpt_rib_margins=(rx0 - rib_l, rib_r - rx1),
                      rcpt_strip=P["comp_rear"][1] - rz1, rcpt_past_board=ry1 - by1, rcpt_to_rib_face=P["rib_y0"] - ry1)
    # 4. RP2040-Zero vs the fin foot and the keep-out
    zx0, zx1, zy0, zy1 = P["zero_xy"]
    out["zero"] = dict(x=(zx0, zx1), y=(zy0, zy1), foot_gap=zy0 - P["fin_slot_y"][1], keepout=(kx0, kx1, by0, P["board_slot_y1"] + P["board_slot_keepout"]),
                       overhang=(max(zx0, kx0), min(zx1, kx1), zy0, P["board_slot_y1"] + P["board_slot_keepout"]), pcb_z=tuple(P["zero_z"][:2]),
                       hung_fin_z=P["comp_zmax"] + 1.5, to_hung_fin=P["comp_zmax"] + 1.5 - P["zero_z"][2],
                       lattice_x=[round(zx0 + 1.38 + 2.54 * i, 2) for i in range(7)], rcpt_centre=0.5 * (rx0 + rx1), slot_centre=0.5 * (s0 + s1),
                       mux=tuple(P["mux_xy"]), mux_to_keepout=kx0 - P["mux_xy"][1], j302=tuple(P["ext_pads"]),
                       j302_to_rib=P["rib_y0"] - (P["ext_pads"][2] + P["board_pad_r"]))
    # 5. end parts: sensor board support, rear-rib gap, lead lane, rear-wall notch
    ends = {}
    for side, e in ep.items():
        ed = END_DEF[side]
        sb = ed["sb"]
        Fe = end_fixed_prisms(P, g, e)
        ln0, ln1 = lead_lane(P, sb)
        w_ = sb["cores"] * P["ribbon_pitch"]
        g0, g1 = sb["gap"]
        pr_ = P["board_pad_r"]
        yb = P["sb_rib_rear"][0]
        cross = []
        for xa, ya, xb, yb_ in sb["wires"]:
            xcr = xa + (xb - xa) * (yb - ya) / (yb_ - ya) if yb_ != ya else xa
            cross.append(xcr)
        bar = [f for f in Fe if f[0] == "sensor bar"]
        bar_x = (min(f[1] for f in bar), max(f[2] for f in bar))
        pins = []
        zpin = P["block_step_z"] + P["pin_engage"]
        for nm in e["order"]:
            bx = block_x(P, e["keys"][nm])
            xp = 0.5 * (bx[0] + bx[1])
            if xp + P["pin_d"] / 2 > ln0 and xp - P["pin_d"] / 2 < ln1:
                pins.append((nm, xp, zpin - P["pin_len"] - P["lead_lane_z"][1]))
        tabs = [f for f in Fe if f[0].startswith("black tab base")]
        lead = (sb["lead_xc"] - w_ / 2, sb["lead_xc"] + w_ / 2)
        tab_gap = min((max(f[1] - lead[1], lead[0] - f[2]) for f in tabs), default=None)
        dov = [f for f in Fe if "dovetail" in f[0] and _box_of(f)[3] > 150]
        dov_gap = min((max(f[1] - ln1, ln0 - f[2]) for f in dov), default=None)
        fin_gap = min(max(f0 - ln1, ln0 - f1) for f0, f1 in e["lay"]["fins"])
        post = [f for f in Fe if f[0] == "rod end stop post"]
        post_gap = min(max(f[1] - ln1, ln0 - f[2]) for f in post)
        # r4.4 resume: the whole plan path (fan-in included) vs every fixed prism reaching the cable layer (z <= floor + 1)
        lp_ = lead_path_poly(P, sb)
        path_d = sorted((_poly_rect_dist(lp_, f[1], f[2], min(q[0] for q in f[3]), max(q[0] for q in f[3])), f[0]) for f in Fe
                        if min(q[1] for q in f[3]) <= zf + 1.0 and not f[0].startswith(("floor", "sensor board EL", "sensor board ER")))
        fan_tab = min((d_ for d_, n_ in path_d if n_.startswith("black tab base")), default=None)
        ends[side] = dict(board=sb["board"], bar=bar_x, board_in_bar=(sb["board"][0] - bar_x[0], bar_x[1] - sb["board"][1]),
                          rib_x=sb["rib_x"], gap=sb["gap"], pads=sb["pads"], pad_margins=(sb["pads"][0] - pr_ - g0, g1 - (sb["pads"][1] + pr_)),
                          wire_cross=cross, wire_margins=(min(cross) - g0, g1 - max(cross)),
                          cores=sb["cores"], lead_w=w_, lead_xc=sb["lead_xc"], lead=lead, lane=(ln0, ln1), lane_w=ln1 - ln0, lane_z=tuple(P["lead_lane_z"]),
                          notch_z=tuple(P["lead_notch_z"]), pins_over_lane=pins, tab_gap=tab_gap, dovetail_gap=dov_gap, fin_gap=fin_gap, post_gap=post_gap,
                          fan_y=P["sb_board"][3] + P["lead_fan"], path_min=path_d[0], fan_tab=fan_tab, path_list=path_d[:8])
    out["ends"] = ends
    return out


def print_group(name):
    """r4.2: which separate print / part a fixed prism belongs to (fixed-fit check between groups)."""
    if name.startswith(("pad bar rail",)):
        return "frame"
    if name.startswith(("pad bar", "pad wedge")):
        return "pad bar"
    if name.startswith("up-stop pad"):
        return "pad " + name.split()[-1]
    if name.startswith("cover curtain"):
        return "curtain"
    if name.startswith(("top plate", "fin", "rear wall", "spring groove boss", "rear shelf", "shelf rib", "balance rail", "rod end stop",
                        "cheek", "rear dovetail male", "front dovetail male", "white front rail", "black stop rail", "black tab base", "tab ",
                        "keeper hook", "floor", "control-board stand-off", "control-board locating pin", "sensor board support",
                        "control-board boss", "fin keel", "sensor-bar ledge")):
        return "frame"
    return name


def fixed_fit_check(F, res=0.02, groups=("frame", "pad bar", "curtain"), min_area=0.01):
    """r4.2 (drafter's _chk_ff): interference between separately printed / fitted fixed parts: for every pair of prisms
    from different groups whose x ranges overlap by > 0.05, the (y, z) overlap area on a `res` raster eroded by one pixel
    (edge contact is not interference).  Returns the pairs with area > min_area (mm^2), largest first."""
    from matplotlib.path import Path
    out = []
    items = [(print_group(f[0]), f) for f in F]
    items = [q for q in items if q[0] in groups or q[0].startswith("pad ")]
    for i in range(len(items)):
        ga, a = items[i]
        pa = np.array(a[3])
        for j in range(i + 1, len(items)):
            gb, b = items[j]
            if ga == gb or (ga.startswith("pad ") and gb == "pad bar") or (gb.startswith("pad ") and ga == "pad bar"):
                continue                      # pads are glued to their wedges (designed contact)
            if min(a[2], b[2]) - max(a[1], b[1]) <= 0.05:
                continue
            pb = np.array(b[3])
            y0, y1 = max(pa[:, 0].min(), pb[:, 0].min()), min(pa[:, 0].max(), pb[:, 0].max())
            z0, z1 = max(pa[:, 1].min(), pb[:, 1].min()), min(pa[:, 1].max(), pb[:, 1].max())
            if y1 - y0 < 2 * res or z1 - z0 < 2 * res:
                continue
            ny, nz = int((y1 - y0) / res) + 1, int((z1 - z0) / res) + 1
            yy, zz = np.meshgrid(y0 + (np.arange(ny) + 0.5) * res, z0 + (np.arange(nz) + 0.5) * res, indexing="ij")
            pts = np.c_[yy.ravel(), zz.ravel()]
            m_ = (Path(pa).contains_points(pts) & Path(pb).contains_points(pts)).reshape(ny, nz)
            if m_.shape[0] > 2 and m_.shape[1] > 2:
                m_ = m_[1:-1, 1:-1] & m_[:-2, 1:-1] & m_[2:, 1:-1] & m_[1:-1, :-2] & m_[1:-1, 2:]
            area = float(m_.sum()) * res * res
            if area > min_area:
                ii, jj = np.nonzero(m_)
                out.append(dict(area=area, a=a[0], xa=(a[1], a[2]), b=b[0], xb=(b[1], b[2]),
                                box=(y0 + (ii.min() + 1) * res, y0 + (ii.max() + 2) * res, z0 + (jj.min() + 1) * res, z0 + (jj.max() + 2) * res)))
    out.sort(key=lambda q: -q["area"])
    return out


def pad_bar_fit_gaps(P, g, F):
    """r4.2: clearances of the pad-bar assembly to the frame that are NOT designed contacts: wedges / pads vs the plate's
    rear step face and the rails; the bar's joggle vs the plate's channel end; leaf bump on the lip (contact) and the lip
    overlap under the bar edge."""
    out = {}
    plate = [f for f in F if f[0].startswith("top plate")][0]
    rails = [f for f in F if f[0].startswith("pad bar rail")]
    # the plate's rear step face alone (vertical at plate_step_y, from the rear-zone underside up to the seat)
    ps_ = P.get("plate_step_y", P["pad_bar_y"][1])
    zr_ = min(z for y, z in g["plate_under"] if y > ps_ + 0.25)
    face = rect(ps_, ps_ + 0.01, zr_, g["z_seat"])
    for kind in ("pad wedge", "up-stop pad"):
        best = (1e9, None)
        bst = (1e9, None)
        for f in F:
            if f[0].startswith(kind):
                d = prism_dist((f[1], f[2]), f[3], (plate[1], plate[2]), plate[3])[0]
                if d < best[0]:
                    best = (d, f[0])
                ds_ = prism_dist((f[1], f[2]), f[3], (plate[1], plate[2]), face)[0]
                if ds_ < bst[0]:
                    bst = (ds_, f[0])
                for r_ in rails:
                    if r_[2] < f[1] - 6 or r_[1] > f[2] + 6:
                        continue
                    d = prism_dist((f[1], f[2]), f[3], (r_[1], r_[2]), r_[3])[0]
                    if d < best[0]:
                        best = (d, f[0] + " vs " + r_[0])
        out[kind] = best
        out[kind + " to plate step"] = bst
    yj = g["y_bar_joggle"]
    out["joggle_to_channel_end"] = g["y_bar_step"] - yj
    out["lip_under_bar"] = P["rail_lip"] - P["pad_bar_clear"]
    out["lip_top_to_bar"] = P["bar_leaf_gap"]
    lf_t, lf_w, lf_L, pre = P["bar_leaf"]
    k = E_PETG * lf_w * lf_t ** 3 / (4 * lf_L ** 3)
    out["leaf_k"] = k
    out["leaf_F"] = k * pre
    out["leaf_sigma"] = 3 * E_PETG * lf_t * pre / (2 * lf_L ** 2)
    out["leaf_sigma_max_tol"] = 3 * E_PETG * lf_t * (pre + TOL) / (2 * lf_L ** 2)
    return out


def lever_drop(P, g, name, lay=None, keys=None, fixed=None, actual=False, extra=()):
    """key `name` removed and its lever let go: how far does it fall (front down) and onto what?  (pad bar out,
    neighbours at rest).  r4: no service blocks - this is the lever's resting place while its key is out.
    r4.4: actual=True drops onto the named BRD-01 parts, the stand-off heads / pins and the board itself instead of the
    generic component envelope (z20 limit); `extra` = more fixed prisms (e.g. a part fitted on O1 / O7 only)."""
    keys = g["keys"] if keys is None else keys
    lay = g["lay"] if lay is None else lay
    blk = keys[name]["black"]
    b_rest = g["b_rest_" + ("b" if blk else "w")]
    xl = lay["levers"][name]
    removed = ("up-stop pad", "pad wedge", "pad bar", "cover curtain") + (("board components",) if actual else ())
    obst = [f for f in (fixed_prisms(P, g) if fixed is None else fixed) if not f[0].startswith(removed)] + list(extra)
    order = list(lay["levers"])
    i = order.index(name)
    for j in (i - 1, i + 1):
        if 0 <= j < len(order):
            nm2 = order[j]
            kd2 = keys[nm2]
            yc2 = g["caps"]["black" if kd2["black"] else "white"]
            obst += [(t + " (key %s)" % nm2, x0, x1, poly) for t, x0, x1, poly in key_prisms(P, kd2, yc2, lay["levers"][nm2])]
    lp_ = lever_prisms(P, xl)
    deg = math.degrees(b_rest)
    while deg > -60:
        deg -= 0.25
        b = math.radians(deg)
        best = (9.0, None)
        for t, x0, x1, poly in lp_:
            pg = [rot(p, P["L"], -b) for p in poly]
            for f in obst:
                if f[1] - x1 > 3 or x0 - f[2] > 3 or (t == "hub" and f[0].startswith(("fin", "fin boss"))) or f[0].startswith("fin boss"):
                    continue
                if t.startswith(("hub", "web")) and f[0].startswith("lever rod"):      # r4.4: the rod runs through the hub
                    continue
                d, mode = prism_dist((x0, x1), pg, (f[1], f[2]), f[3])
                if d < best[0]:
                    best = (d, f[0])
        if best[0] <= 0.0:
            A = g["Ab"] if blk else g["Aw"]
            # static force on what it lies on (lever weight + torsion spring), at the lever's front bottom
            front = A.lp((P["y_lever_front"], P["z_sb"] - P["lip"]), b)
            T = A.mL * G * (A.L[0] - A.lp(A.cL, b)[0]) + (A.spring_T(b) if A.spring else 0.0)
            return dict(angle_deg=deg, onto=best[1], drop_deg=math.degrees(b_rest) - deg, F_rest=T / max(1.0, A.L[0] - front[0]))
    return dict(angle_deg=deg, onto=None, drop_deg=math.degrees(b_rest) - deg, F_rest=0.0)


def service_swing(P, g, xl, collars=(0.0, 0.0), fixed=None):
    """largest lever angle (deg) with the curtain and the bay's pad bar (with its pads) out before the lever touches the
    top plate, a fin, a pad-bar rail or the rear wall."""
    fixed = [f for f in (fixed_prisms(P, g) if fixed is None else fixed) if not f[0].startswith(("up-stop pad", "pad wedge", "pad bar ", "pad bar", "cover curtain"))
             or f[0].startswith("pad bar rail")]

    def dmin(b):
        best = 1e9
        for t, x0, x1, poly in lever_prisms(P, xl, collars):
            pg = [rot(p, P["L"], -b) for p in poly]
            for f in fixed:
                if f[1] - x1 > 6 or x0 - f[2] > 6 or (t in ("hub", "web", "hub collar") and f[0].startswith(("fin", "fin boss"))) or f[0].startswith("fin boss"):
                    continue
                if t.startswith(("hub", "web")) and f[0].startswith("lever rod"):      # r4.4: the rod runs through the hub
                    continue
                best = min(best, prism_dist((x0, x1), pg, (f[1], f[2]), f[3])[0])
        return best
    b = math.radians(8.0)
    while dmin(b) > 0.05 and b < math.radians(40):
        b += math.radians(0.25)
    return math.degrees(b)


def pad_bar_slide(P, g, bay_levers, fixed=None, keys=None, lay=None, shims=0, pull_max=None, step=0.5, raise_after=None, caps=None, collars=None,
                  fit_out=None):
    """r4.1 (verifier geometry major 2): the pad bar of one fin bay (bar, grip, its pads and wedges; `shims` PET shims
    0.1 under every pad) pulled straight forward at rail height from 0 to pull_max (its rear end past the plate front
    edge), against the bay's keys and levers at rest and the fixed parts that stay (top plate, rails, fins).
    raise_after = (pull, dz): from that pull on the bar is pressed up by dz against the plate's front channel (its
    front part has left the plate; the rear step then has the channel's 1.5 of headroom).  Returns (min distance, pull, pair)."""
    keys = g["keys"] if keys is None else keys
    lay = g["lay"] if lay is None else lay
    fixed = fixed_prisms(P, g) if fixed is None else fixed
    pull_max = (P["pad_bar_y"][1] - P["ledge_y0"]) if pull_max is None else pull_max
    xs = [lay["levers"][n] for n in bay_levers]
    xa, xb = min(xs) - 8.0, max(xs) + 8.0
    moving, obst = [], []
    for f in fixed:
        if f[2] < xa or f[1] > xb:
            continue
        nm_ = f[0]
        if nm_.startswith(("up-stop pad ", "pad wedge ")):
            if nm_.split()[-1] in bay_levers:
                dz = -0.1 * shims if nm_.startswith("up-stop pad") else 0.0
                moving.append((nm_, f[1], f[2], [(y, z + dz) for y, z in f[3]]))
        elif nm_.startswith("pad bar") and not nm_.startswith("pad bar rail"):
            moving.append((nm_, f[1], f[2], f[3]))
        elif nm_.startswith(("cover curtain", "up-stop pad", "pad wedge")):
            continue
        else:
            obst.append(f)
    collars = g["collars"] if collars is None else collars
    for n in bay_levers:
        kd = keys[n]
        yc = (g["caps"]["black" if kd["black"] else "white"]) if caps is None else caps[n]
        obst += [("key %s %s" % (n, t), x0, x1, poly) for t, x0, x1, poly in key_prisms(P, kd, yc, lay["levers"][n])]
        b = g["b_rest_" + ("b" if kd["black"] else "w")]
        obst += [("lever %s %s" % (n, t), x0, x1, [rot(q, P["L"], -b) for q in poly]) for t, x0, x1, poly in lever_prisms(P, lay["levers"][n], collars[n])]
    best = (1e9, None, None)
    fit = (1e9, None, None)
    pull = 0.0
    # r4.2: once the leaf bumps have passed the lips' front end the bar rests on the lips with its lower part (0.3 lower)
    y_off = P["bar_leaf_y"][0] + P["bar_leaf_bump"] - P.get("rail_lip_y0", P["rail_y0"]) if "bar_leaf_y" in P else 1e9
    while pull <= pull_max + 1e-9:
        dzr = raise_after[1] if (raise_after and pull >= raise_after[0] - 1e-9) else (-P.get("bar_leaf_gap", 0.0) if pull > y_off + 1e-9 else 0.0)
        for mn, mx0, mx1, mp in moving:
            pg = [(y - pull, z + dzr) for y, z in mp]
            for f in obst:
                if f[1] - mx1 > 2 or mx0 - f[2] > 2:
                    continue
                d = prism_dist((mx0, mx1), pg, (f[1], f[2]), f[3])[0]
                if f[0].startswith(("pad bar rail", "top plate")):
                    # r4.2: the bar slides in its rails / against the plate (designed sliding fit): contact (-0.01) is fine,
                    # a real overlap is not - reported as `fit` (the drafter's 1.5 x 1.5 overlap at the channel end)
                    if mn.startswith("pad bar") and d < fit[0]:
                        fit = (d, pull, "%s vs %s" % (mn, f[0]))
                    continue
                if pull > 0 and d < best[0]:
                    best = (d, pull, "%s vs %s" % (mn, f[0]))
        pull += step
    if fit_out is not None:
        fit_out.append(fit)
    return best


def lever_insert(P, g, name, keys_present=(), fixed=None, keys=None, lay=None, collars=None, res=0.25, pitch=(-40.0, 60.0, 1.0)):
    """r4.1 (verifier geometry major 1): can lever `name` be brought from outside (in front of and above the frame) to
    its place on the lever-rod line under the one-piece top plate?  2D (y, z) configuration space (translation +
    pitch), obstacles = every part at rest whose x range overlaps the lever's (keys only if in keys_present; pad
    bars, pads, wedges and curtain not yet fitted; other levers not fitted).  Goal: hub on the rod line (dy 0, dz 0)
    at any pitch between -35 deg and the rest angle.  The torsion-spring long leg is not in the lever outline (it is
    held by a finger, see DESIGN 10)."""
    from matplotlib.path import Path
    from scipy.signal import fftconvolve
    from scipy import ndimage
    keys = g["keys"] if keys is None else keys
    lay = g["lay"] if lay is None else lay
    collars = g["collars"] if collars is None else collars
    fixed = fixed_prisms(P, g) if fixed is None else fixed
    Y0, Y1, Z0, Z1 = 30.0, 216.0, 0.0, 112.0
    ny, nz = int((Y1 - Y0) / res), int((Z1 - Z0) / res)
    yy, zz = np.meshgrid(Y0 + (np.arange(ny) + 0.5) * res, Z0 + (np.arange(nz) + 0.5) * res, indexing="ij")
    pts = np.c_[yy.ravel(), zz.ravel()]

    def raster(polys, grow=0.0):
        msk = np.zeros(ny * nz, bool)
        for poly in polys:
            pa = np.array(poly)
            bb = (pa[:, 0].min() - 1, pa[:, 0].max() + 1, pa[:, 1].min() - 1, pa[:, 1].max() + 1)
            sel = (pts[:, 0] > bb[0]) & (pts[:, 0] < bb[1]) & (pts[:, 1] > bb[2]) & (pts[:, 1] < bb[3])
            if sel.any():
                msk[sel] |= Path(pa).contains_points(pts[sel], radius=1e-9)
        msk = msk.reshape(ny, nz)
        if grow > 0:
            r = max(1, int(round(grow / res)))
            c = np.arange(-r, r + 1)
            st = (c[:, None] ** 2 + c[None, :] ** 2) <= r * r
            msk = ndimage.binary_dilation(msk, st)
        return msk
    xl = lay["levers"][name]
    lp = lever_prisms(P, xl, collars[name]) + [("steel", xl - P["steel_w"] / 2, xl + P["steel_w"] / 2, steel_poly(P))]
    x0 = min(q[1] for q in lp)
    x1 = max(q[2] for q in lp)
    obst = []
    for f in fixed:
        if f[0].startswith(("pad bar", "up-stop pad", "pad wedge", "cover curtain")) and not f[0].startswith("pad bar rail"):
            continue
        if f[0].startswith(("lever rod", "fin boss bore")):      # r4.4: the rod goes in after the levers; bores are holes
            continue
        if f[2] <= x0 or f[1] >= x1:
            continue
        obst.append(f[3])
    for n in keys_present:
        kd = keys[n]
        yc = g["caps"]["black" if kd["black"] else "white"] if n in g["keys"] else 188.0
        for t, a, b, poly in key_prisms(P, kd, yc, lay["levers"][n]):
            if b > x0 and a < x1:
                obst.append(poly)
    O = raster(obst, 0.15).astype(float)
    angs = np.arange(pitch[0], pitch[1] + 1e-9, pitch[2])
    frees = []
    for a in angs:
        polys = [[rot(q, P["L"], -math.radians(a)) for q in poly] for t, _, _, poly in lp]
        Lm = raster(polys)
        idx = np.argwhere(Lm)
        i0, j0 = idx.min(0)
        i1, j1 = idx.max(0)
        K = Lm[i0:i1 + 1, j0:j1 + 1].astype(float)
        C = fftconvolve(O, K[::-1, ::-1], mode="full")
        Kh, Kw = K.shape
        di = np.arange(C.shape[0]) - (Kh - 1) - i0
        dj = np.arange(C.shape[1]) - (Kw - 1) - j0
        si = (di * res >= -110) & (di * res <= 5)
        sj = (dj * res >= -12) & (dj * res <= 45)
        frees.append(C[np.ix_(si, sj)] < 0.5)
        dy_ax, dz_ax = di[si] * res, dj[sj] * res
    F = np.stack(frees, 0)
    lab, _ = ndimage.label(F, structure=ndimage.generate_binary_structure(3, 1))
    start = set(np.unique(lab[:, 0, -1])) - {0}
    blk = keys[name]["black"]
    b_rest = math.degrees(g["b_rest_" + ("b" if blk else "w")])
    j0_ = int(np.argmin(abs(dy_ax)))
    k0_ = int(np.argmin(abs(dz_ax)))
    goal = set()
    ok_angles = []
    for ia, a in enumerate(angs):
        if -35.0 <= a <= b_rest + 0.5 and lab[ia, j0_, k0_]:
            goal.add(lab[ia, j0_, k0_])
            if lab[ia, j0_, k0_] in start:
                ok_angles.append(float(a))
    return dict(ok=bool(start & goal), pitches=(min(ok_angles), max(ok_angles)) if ok_angles else None, x=(x0, x1))


# ============================================================================ end parts (same mechanism)
def end_part_keys(P):
    s = (P["head_gap"] - 1.0) / 2
    st = (P["tail_gap_ww"] - 1.0) / 2
    bw = P["black_w"]
    L = {"A0": dict(name="A0", black=False, head=(0.5 + s, 23.0 - s), tail=(0.5 + st, 20.073), xc=10.287, guide_c=11.75),
         "A#0": dict(name="A#0", black=True, head=(26.927 - bw / 2, 26.927 + bw / 2), tail=(26.927 - bw / 2, 26.927 + bw / 2), xc=26.927,
                     top=(26.927 - P["black_top_w"] / 2, 26.927 + P["black_top_w"] / 2), guide_c=26.927),
         "B0": dict(name="B0", black=False, head=(24.0 + s, 46.5 - s), tail=(33.781, 46.5 - st), xc=40.141, guide_c=35.25)}
    R = {"C8": dict(name="C8", black=False, head=(0.5 + s, 23.0 - s), tail=(0.5 + st, 23.0 - st), xc=11.75, guide_c=11.75,
                    block=(4.3, 19.2))}
    return L, R


END_DEF = dict(
    # side: order, fins (cheek-side fin, seam fin), key-area x range, cheek (x0, x1), seam side, neighbour module keys
    # across the seam and their x shift (module-local x = part-local x - shift)
    # r4.4 (circuit cross-check 4): 'sb' = the end part's sensor board (circuit BRD-02: inside the r4.2 sensor bar), its
    # v3-style support (post x0.5-6.0 + front / rear ribs over rib_x), the rear-rib gap under the lead pads (circuit: EL
    # x15-38, the B0 wire enters the rib band at x36; ER x6-16), the lead pads (J401 / J411 on the underside, y74.62)
    # and the lead: `cores` 1.27 strands centred on lead_xc through a lane under the balance rail and a rear-wall notch.
    # EL lead_xc 18.0: the 5-core lead passes the A#0 black tab base (x22.93-30.93, y79-93, on the floor) on its left
    # with 1.75; ER lead_xc = J411 centre 10.79 (C8's balance pin sits 1.3 above the lane top as the module's E / F pins)
    left=dict(order=["A0", "A#0", "B0"], fins=((-1.8, -0.2), (45.2, 46.8)), x=(0.0, 47.0), cheek=(-16.0, -0.68), seam_fin=1,
              neighbour=("C", "C#", "D"), dx=47.0,
              sb=dict(board=(1.0, 46.5), rib_x=(6.0, 45.0), gap=(15.0, 38.0), pads=(18.41, 28.57), n_pads=5, cores=5, lead_xc=18.0,
                      wires=((13.33, 72.08, 20.95, 74.62), (31.11, 72.08, 23.49, 74.62), (43.81, 72.08, 26.03, 74.62), (18.41, 67.0, 18.41, 74.62), (28.57, 64.46, 28.57, 74.62)))),
    right=dict(order=["C8"], fins=((0.2, 1.8), (23.5, 25.1)), x=(0.0, 23.5), cheek=(24.18, 39.5), seam_fin=0,
               neighbour=("A", "A#", "B"), dx=-164.5,
               sb=dict(board=(1.0, 23.0), rib_x=(6.0, 21.5), gap=(6.0, 16.0), pads=(8.25, 13.33), n_pads=3, cores=3, lead_xc=10.79,
                       wires=((15.87, 72.08, 10.79, 74.62), (8.25, 67.0, 8.25, 74.62), (13.33, 64.46, 13.33, 74.62)))),
)


def fh(v, n=2):
    """r4.4: format a length half away from zero at n decimals on its shortest decimal repr (13.525 -> '13.53'; '%.2f'
    gives '13.52' from the binary value) - the rule of export_geo.hu, for the new circuit-interface strings."""
    from decimal import Decimal, ROUND_HALF_UP
    d6 = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-6), rounding=ROUND_HALF_UP)
    return str(d6.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def lead_path_poly(P, sb):
    """r4.4 resume: plan path of an end part's lead (floor, z5 up): from the pad row (pads +- pad radius, underside,
    inside the rear-rib gap) fanning in to the lead width within lead_fan behind the board's rear edge, then straight
    back through the rail lane and the rear-wall notch to the rear face y212."""
    w = sb["cores"] * P["ribbon_pitch"]
    l0, l1 = sb["lead_xc"] - w / 2, sb["lead_xc"] + w / 2
    pr = P["board_pad_r"]
    py = P["sb_j201"][3]
    yf = P["sb_board"][3] + P["lead_fan"]
    p0, p1 = sb["pads"][0] - pr, sb["pads"][1] + pr
    return [(p0, py - pr), (p1, py - pr), (p1, py + pr), (l1, yf), (l1, P["rear_wall"][1]), (l0, P["rear_wall"][1]), (l0, yf), (p0, py + pr)]


def _poly_rect_dist(poly, x0, x1, y0, y1):
    """plan distance between a closed polygon and an axis-parallel rectangle (0 when they overlap)."""
    from matplotlib.path import Path
    pts = list(poly)
    rc = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if Path(pts).contains_points([(0.5 * (x0 + x1), 0.5 * (y0 + y1))])[0] or any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pts):
        return 0.0
    def sd(p, a, b):
        ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)
    d = 1e9
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        for c in rc:
            d = min(d, sd(c, a, b))
    for i in range(4):
        a, b = rc[i], rc[(i + 1) % 4]
        for p in pts:
            d = min(d, sd(p, a, b))
    return d


def lead_lane(P, sb):
    """r4.4: x range of an end part's lead lane under the balance rail / rear-wall notch (lead width + lead_margin)."""
    w = sb["cores"] * P["ribbon_pitch"]
    return sb["lead_xc"] - w / 2 - P["lead_margin"], sb["lead_xc"] + w / 2 + P["lead_margin"]


def sb_support_prisms(P, board_x, rib_x, gap, tag=""):
    """r4.4 (circuit cross-check 4-5): the sensor board (v3 6-row stripboard) and its v3 support printed with the frame:
    post (P111) and front / rear ribs (P113) up to the board underside; the rear rib is open over `gap`."""
    bx0, bx1 = board_x
    _, _, by0, by1, bz0, bz1 = P["sb_board"]
    px0, px1, py0, py1 = P["sb_post"]
    fz = P["z_floor"][1]
    F = [("sensor board%s (v3 6-row stripboard 1.6, under the sensor bar)" % tag, bx0, bx1, rect(by0, by1, bz0, bz1)),
         ("sensor board support post (v3 P111, M3x10 of bar + board into it)", px0, px1, rect(py0, py1, fz, bz0)),
         ("sensor board support rib front (v3 P113)", rib_x[0], rib_x[1], rect(P["sb_rib_front"][0], P["sb_rib_front"][1], fz, bz0))]
    for a, b in ((rib_x[0], gap[0]), (gap[1], rib_x[1])):
        if b - a > 1e-6:
            F.append(("sensor board support rib rear (v3 P113; open x%.1f-%.1f)" % gap, a, b, rect(P["sb_rib_rear"][0], P["sb_rib_rear"][1], fz, bz0)))
    return F


def sb_ledge_prisms(P):
    """r4.5 circuit 2nd cross-check (item 8): the v3 P112 right ledge printed with the module frame - two pieces (front /
    rear of the B sensor leads), each an inverted L: lip over the sensor bar's right end (underside = white bar top, the
    bar + board slide under it from the left before the two left M3x10) and its post from the floor beside the bar end."""
    lx0, lx1, px1, zl0, zl1 = P["sb_ledge"]
    fz = P["z_floor"][1]
    F = []
    for tag, (y0, y1) in zip(("front", "rear"), P["sb_ledge_y"]):
        F.append(("sensor-bar ledge lip %s (frame, v3 P112; underside z%.1f = bar top)" % (tag, zl0), lx0, lx1, rect(y0, y1, zl0, zl1)))
        F.append(("sensor-bar ledge post %s (frame, v3 P112)" % tag, lx1, px1, rect(y0, y1, fz, zl1)))
    return F


def end_parts(P, g):
    """left end part (A0, A#0, B0; keys x0-47, cheek x-16..-0.68) and right end part (C8; key x0.68-22.82, cheek
    24.18-39.5, local x).  Same section as the modules (heights, top plate, one pad bar, pads, front parts), own lever
    layout / capstans; bosses on the seam fins one-sided (r3 major #3), seam fins notched over the dovetail."""
    Lk, Rk = end_part_keys(P)
    out = {}
    for side, keys in (("left", Lk), ("right", Rk)):
        ed = END_DEF[side]
        order = ed["order"]
        lay = solve_lever_layout(P, keys, order, ed["fins"], [], [], [])
        caps, acts, dw, pads = {}, {}, {}, {}
        for nm in order:
            yc = solve_cap_y(P, keys[nm], lay["levers"][nm])
            caps[nm] = yc
            A = Action(P, keys[nm], yc, lay["levers"][nm])
            acts[nm] = A
            s = A.statics(1e-4)
            st, top, fr, w = held_bottom(A, g["z_shelf"], 1.0)
            pt = g["pad_b"] if keys[nm]["black"] else g["pad_w"]
            # this key's steel top vs its colour's pad face at its own settled bottom (+ = pad above = key first)
            tab = PadTable(A, st[1], 0.0, e_eff=pt.e_eff)
            face_off = ((tab.ref[0] - pt.ref[0]) * pt.n[0] + (tab.ref[1] - pt.ref[1]) * pt.n[1])
            gd_ = P["gap_us_b"] if keys[nm]["black"] else P["gap_us_w"]
            dw[nm] = dict(DW=s["DW"], UW=s["UW"], meff=s["meff"], key_g=petg_mass(A.key), y_cap=yc, held_b=st[1],
                          held_cap_top=top, gap_to_face=-face_off, gap_design=gd_)
            # r4.2 (drafter): the part's own pad face = the one its dynamics use (own settled bottom, design gap); its
            # wedge is printed to it (DESIGN 14 thickness offsets are the normal shift of this face vs the module face)
            pads[nm] = PadFace(A, st[1], gd_)
            wd_ = [g["z_seat"] - P["pad_bar_t"] - (pad_face_z(pads[nm], y) + P["pad_h"] * pads[nm].n[1]) for y in P["pad_y"]]
            wm_ = [g["z_seat"] - P["pad_bar_t"] - (pad_face_z(pt, y) + P["pad_h"] * pt.n[1]) for y in P["pad_y"]]
            dw[nm].update(wedge=tuple(wd_), wedge_module=tuple(wm_), wedge_delta=(wd_[0] - wm_[0], wd_[1] - wm_[1]),
                          face_tilt_deg=math.degrees(st[1]), face_tilt_module_deg=math.degrees(pt.b_face if hasattr(pt, "b_face") else st[1]))
        out[side] = dict(keys=keys, order=order, lay=lay, caps=caps, stat=dw, acts=acts, cheek=ed["cheek"], x=ed["x"],
                         collars=hub_collars(lay, P), side=side, pads=pads)
    return out


def end_fixed_prisms(P, g, e):
    """fixed parts of an end part (part-local x): module sections clipped to the part, balance rail with its blocks,
    per-key front parts and balance pins, fins (seam fin notched over the dovetail zone, extension inset) with one-sided
    bosses, the top plate over the part and its cheek, one pad bar with the part's pads, the curtain, the cheek, and the
    seam dovetail of the part (left: male root/tongue, right: female groove)."""
    side = e["side"]
    x0e, x1e = e["x"]
    c0, c1 = e["cheek"]
    keep = ("floor", "white front rail", "white front felt", "rear shelf", "rear wall")
    sb = END_DEF[side]["sb"]
    ln0, ln1 = lead_lane(P, sb)
    nz0, nz1 = P["lead_notch_z"]
    F = []
    # r4.5 circuit 2nd cross-check (item 11): the floor comes from the module WITHOUT its control-board hatch (the module-x
    # hatch cut x46.25-118.25 left a floor gap x46.25-46.8 x y144.5-196.5 in the left end part); the hatch is a module feature
    for f in fixed_prisms(dict(P, board_hatch=None), g):
        if f[0].startswith(keep):
            a, b = max(f[1], x0e + 0.2), min(f[2], x1e - 0.2)
            if b > a:
                if f[0] == "rear wall" and a < ln0 and ln1 < b:
                    # r4.4 (circuit cross-check 4): notch z5-12 in the rear wall for the lead (same x as the rail lane)
                    zt_ = max(q[1] for q in f[3])
                    F.append((f[0], a, ln0, f[3]))
                    F.append(("rear wall (over the lead notch z%.0f-%.0f)" % (nz0, nz1), ln0, ln1, rect(P["rear_wall"][0], P["rear_wall"][1], nz1, zt_)))
                    F.append((f[0], ln1, b, f[3]))
                    continue
                F.append((f[0], a, b, f[3]))
    blocks = [block_x(P, e["keys"][nm]) for nm in e["order"]]
    F += rail_prisms(P, g, blocks, (x0e + 0.3, x1e - 0.3), (x0e + 1.55, x1e - 1.55), lane=(ln0, ln1),      # r4.4: lead lane z5-10
                     pockets=rail_pockets(P, g, e["keys"], e["order"]))
    F += sb_support_prisms(P, sb["board"], sb["rib_x"], sb["gap"], " EL" if side == "left" else " ER")      # r4.4: v3 P111 / P113
    F += front_parts(P, g, e["keys"], e["order"])
    zpin = P["block_step_z"] + P["pin_engage"]
    for nm in e["order"]:
        bx0, bx1 = block_x(P, e["keys"][nm])
        xp = (bx0 + bx1) / 2
        F.append(("balance pin D2 " + nm, xp - 1.0, xp + 1.0, rect(P["pin_y"] - 1.0, P["pin_y"] + 1.0, zpin - P["pin_len"], zpin)))
    bl = fin_boss_len(e["lay"], P)
    ins = P["fin_ext_inset"]
    for i, (f0, f1) in enumerate(e["lay"]["fins"]):
        main, ext = fin_poly(P, g, False, False, True)
        F.append(("fin", f0, f1, main))
        F.append(("fin", f0 + ins, f1 - ins, ext))
        rl, rr_ = bl[i]
        F.append(("fin boss", f0 - rl, f1 + rr_, circle(P["L"], P["boss_R"], 16)))
    # r4.4: lever rod, fin-boss bores and the rod-end plug (plug at the seam fin: the cheek-side fin is blind)
    F += lever_rod_prisms(P, e["lay"]["fins"], bl, plug_side="right" if side == "left" else "left")
    xa, xb = min(x0e, c0) + 0.2, max(x1e, c1) - 0.2
    F += top_parts(P, g, e["lay"]["fins"], e["lay"]["levers"], e["keys"], (xa, xb), bays_=bays(e["lay"]["fins"]), pads=e.get("pads"))
    # r4.2 (drafter): the end parts' own sensor bars (v3 bar section, low top +-bar_low_half at the black key)
    xs_ = [x0e + 0.5]
    for nm in e["order"]:
        if e["keys"][nm]["black"]:
            xs_ += [e["keys"][nm]["xc"] - P["bar_low_half"], e["keys"][nm]["xc"] + P["bar_low_half"]]
    xs_.append(x1e - 0.5)
    for i in range(len(xs_) - 1):
        F.append(("sensor bar", xs_[i], xs_[i + 1], rect(P["bar_y"][0], P["bar_y"][1], 8.6, P["bar_top_b"] if i % 2 == 1 else P["bar_top_w"])))
    F += curtain_parts(P, g, x0e + 0.2, x1e - 0.2, [e["keys"][n]["xc"] for n in e["order"] if e["keys"][n]["black"]])
    F += spring_bosses(P, g, e["lay"]["levers"])
    zt = g["z_top"]
    F.append(("cheek", c0, c1, rect(0.0, P["frame_depth"], P["z_floor"][0], zt)))
    if side == "left":
        F.append(("rear dovetail male root", x1e - 4.0, x1e, rect(198.0, 207.0, 3.0, 17.0)))
        F.append(("front dovetail male root", x1e - 4.0, x1e, rect(6.5, 15.5, 3.0, 8.5)))
    else:
        F.append(("rear dovetail (female groove, neighbour male inside)", x0e, x0e + 4.0, rect(198.0, 207.0, 3.0, 17.3)))
        F.append(("front dovetail (female)", x0e, x0e + 4.0, rect(6.5, 15.5, 3.0, 8.8)))
    return F


def end_part_sweep(P, g, e, pk_w, pk_b, pl_w, pl_b, pk_mod=None, pl_mod=None):
    """clearance sweep of an end part: its keys and levers against each other, the cheek and all its fixed parts, AND
    (r3 major #3) the neighbouring module's three keys / levers and fixed parts across the seam."""
    bodies = []
    poses_k, poses_l = {}, {}
    flo_e, pg_e = lever_float(e["lay"], P, e["collars"])          # r4.4 fix 2
    flo_m, _ = lever_float(g["lay"], P, g["collars"])
    for nm in e["order"]:
        kd = e["keys"][nm]
        yc = e["caps"][nm]
        xl = e["lay"]["levers"][nm]
        bodies.append((("key", nm, 0), "key", nm, 0.0, yaw_inflate(P, key_prisms(P, kd, yc, xl), "key", kd["black"])))
        bodies.append((("lever", nm, 0), "lever", nm, 0.0, yaw_inflate(P, lever_prisms(P, xl, e["collars"][nm]), "lever", kd["black"], flo_e[nm])))
        poses_k[nm] = pk_b if kd["black"] else pk_w
        poses_l[nm] = pl_b if kd["black"] else pl_w
    ed = END_DEF[e["side"]]
    dx = ed["dx"]
    keys, lay = g["keys"], g["lay"]
    for nm in ed["neighbour"]:
        kd = keys[nm]
        yc = g["caps"]["black" if kd["black"] else "white"]
        bodies.append((("key", nm, dx), "key", nm, dx, yaw_inflate(P, key_prisms(P, kd, yc, lay["levers"][nm]), "key", kd["black"])))
        bodies.append((("lever", nm, dx), "lever", nm, dx, yaw_inflate(P, lever_prisms(P, lay["levers"][nm], g["collars"][nm]), "lever", kd["black"], flo_m[nm])))
        poses_k[nm] = (pk_mod or {}).get(nm, pk_b if kd["black"] else pk_w)
        poses_l[nm] = (pl_mod or {}).get(nm, pl_b if kd["black"] else pl_w)
    fixed = end_fixed_prisms(P, g, e)
    # the neighbour module's fixed parts near the seam (shifted into part-local x)
    for f in fixed_prisms(P, g):
        a, b = f[1] + dx, f[2] + dx
        if b > min(e["x"]) - 8.0 and a < max(e["x"]) + 8.0:
            fixed.append((f[0] + " (module)", a, b, f[3]))
    # neighbour-module bodies are compared only with the part's bodies and fixed parts (the module's own sweep covers the rest)
    return clearance_sweep(P, g, poses_k, poses_l, extra_moving=dict(bodies=bodies, fixed=fixed, pair_gap=pg_e, xlev=dict(e["lay"]["levers"])))


def seam_fixed_check(P, g, e):
    """fixed-to-fixed across the seam: the end part's fixed prisms vs the neighbouring module's.  Seam faces (fins, top
    plates, curtains, pad-bar rails: 0.2 inset on each side = the 0.4 seam of every module joint) must not overlap; every
    other pair must keep 1.3; the dovetail pair is the designed sliding fit (reported apart)."""
    ed = END_DEF[e["side"]]
    dx = ed["dx"]
    A_ = end_fixed_prisms(P, g, e)
    B_ = [(f[0], f[1] + dx, f[2] + dx, f[3]) for f in fixed_prisms(P, g)]
    B_ = [f for f in B_ if f[2] > min(e["x"]) - 8.0 and f[1] < max(e["x"]) + 8.0]
    # v3 full-width parts that abut at every seam (floors, front rail and felt, shelf, rear wall, balance rail, sensor bar)
    skip = ("floor", "white front rail", "white front felt", "rear shelf", "rear wall", "balance rail", "rod end stop post", "key rod", "sensor bar",
            "lever rod D4", "sensor board")      # r4.4: v3 sensor boards / supports abut every seam like the bar
    face = ("fin", "top plate", "cover curtain", "pad bar rail", "lever rod end plug")     # r4.4: the plug is flush with its fin face
    best = (1e9, None)
    seam = (1e9, None)
    dove = (1e9, None)
    for a in A_:
        for b in B_:
            if b[1] - a[2] > 6 or a[1] - b[2] > 6:
                continue
            if a[0].startswith(skip) or b[0].startswith(skip):
                continue
            d, mode = prism_dist((a[1], a[2]), a[3], (b[1], b[2]), b[3])
            lab = "%s vs %s (module)" % (a[0], b[0])
            if "dovetail" in a[0] and "dovetail" in b[0]:
                if d < dove[0]:
                    dove = (d, lab)
                continue
            if a[0].startswith(face) and b[0].startswith(face):
                if d < seam[0]:
                    seam = (d, lab)
                continue
            if d < best[0]:
                best = (d, lab)
    return dict(min=best, seam=seam, dovetail=dove)
# ============================================================================ tilt retention (90 deg)
def tilt_check(g, A, angle_deg, mu_lip=None, t_tilt=400.0):
    """module tilted about x by angle (+ = front edge down / rear up).  Gravity in the module frame is
    rotated; the key must stay on its rod (notch lift < lip clearance) and the keeper must hold.  Then the
    module is laid flat again: does the key re-seat by itself (lip friction mu_lip included)?"""
    t = math.radians(angle_deg)
    gvec = (-math.sin(t), -math.cos(t))          # +angle: front down -> gravity has a -y component
    D = dyn_for(g, A, gvec=gvec, mu_lip=mu_lip)
    ev = D.run(t_tilt)
    D0 = dyn_for(g, A, mu_lip=mu_lip)
    ev0 = D0.run(400.0, state=ev["state"])
    th0 = ev0["state"][0]
    N0 = key_point_world(A, ev0["state"], A.K)
    off0 = (A.K[0] - N0[0], A.K[1] - N0[1])
    reseat_lift = (D.Rn - D.r_rod) - (off0[0] * (-math.sin(th0)) + off0[1] * math.cos(th0))
    reseat_front = key_point_world(A, ev0["state"], A.front)[1] - key_point_world(A, D0.run(200.0)["state"], A.front)[1]
    reseat_y = -(off0[0] * math.cos(th0) + off0[1] * math.sin(th0))
    th, b, c, vc, w, wb = ev["state"]
    Nw = key_point_world(A, ev["state"], A.K)
    off = (A.K[0] - Nw[0], A.K[1] - Nw[1])
    upk = (-math.sin(th), math.cos(th))
    along = off[0] * upk[0] + off[1] * upk[1]
    lift = (D.Rn - D.r_rod) - along
    escape_margin = (A.P["rod_k"] / 2 - A.P["block_lift"]) - lift
    rightk = (math.cos(th), math.sin(th))
    y_off = -(off[0] * rightk[0] + off[1] * rightk[1])
    return dict(angle=angle_deg, notch_lift=lift, escape_margin=escape_margin, notch_y_offset=y_off, keeper_force=ev["keep_peak"],
                keeper_gap_min=ev["keep_gap_min"], key_angle_deg=math.degrees(th), lever_angle_deg=math.degrees(b),
                upstop_force=ev["up_peak"], reseat_lift=reseat_lift, reseat_front_dz=reseat_front, reseat_y=reseat_y,
                mu_lip=D.mu_lip)

def roll_check(P, g, hist_w=None, hist_b=None):
    """key roll about its long axis: the capstan force acts at the lever x, which is offset from the balance-block
    centre (beam jog); the rod reaction can move to the block edge (restoring = R_rod x half block width).  Ratio
    restoring / overturning at rest (statics) and over a held 2.0 m/s stroke (4-DOF history of the representative
    white / black key, scaled to each key's offset); where it drops below 1 the guide tab takes the rest as a couple
    over the rib height."""
    keys, lay = g["keys"], g["lay"]
    out = {}
    rib_h = P["key_top"] - P["skin_w"] - P["key_bot"]
    # r4.3: the rest felt of F / F# lands only beside the USB slot -> the shelf reaction moves off the lever line
    land = rest_landing(P, g) if "usb_clear" in P else {}
    for nm in ORDER:
        kd = keys[nm]
        A = g["Ab"] if kd["black"] else g["Aw"]
        bx = block_x(P, kd)
        xb = (bx[0] + bx[1]) / 2
        hw = (bx[1] - bx[0]) / 2
        d = abs(lay["levers"][nm] - xb)
        dN = lay["levers"][nm] - xb                              # capstan (down on the key) offset
        dR = dN + (land[nm]["dx"] if nm in land else 0.0)         # r4.3: rest reaction (up) offset
        s = A.statics(1e-4)
        yr = sum(P["rest_pad_y"]) / 2
        Mg = A.mk * G * (A.K[0] - A.ck[0])
        Rs = (s["N"] * (A.y_cap - A.K[0]) - Mg) / (yr - A.K[0])
        Rk = A.mk * G + s["N"] - Rs
        over_rest = abs(Rs * dR - s["N"] * dN)
        r_rest = (Rk * hw / over_rest) if over_rest > 1e-9 else 99.0
        r_dyn = 99.0
        tab_N = 0.0
        h = hist_b if kd["black"] else hist_w
        if h:
            for rec in h:
                Nc, Frod, fre = rec[4], rec[6], rec[7]
                ov = abs(fre * dR - Nc * dN)
                if ov > 1e-6 and Nc > 0.2:
                    r_dyn = min(r_dyn, Frod * hw / ov)
                    tab_N = max(tab_N, max(0.0, ov - Frod * hw) / rib_h)
        out[nm] = dict(offset=d, half_block=hw, ratio_rest=min(r_rest, 99.0), ratio_stroke=min(r_dyn, 99.0), tab_N=tab_N,
                       rest_dx=dR - dN, rest_frac=land[nm]["frac"] if nm in land else 1.0)
    return out


# r4.5 fix 2: the insertion slot runs along the captured short leg (its direction follows the groove geometry)
P["spring_slot"] = (round(spring_notch_geo(P)["slot_deg"], 2), P["spring_slot"][1], P["spring_slot"][2])
