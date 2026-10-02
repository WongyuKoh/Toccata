# Round r4.4: close the open issues of the W1+ key action (r4.3 → r4.4)

The project is Toccata, a hobbyist 3D-printed 88-key MIDI piano. The key action W1+ r4.3 is complete and published:
- short PETG seesaw key on a Ø4 SUS rod
- a tail M3 capstan lifts a printed lever carrier holding an SS400 9×19×40 block on a Ø4 rod
- torsion assist spring
- up-stop pads on slide-out pad bars

The user asked: **"남은 문제 부분을 고쳐줄래"**, which means fix the remaining issues. This round closes the r4.3 open issues without undoing anything that works.

## Read first
- `final/DESIGN.md`: the r4.3 design document. Read §0 (criteria and results), §1d (circuit interface), §9 (clearances), §12 (adjustments), §15 (printing), §17 (stage-0 tests) and §18 (remaining risks).
- `final/model_v4.py`, `final/run_all.py`, `final/export_geo.py`, `final/make_design_md.py`: the single model. It produces geometry.json, metrics.json, results.txt, DESIGN.md and parts_list.json.
- `report_r4/open_issues.r4_3.json`: the 7 open issues listed below, in Korean.
- The r4.3 backup is in `final_r4_3/` and `drawings_r4_3/`. Never edit the backups, `final_r3/` or `drawings_r3/`.

## The open issues
1. **Lever upper snap lip.** The lip is 0.8 × 1.0 and sits on the carrier's top edge. At full press (dip/ff) it comes into the space beside the up-stop pad and misses the 1.0 mm clearance rule (±0.3 FDM).
   - The lip is not exported to geometry.json, so the model's clearance check missed it. The drafter found it.
   - Also export the lever pin-boss holes and the rod end plugs so they are checked too.
   - Fix it without adding parts: shorten or move the lip out of the pad zone (y160–172 and the pad-bar rails). Check that the steel block is still retained with a numeric retention check.
2. **F / F# rest felt partial landing.** The r4.3 USB shelf slot (x76.45–91.55) leaves the F rest felt 59 % seated and the F# rest felt 42 % seated.
   - Still to run under that condition: the return-overshoot pose sweep, and dynamics at the weak 6-key chord site (top plate 492 N/mm).
   - Run both. If a target fails, fix it without adding parts and without touching the circuit interface.
3. **Black-key dip export.** The black-key dip polygon is exported at the rigid kinematic bottom (6.22°) instead of the truly settled 1 N bottom with the pad (6.08°), which the white keys already use. Make the export consistent, and keep the rigid pose as a separate field if the drawings need it.
4. **Circuit interface** (the circuit session owns hardware/pcb). These conditions are frozen: do not change them without flagging it.
   - USB-C cable overmould ≤ 12.5 × 7.6 × 25 (plug z10.7–18.3; shelf slot edge clearance exactly 1.30).
   - RP2040-Zero top parts and header-pin tips ≤ z16.3; the y194.5–195.5 band ≤ z16.7.
   - Shelf underside z18.05; wall opening z5–21; keep-out x81.22–85.42 × y≤173.2.
   - The circuit session already published these (merged artifact v5).
   - Task: find real buyable USB-C cables (sold in Korea, or AliExpress) whose C-plug overmould meets the limit, with measured dimensions from a datasheet or product page.
5. **Documentation.**
   - Dimension-table rounding is inconsistent (e.g. 0.955 → 0.95; pick one rule: round half away from zero at the shown precision, and make every generated table use one helper).
   - Parts of §15 (print plan) and §13 (spare-key storage, A08) are older than parts_list.json.
   - The three printed tools (bench jig, capstan bench gauge, balance-pin height gauge) have only working heights and no shapes; drawing 13 is schematic.
   - Task: design the tools with real dimensions (printable, parametric from the model) and put them in the model output and the drawings.
6. **Stage-0 tests.** Pad rebound e ≤ 0.07, base-plate deflection ≤ 0.07 mm at 100 N, and torsion spring quality are assumptions.
   - They need physical tests; nobody can run them here.
   - What *can* be done: a ready-to-print stage-0 test kit. Coupon models (STL) plus a Korean procedure with pass/fail numbers, the measuring method, and what to change in the model for each outcome.

## Rules (unchanged from r4)
- **PLAY** (key-front speed ≤ 1.5 m/s): every functional target must hold.
- **ABUSE** (2.5 m/s single key, 2.0 m/s 6-key chord): no damage only.
- Clearance ≥ 1.0 mm after ±0.3 FDM between moving bodies and their neighbours.
- **Scope:** all octave modules are identical. Work on ONE module: the worst-case white key shape of the 7, black C#, plus F and F# for issue 2. Add the end-part keys A0 and C8 only where a change touches them.
- Dynamic case grid: PLAY 0.5 / 1.0 / 1.5 m/s × finger holds 0.45 / 1 / 2 N plus release; ABUSE 2.5 m/s single key; materials nominal and worst.
- Do not add parts unless there is no other way. If you must, say so with the cost.
- Coordinates:
  - z0 = desk, y0 = white key front lip (+y away from the player), x0 = C left boundary.
  - Module width 164.5, frame depth 212, total depth 410.
- Python: `scratchpad/venv/bin/python` (numpy, scipy, resvg_py, trimesh). OpenSCAD: `/opt/homebrew/bin/openscad`.
- Korean text in DESIGN.md, drawings and procedures. Code and comments may be English.
- The user values speed: work only on what the issue needs, and report the most important findings first.
