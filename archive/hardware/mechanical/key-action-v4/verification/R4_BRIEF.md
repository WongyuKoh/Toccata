# Toccata v4 W1+ — round 4 brief (fix + SIMPLIFY)

Scratch root: /private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/2f19e142-4ac2-4c90-bd1e-b3b469f97487/scratchpad/v4
Python: ../venv/bin/python (numpy, scipy, matplotlib, resvg_py).
Read first: context/DETAIL_BRIEF.md (architecture, conventions), final/DESIGN.md (r3 design, 700 lines — §0 targets, §2 r2→r3 changes, §3 parts, §15 cost, §20 risks), final/model_v4.py + run_all.py + export_geo.py (the single-source model), context/r3_findings.json (round-3 verifier findings: 8 major + 10 minor), drawings/geometry_patch.json + drawings/geo_patch.py (corrections the drafter applied ONLY in the drawings: end-part joint bosses, plan lever-rod x, black magnet bosses, assist spring — they must be merged into the model), drawings.json issues_left in detail_result.json (key `drawings`).
r3 is backed up in final_r3/ and drawings_r3/ — never edit those.

## Why round 4 exists
The user asked for a gravity-return seesaw action "with every part that can be removed removed, and made smaller". Rounds 1–3 made the model pass ever stricter checks, and the design grew: 8 thumb screws with 3×3 disc-spring stacks per module, tapped SS400 strips in printed pockets, SUJ2 hardened lever shaft, 5 g lead in every black key, cover locating pins + magnets, brass bushings, C-rings, 12 service blocks, snap notch. Module mass went 0.59 kg (v3) → 2.03 kg, cover top z59 → z78 (screw heads z80.7), base cost +130,400 KRW. The user has now seen this and asked to continue.

## Revised load criteria (decided — apply them everywhere, state them in DESIGN.md §0)
Measured piano key-front speeds reach roughly 1–1.5 m/s in fortissimo (hammer 5–7 m/s ÷ ~5 lever ratio); 2.5 m/s is a slap/abuse case. Verify this with 1–2 sources and cite them in DESIGN.md.
- PLAY envelope, key-front speed ≤ 1.5 m/s (single keys, rolled and simultaneous chords of up to 6 keys, fingers held at 0.45–2 N or released): EVERY functional target must hold — DW 47–55 g, UW ≥ 20 g, repetition ≥ 13.3 Hz (also with doubled friction, assist spring allowed if it can really be built), full return < 60 ms, notch lift ≤ 0.2 mm, keeper never touched, no ghost re-trigger above the firmware re-arm line (firmware filter may be used, state it), up-stop joint stays closed, sensor gap ≥ 3.0, clearances ≥ 1.0 after ±0.3 FDM.
- ABUSE envelope, 2.5 m/s single key and 2.0 m/s 6-key simultaneous: NO DAMAGE only — no yield, stresses below fatigue limits for ≤ 10^4 events, no part leaves its seat permanently (a key may lift and reseat), no loss of adjustment. Momentary joint opening, notch lift up to the pop-out margin with safety factor 2, and a filtered ghost event are acceptable.

## Simplification targets (try hard; report what was achieved and what each removal costs)
- Up-stop: lower the peak up-stop force by a softer / longer-travel lever stop (thicker felt or felt + low-rebound foam with enough travel) so the rail mount can be simple — e.g. plain M3 through-bolts or hand-turned knurled nuts in fins loaded in compression, no disc springs, no tapped strips, no pockets. Keep single-key removal TOOL-FREE (hand-turned knobs/nuts or quarter-turn latches are fine; no driver, no 24 h re-tightening).
- Black keys: remove the 5 g lead if the play-envelope notch-lift target holds with pad/felt choices; otherwise explain.
- Lever shaft: plain SUS304 Ø3 if the revised loads allow it (no hardened shaft, no brass bushings unless wear requires).
- Cover: rest it on the rail/fins without locating pins or magnets if possible.
- Heights: cover top ≤ z74, nothing above it; module mass ≤ 1.6 kg if possible (steel blocks alone are 0.91 kg/module).
- Remove service blocks / C-rings / other small parts if a simpler feature does the job.
- Everything else from r3 that is not needed under the revised criteria.

## Must also resolve
All 8 major + 10 minor round-3 findings (context/r3_findings.json) — or show with numbers why a finding no longer applies after simplification. Merge drawings/geometry_patch.json into the model. Keep the spare-key bay ≥ 1 mm clearance per side. End parts use the same mechanism and the same simplifications.

## Outputs (overwrite in final/, r3 is backed up)
model_v4.py, run_all.py, export_geo.py, geometry.json, metrics.json, results.txt, DESIGN.md (Korean; add a section "r3 → r4 단순화" with a before/after parts table: count, mass, cost, height, and what each removal cost in performance), parts_list.json (every printed and purchased part with qty per module / 88 keys, spec, mass).
