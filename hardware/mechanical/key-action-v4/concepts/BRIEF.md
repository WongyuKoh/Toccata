# Toccata v4 key action — design brief (2026-09-27)

Repo root: /Users/kwg/Desktop/mydrive/project/Toccata
Scratch root: /private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/2f19e142-4ac2-4c90-bd1e-b3b469f97487/scratchpad/v4

## 1. What the user asked (verbatim, Korean)
"지금 구조는 아무리 봐도 중력 때문에 처음부터 구부러질 거 같아. 기존 디지털 피아노나 그랜드 피아노 구조를 보면 시소 작용을 이용해. 그리고 그거 덕분에 다시 원래상태로 돌아올 수도 있고, 상태도 오래 유지되는거거든? 우리도 시소 시스템을 적용하면서 기존 구조에서 뺄 수 있는 부분을 빼고 사이즈를 축소화해서 디자인을 하면 좋을 거 같아. 아니면 https://darkpgmr.tistory.com/187 이 링크에서 gif로 있는 디지털 피아노 건반 내부 구조를 참고해도 좋을 거 같아. 해당 구조는 시소는 아닌데, 끝 부분에 축으로 연결되어있고, 무게추를 이용해서 누르면 다시 돌아오게 하는 구조거든? 이런 구조를 참고해서 다시 건반 구조를 만들어줄래"
Follow-up: "필요하다면 스프링을 사용해도 좋아" (metal springs are allowed if needed).

Meaning: replace the v3 leaf-flexure key (a PETG leaf that is both pivot and return spring, permanently preloaded ~6 MPa → creep/sag is the #1 risk) with a structure that returns by gravity (seesaw / weighted hammer) and keeps its state for years. Strip everything an acoustic or digital action has that we do not need, and make it as small as possible.

## 2. Reference mechanism the user pointed to (Casio Privia PX-720, from the blog)
Images (read them): scratchpad/v4/../ref/gif_sheet.png (4 frames of the GIF), ref/btry6Foox7F.png (labelled figure), ref/gif_f00.png … gif_f28.png (all frames).
- White plastic key pivots on an axis at its REAR end (far from the player).
- A hook/lug hanging down from the key (about 2/3 of the way to the front) engages the front end of a separate orange hammer lever that sits under the key.
- The hammer pivots in the middle of the keybed; its long rear arm carries a steel weight (grey block) near the rear, low down.
- Pressing the key pushes the hammer front down → the hammer rotates → the rear weight rises and hits an upper sponge stop. Releasing → the weight falls and pushes the key back up. Sponge also under the weight (rest stop).
- Rubber-dome switches (red) sit under the hammer front.
- Blog's noise findings: (a) "딱" on press = key hitting the down-stop whose cushioning grease/felt wore off; (b) "덜걱" on release = play (clearance) in the key↔hammer coupling slot: the weight bounces on its bottom sponge and the lug rattles in the slot. → our coupling must have minimal play and damping, and every stop must be felt/EVA.
This is the same family as Yamaha GHS/GHC and the repo's build-set method D.

## 3. Prior art already in the repo (do not copy blindly — downsize/simplify)
File: docs/report/toccata-build-set/index.html (Korean report) and its generator docs/report/toccata-build-set/src/model.py (method_C, _method_D, method_D with all geometry and calcs), src/calc.py.
- C 밸런스 핀 시소: 2-piece 372 mm key, Ø4 balance pin at y212, steel flat-bar counterweight (9×25, 85 g white / 65 g black) at the tail y319–367, felt punching. DW ≈ 50 g, UW ≈ 38 g, effective mass at front 47 g, case depth +124 mm (558), 6.8 kg steel, 6.1 kg filament/245 h. Gravity return, no spring.
- D 해머 액션 (GHS-like): key pivots on rear shaft y238; separate hammer lever with Ø3 shaft at y95, key presses hammer at y66; angular-velocity ratio 5.9 → 34 g weight feels like 128 g at the key front. Key top raised to z58 (vs v3 z43.5), 7.6 kg filament / 304 h, most parts (88 hammers + 88 weights + 2 combs). Sensor reads a hammer magnet (3.88 mm travel).
- A/B (spring return) for comparison: 44 → 56 g, effective mass 12 g ("light synth touch").
- v2.0 (old, in hardware/mechanical/before/) rejected a pure tail counterweight because "gravity return time is fixed at ~40 ms (≈12 Hz) regardless of mass, can't do 200 bpm 16ths (13.3 Hz)". CHECK this claim yourself: with firmware re-trigger at partial return (sensor-based, D4/R-requirements allow it) the relevant time is the time to rise from bottom to the re-trigger point, not a full return. A light assist spring is now allowed.

## 4. The v3 system this action must plug into (keep unless you justify a change)
Full extract of the v3 report (dimension tables P/S/D/A, mechanism text, calcs, risks): scratchpad/v4/context/v3_extract.txt. Key facts:
- Octave module C–B, identical, detachable (R17/R18), width 164.5 (pitch 23.5 white, black slot 13.708). 88 keys = 7 modules + left end part (A0, A#0, B0, 47 mm) + right end part (C8, 39.5 mm). Modules join with printed dovetails.
- White key: head 22.5 wide (gap 1.0), visible length 146 (y0 front lip → y146 in v3), top z43.5 above desk (z=0 desk), bottom z23.5, height 20. Black key: base width 11, top 9.5, top z55.5 (12 above white), front at y51.5–52.5, top ends y142. Dip: white 10 at y0, black 9.5 at y52.5.
- Sensing (keep if at all possible — electronics are designed and costed): DRV5055A2 (or OH49E) lying flat on a hand-soldered stripboard (6 rows, 15.24 mm) inside a printed sensor bar at y59–77.5, element row y67, element z≈12.7 (white) / 10.2 (black). Ø5×2 N35 magnet in the key at y65.8 (white) / 64.2 (black), rest magnet-face→element 10.8 (white) / 13.35 (black), bottom 4.7 / 4.9. Minimum mechanical gap 3.0 mm. Velocity comes from magnet travel, so ≥ ~5 mm travel at the sensor is wanted.
- Control board 5×7 cm stripboard at x47.25–117.25, y145.5–195.5, z9–10.6 (components ≤ z20), RP2040-Zero with USB-C pointing +y out of the frame rear; ribbon lane x60–82 from sensor bar to board. You MAY move the control board if the action needs that space — say where it goes.
- Frame depth 212 (y0–212) so the frame fits a 220×220 bed (printer model still unknown; assume 220×220 bed, 0.4 nozzle, 0.2 layer, PETG). Rear bar (speakers + center unit) starts at y215; total instrument depth 410 (212 + 3 + 195), width 1254. Rear cover top z59. If your action needs more depth, give the new total depth and why.
- Felt 3T high-density wool and EVA 3T are already in the BOM. Tungsten putty (ME14) is in the purchase list. Fasteners M3 SUS, nut traps (v3.2 style — no brass inserts).
- Budget: base (non-consumable) BOM is 583,219 KRW of the 1,000,000 KRW cap (R21); consumables (filament, felt…) may exceed the cap. Filament: Bambu PETG Basic (E_flex 1.95 GPa, tensile 51 MPa, HDT 71 °C, density 1.25) — the user bought this.

## 5. Requirements (hardware/mechanical/sound-requirements.md — read R6, R17–R23, D-items)
- R6 behave like a real (entry-level digital) piano: velocity, dip 10 / 9.5, black height 12, downweight ~50 g, repetition helped by firmware re-trigger, felt stops.
- R20 keys are 3D-printed. R22 simplest possible structure, only needed functions. R23 (compliant mechanism) is being RELAXED by this request: gravity return (seesaw / weighted lever) is now the user's explicit direction; metal springs allowed if needed; printed flexures may still be used where they are not permanently preloaded.
- Keys should be individually removable (long-standing scope decision) — or at least removable per octave without tools.
- R26–R29: every part detaches for carrying; a key storage bay holds a spare key set (inner 338.8 × 172 × 77).

## 6. Design targets (numbers every concept must report)
Report at the white key front (finger at y≈13 from the lip, and also at y0 lip) unless stated.
1. Downweight DW (g, static, key just starts to move, including an explicit friction estimate): target 47–55 g. Upweight UW (g): ≥ 20 g (piano: DW−UW = 2×friction). Balance weight = (DW+UW)/2.
2. Effective (inertial) mass at the key front m_eff (g) = I_total / r_front²: entry digital pianos (GHS-class) are ~100 g+; C was 47 g, D 128 g, springs 12 g. More is more piano-like, but it slows return.
3. Return / repetition: time from bottom to the re-trigger point (assume re-trigger when the key has risen 40 % of the dip at the sensor — state your assumption) and time for full return, with and without any assist spring. Target: re-trigger rate ≥ 13.3 Hz (200 bpm 16ths) and ideally full return < 60 ms.
4. Front/back force ratio: force needed at y90 (between black keys) ÷ force at y13.
5. Constant stress in any plastic part at rest (MPa) — target < 2 MPa (no creep story). All pivots must be metal pins/shafts or knife edges on hard surfaces; the rest position must be defined by a felt/EVA stop with gravity (or a steel spring) holding it there.
6. Magnet travel and gaps at the sensor row y67 (rest, bottom, min gap ≥ 3.0).
7. Envelope: depth used (y range), key top z, highest moving part z, lowest z; must fit v3 frame 212 deep × cover z59 if possible. State the total instrument depth.
8. Parts per octave (printed, purchased), assembly steps, removal of a single key.
9. Mass of steel/weights per octave and for 88 keys; filament g and print hours (15 g/h, density 1.25) and whether every part fits a 220×220 bed.
10. Cost delta vs v3 (KRW) — list purchased items with spec and a plausible Korean source/price (verify with a web search when you can).
11. Noise: every impact (down-stop, up-stop, weight top/bottom, coupling) and how it is damped; coupling play.
12. Risks and a stage-0 test that would falsify the design quickly.

## 7. Method rules
- Do the physics with a Python script saved in your concept folder (calc.py) and run it; include moments of inertia of key + lever + weight (parallel-axis), friction assumptions (felt bushing/pin friction torque), gravity torques of every body, lever ratios, and the dynamic return simulation (integrate the equation of motion; include the weight/key contact separation if the hammer can leave the key).
- Keep v3 electronics and body interfaces unless a change clearly wins; say explicitly what you removed compared with a grand action / GHS action / v3.
- Units: mm, g, N, ms. z = 0 desk, y = 0 white key front lip, +y away from the player, x across.
