# Toccata electrical design review (before the schematic is frozen)

Reviewer role: independent senior-HW review of CIRCUIT_BRIEF.md (v3 electronics, still valid for v4 r4.1).
Date: 2026-09-28. Scope: octave sensor board + control board (x7), end parts, PED board + pedal, CU power, CU audio.
Severity: **must-fix** = will not work or can damage; **should-fix** = robustness; **note** = OK as is / information.
"Parts" says whether a fix needs anything that is not already bought (BOM: 100 nF 1206 x100, 1k/10k/100k/100 ohm x10 each, 1 uF leaded MLCC x5).

---

## 0. Verified facts this review relies on (primary sources)

| Item | Fact | Source |
|---|---|---|
| DRV5055 LPG (TO-92) pins | 1 = VCC, 2 = GND, 3 = OUT | TI DRV5055 datasheet SBAS640C (Jun 2026), Table 4-1 |
| DRV5055 VCC | 3.0-3.63 V or 4.5-5.5 V (two isolated ranges); abs max 7 V; OUT abs max VCC+0.3 V | same, 5.1/5.3 |
| DRV5055 ICC @3.3 V | rev C: 2 mA typ / 4 mA max. Earlier revisions: 6 mA typ / 10 mA max ("changed the operating supply current" in rev C history) | same, 5.5 + revision history; older rev on Mouser |
| DRV5055 output | +/-1 mA continuous; linear range 0.2 V .. VCC-0.2 V; 20 kHz BW; 10 us propagation delay; A2 @3.3 V: 30 mV/mT, +/-44 mT, output noise 6 mVpp | same, 5.3/5.5/5.6 |
| DRV5055 capacitive load | No CL limit given. "Do not connect a capacitor directly to the device output without a resistor in between because doing so can make the output unstable." Supply cap >= 0.01 uF. Wire-break idea: output within 150 mV of a rail = fault | same, 7.1.3, 7.1.4, 7.4 |
| CD74HC4067 | RON @4.5 V: 70 typ/160 max ohm (rails), 90/180 (mid); CI 5 pF; CCOM 50 pF; off leakage +/-0.8 uA (25 C); Sn->out 300 ns max @2 V, 60 ns @4.5 V; VIS 0..VCC; E active-low | TI CD74HC4067 datasheet SCHS209D |
| RP2040 ADC | 96 clk @48 MHz = 2 us/sample (500 ksps); ~1 pF sampling cap, effective input impedance > 100 kohm at 500 ksps, "no need to buffer"; ADC input must not exceed IOVDD; digital input must be disabled on ADC pins | RP2040 datasheet 4.9 |
| RP2040 errata | E11: DNL spikes at codes 512/1536/2560/3584, ENOB 8.7 bit, not fixed. E6: GPIO26-29 digital input enabled after reset (SDK/B2 bootrom handles) | RP2040 datasheet, Appendix B |
| RP2040 pads | Pull-up/down 50-80 kohm; reset state PDE = 1 (pull-down on), PUE = 0 | RP2040 datasheet 2.19.6 / 5.5.3 |
| RP2040-Zero (Waveshare) | LDO U1 = **RT9013-33** (500 mA, SOT-23-5, theta-JA ~250 C/W); VSYS = VBUS directly (no diode); ADC_AVDD fed from 3V3 through **R6 200 ohm + C11 2.2 uF**; WS2812 on **GP16**, powered from 3V3 | Waveshare RP2040_Zero.pdf schematic; Richtek RT9013 datasheet |
| Pico ADC offset analogue | "ADC draws ~150 uA ... offset of about 150 uA x 200 = ~30 mV" | Raspberry Pi Pico schematic/datasheet note |
| parts-parts PP-A799-2 | "China OEM" clone, LDO not stated -> must be checked on the board | seller page |
| HUSB238 | VSET open = 20 V; **ISET open = 3.25 A**; RISET 22.6 k = 3.0 A, 19.6 k = 2.75 A, 0 = 1.25 A. Picks the highest PDO with V <= VSET **and I >= ISET**, otherwise tries the next lower PDO. Output (GATE) on at POR, i.e. 5 V before the contract | Hynetek HUSB238 datasheet (Adafruit copy) |
| XL4016 | 8-40 V input (module sold as 4-40 V), 180 kHz, 100 % max duty | XLSEMI datasheet summaries |
| TPA3110D2 | Zi = 60/30/15/9 kohm at 20/26/32/36 dB (+/-20 %, design min 7.2 kohm); single-ended use: AC-ground the unused input **at the source** for best noise; PVCC 8-26 V | TI TPA3110D2 datasheet |
| Pi 5 | PSU_MAX_CURRENT=5000 makes the firmware treat the supply as 5 A and sets usb_max_current_enable automatically (USB 1.6 A instead of 600 mA) | Raspberry Pi forum / PD white paper |
| Apple USB-C dongle | ~1 Vrms max (US), 0.5 Vrms (EU-limited) | head-fi / audioreviews |
| Fuse 0218005.MXP | 250 VAC rated (no DC rating), time-lag | Littelfuse 218 datasheet |
| KCD1-101 | 6 A 250 VAC / 10 A 125 VAC; DC rating differs by maker (some list 20 A 12 VDC) | vendor pages |
| PJ-313 | 30 V 0.5 A contacts; pin numbering differs by maker -> verify with a meter | JLCPCB/vendor pages |
| FluidSynth midi.autoconnect | "connects to available MIDI input ports"; users report it only covers ports present when the driver starts | fluidsynth.org settings, ArchWiki |

---

## 1. Summary table

| ID | Area | Sev. | Problem | Fix | Parts |
|---|---|---|---|---|---|
| R1 | PED pedal jack | must-fix | RING = 3V3 through 0 ohm. Any TS plug (normal switch pedal, mono cable) and many insertion positions short 3V3 to GND; insertion can also drive 3V3 into the unpowered DRV5055 OUT. PED board browns out -> USB re-enumerates -> FluidSynth may lose the port | 3V3 -> **4 x 100 ohm in parallel (25 ohm)** -> jack RING. In the pedal: **1 kohm in series with DRV5055 OUT** before the cable TIP. Check VCC at the pedal >= 3.05 V | BOM (4x100R, 1x1k) |
| R2 | PED pedal | should-fix | DRV5055 OUT drives 3 m of cable (~300-450 pF) directly; TI says no C on OUT without a resistor | Same 1 kohm series resistor as R1 (inside the pedal, at the sensor) | BOM |
| R3 | PED detection | should-fix | "100 k to GP27, GP27 driven to the released level": a GPIO can only output 0 / 3.3 V, not an analog level; needless complexity | **100 kohm TIP -> GND** (fixed), GP27 not connected. Magnet S-pole toward the marked face so pressing raises OUT. Firmware: < 0.15 V = no pedal -> CC64 = 0. Optional: PJ-313 tip-normal contact -> GND | BOM (100k) |
| R4 | EXT inputs O1/O7 | must-fix | End parts are detachable (R26). Unplugged -> C12..C14 (O1) / C12 (O7) float -> random readings -> phantom notes 21-23 / 108 | Per used EXT channel: **1 kohm** EXT pad -> mux Cn, **100 kohm** mux Cn -> GND. Firmware: < 0.15 V = sensor absent, key muted | BOM (4x1k, 4x100k) |
| R5 | PD input | must-fix (verify) | HUSB238 with ISET open requests 3.25 A; a 20 V/3 A power bank (60 W) or the charger in 2-port mode (20 V/2.25 A) fails the "I >= 3.25 A" test at every PDO -> output stays 5 V -> nothing starts | Bench-test each source, module unloaded: must read ~20 V. If 5 V: put ~22 k (10k+10k+1k+1k) on ISET (-> <= 3 A request) if the module exposes it, or use a 20 V >= 3.25 A (65/100 W) source | BOM or none |
| R6 | 5.1 V rail | must-fix (procedure) | XL4016 ships at an unknown output (up to Vin = 20 V); Pi 5, hub and all 8 RP2040-Zero (VSYS = VBUS, no protection) would be destroyed. Cut hub-adapter lead and MT666 polarity unverified | Set 5.10-5.15 V with **no load**, lock the pot (glue), then connect. Verify +/- of MT666 and the cut hub lead with the meter before first plug-in. Optional crowbar: SMBJ5.0A across 5 V after the fuse | none (TVS optional, buy) |
| R7 | Audio ground | should-fix | Ground loop: dongle GND = Pi GND -> MT666/buck -> 20 V GND -> amp GND -> audio cable shields. Pi and amp supply currents create mV-level noise in series with the single-ended amp input (CPU/USB whine) | Star ground at the XL4016 IN- terminal: amp GND wire and PD-trigger GND both land there; keep MT666 short; return the HPF 1 k resistors to amp IN G only. Test at max volume, no notes. If whine: 3.5 mm ground-loop isolator before the HPF (or TPA3110 INN-at-source mod) | isolator only if needed |
| R8 | Mux supply | should-fix | Module decoupling unknown (seller shows none); datasheet practice = 0.1 uF at VCC | 100 nF 1206 across mux module VCC-GND pins (7x) | BOM (97/100 used) |
| R9 | Sensor bus bulk | should-fix | 10 uF "at both ends" is not in the BOM | 1 x 10 uF (1206 X5R 16 V or radial 16-25 V) at the ribbon entry of each sensor board; control-board end already has the RP2040-Zero LDO caps | buy 8 x 10 uF |
| R10 | ADC settling / scan | should-fix | After S0..S3 change, COM (50 pF) + GP26 dumps charge onto the new DRV5055 output; TI gives no recovery/load spec | No C and no R at SIG. Firmware waits t_settle (start 4 us = 2 dummy conversions), tune by test; scan only used channels | none |
| R11 | RP2040-Zero LDO | should-fix (verify) | Clone LDO unknown; O1 worst case ~205 mA and ~0.35 W in a SOT-23 | Read the LDO marking (5-pin RT9013/ME6217 OK; 3-pin "662K" = 200 mA, not OK for O1). Measure O1 3V3 current at bring-up; keep WS2812 off/dim; do not cover the LDO with Kapton/foam | none |
| R12 | Power-on inrush | should-fix (verify) | Rocker closes 20 V onto ~0.5-1.5 mF (amp + XL4016 bulk); some PD chargers/power banks trip OCP -> hard reset | Test 10 on/off cycles per source. If it resets: switch ON first, then plug USB-C (source ramps 5->20 V; XL4016 only starts above 8 V) | none |
| R13 | Pi power-off | should-fix | The rocker cuts the Pi hard -> SD-card corruption over time | Enable read-only overlay FS (raspi-config) or add a shutdown button (dtoverlay=gpio-shutdown) | none (button optional) |
| R14 | USB re-enumeration | note | Any RP2040 reset/replug creates a new ALSA port; midi.autoconnect may not reconnect it | Test unplug/replug of one module; if not reconnected, add a udev rule / aconnect loop script | none |
| R15 | Ratiometric ref / errata | note | ADC_AVDD = 3V3 via 200 ohm (~30 mV low); E11 DNL spikes at 2560/3584 (2.06/2.89 V) lie inside the key swing | Per-key calibration absorbs the offset; keep thresholds >= 10 LSB away from 2560/3584 or apply E11 LUT correction; average 2-4 scans; disable pulls on ADC pins (adc_gpio_init) | none |
| R16 | ID straps | note | OK. Pads reset with pull-DOWN on | Firmware: enable pull-ups on GP6/7/8/14, wait >= 10 us, read. PCB: SolderJumper_2_Open footprints | none |
| R17 | EN | note | EN tied to GND is correct (active-low enable) | If the module has an EN pull-up, tying to GND just wastes ~0.3 mA; measure EN-VCC/EN-GND resistance before soldering | none |
| R18 | Unused channels | note | C12..C15 on O2..O6 (and C15 on O1, C13..C15 on O7) float; harmless for an analog switch while not selected | Firmware never selects them (ID-based channel list). Optional: tie C15 (EXT4) to GND on every board = zero-reference/self-test channel | none |
| R19 | Amp level | note | Dongle ~1 Vrms x TPA3110 gain (26 dB = x20) = 20 Vrms > ~13 Vrms clip at 20 V | Cap software gain so full scale ~0.5-0.6 Vrms (26 dB). If using the series-1k attenuator, the HPF changes: 1k series + 1k shunt with 1 uF gives fc = 80 Hz and -6 dB | none |
| R20 | HPF | note | 2 uF + 1 k = 79.6 Hz; with TPA3110 Zi 7.2-72 k the corner is 80-90 Hz. Correct | Keep; 1 k to amp IN G | none |
| R21 | Headphone jack | note | Direction correct: dongle -> T/R springs, TN/RN -> amp; plug opens normals; amp side held by 1 k | Verify spring/normal pins with the meter (maker-dependent numbering) | none |
| R22 | Speakers / EMI | note | BTL: each speaker needs its own pair; never common L-/R-, never to GND | Twist each pair; keep speaker and 20 V leads >= 30 mm from ribbons/EXT cable in the channel | none |
| R23 | Fuse / switch | note | Source OCP (<= 3.25 A) acts before a 5 A T fuse; fuse and KCD1 are AC-rated but 20 V / <= 3.25 A DC is benign | Keep (4 A T also fine) | none |
| R24 | 5 V drop / Pi config | note | MT666 0.2-0.29 m; ~0.05-0.1 V at 2 A | Set XL4016 5.15 V no-load; check `vcgencmd pmic_read_adc EXT5V_V` >= 5.0 V under load. PSU_MAX_CURRENT=5000 alone is enough (usb_max_current_enable=1 redundant, harmless) | none |
| R25 | Hub back-feed | note | Hub and Pi share one rail and one switch -> back-feed cannot power a "dead" Pi in normal use | Check once with the Pi lead unplugged (Pi 5V pin must read 0 V); if it back-feeds, never run the hub without the Pi lead | none |
| R26 | Fallback voltages | note | 15/12/9 V: amp works with less power (about 12/8/4.5 W per ch into 8 ohm), XL4016 OK (>= 8 V). 5 V: nothing works | See R5 | none |
| R27 | Ribbon | note | Only 14 of 16 wires used; a broken OUT wire makes that channel copy the previous channel (charge sharing) -> phantom notes | Use all 16: 2 x 3V3 + 2 x GND. Strain-relieve both ends (hot glue). Firmware: mute a key whose rest value leaves its calibrated window | none |
| R28 | Pedal ESD | note | 1 k + 100 nF at TIP plus 25 ohm in RING are enough for 3 m cable ESD | No TVS | none |
| R29 | Mech/misc | note | M3 head (dia ~5.5) at hole (3.0, 61.9) reaches y ~64.7 -> can touch the 3V3 bus row (y64.46); screw is floating so no short, but keep bus solder >= 3 mm from the hole or use a nylon washer. EXT uses JST-XH 6P = LiPo balance plug: label it | none |
| R30 | Test points | note | None defined | Add TP: every control board 3V3, GND, SIG(GP26); CU 20V, 5V1, GND; PED TIP, RING | none |

---

## 2. Details by requested item

### (a) 3V3 current budget per octave vs RP2040-Zero regulator

| Load on 3V3 | typ | worst |
|---|---|---|
| DRV5055 x12 (O2..O6), rev C (2 / 4 mA) | 24 mA | 48 mA |
| DRV5055 x12, older rev (6 / 10 mA) | 72 mA | 120 mA |
| O1: 15 sensors (12 + 3 EXT), older rev | 90 mA | 150 mA |
| RP2040 + flash (DVDD via internal reg + IOVDD) | 25-36 mA | 52 mA |
| WS2812 (GP16, on 3V3) off / dim | ~1 mA | 5 mA (full white 50-60 mA: avoid) |
| CD74HC4067, ADC_AVDD | < 0.3 mA | < 0.3 mA |
| **O1 total** | **~66 mA (rev C) / ~126 mA (old)** | **~207 mA** |

RT9013-33 (genuine Waveshare): 500 mA, so current is fine (<= 42 %).
Thermal: VBUS at the board ~5.0 V (hub 5.1 V minus cable). P = 1.7 V x I:
typ rev C 0.11 W (+28 C), typ old 0.21 W (+54 C), worst 0.35 W (+88 C with 250 C/W) -> Tj ~120 C at 30-35 C inside the body. OK for normal parts, marginal only with worst-case old-rev sensors on O1.
Action (R11): check the clone's LDO. A 5-pin SOT-23-5 (RT9013 / ME6217) is fine. A 3-pin "662K" (XC6206-type, 200 mA, ~500 C/W) is **not** acceptable for O1/O7; use a board with a 5-pin LDO there. Measure O1 3V3 current (meter in series with the ribbon 3V3 wire) at bring-up: expect 60-130 mA.

### (b) ADC path: DRV5055 -> 180 mm ribbon -> 4067 -> RP2040

- Direct load on each DRV5055 OUT: ribbon ~9 pF (1.27 mm flat cable ~50 pF/m) + CI 5 pF. When selected: + CCOM 50 pF + GP26 pad/wire ~10 pF, behind RON (~150-300 ohm at 3.3 V, extrapolated from 70-180 ohm at 4.5 V). This is small and RON isolates most of it, so instability is unlikely; there is no TI limit to check against.
- Ideal settling: (RON + Rout) x 70 pF ~ 20 ns, 12-bit in ~0.2 us. The real limit is how fast the DRV5055 output loop recovers from the charge dump (up to 50 pF x 3 V = 150 pC when coming from a 0 V channel) - not specified.
- RP2040 side: 1 pF sample cap, > 100 kohm effective, "no settling time when switching AINSEL" - the RP2040 is not the bottleneck.
- **Do not** add a capacitor at SIG: every mux switch would have to move its charge through RON and the sensor output (slower, bigger kick). A series R at SIG is not needed (SIG-GP26 is < 30 mm on the same board).
- **Firmware (R10):** set S0..S3, wait t_settle, then convert. Start with t_settle = 4 us (or 2 discarded conversions). Tune: read channel k right after a 0 V channel and again after 50 us; use the smallest wait where the difference is < 2 LSB. Health check: at rest a channel should show about DRV5055A2 noise (6 mVpp = ~7-8 LSB pp) plus ADC noise; if it is > ~25 LSB pp or changes when the previous channel is pressed, add 100 ohm in series at each sensor OUT on the sensor board (84 resistors, would need purchase) - only if the test fails.
- Only fallback if firmware settling cannot fix it: per-channel RC before the mux (e.g. 1 k + 10 nF). Not recommended now (168 extra parts).

### (c) Scan rate for velocity

- Per channel: t_settle 4 us + conversion 2 us = 6 us. O2..O6 (12 ch): 72 us -> **13.9 kHz per key**. O1 (15 ch): 90 us -> 11.1 kHz. O7 (13 ch): 78 us -> 12.8 kHz. Even with 8 us settle: >= 6.7 kHz.
- Need: at fortissimo the key crosses a 25-30 % travel window in a few ms; with linear interpolation of the threshold crossing between samples, >= 2 kHz is the practical minimum, >= 5 kHz is comfortable. The design has 2-5x margin. Scanning faster than ~40 kHz is pointless (DRV5055 BW 20 kHz, 10 us delay).
- Put the scan loop on core1, USB-MIDI (TinyUSB) on core0. Average 2-4 consecutive scans for thresholds; keep raw samples for timing.

### (d) Unused channels C12..C15 on O2..O6

- Analog-switch channel pins are not CMOS gate inputs, so floating unselected channels do not draw current or oscillate. Only a *selected* floating channel reads garbage (it copies the previous channel through CCOM charge sharing).
- Fix = firmware channel list by ID (O1: C0..C14, O7: C0..C12, O2..O6: C0..C11). Optional: wire C15 (EXT4) to GND on every board as a 0 V self-test channel (EXT4 is unused on both end parts).
- The real problem is the *used* EXT channels when an end part is unplugged -> **R4 (must-fix)**.

### (e) EN tied low

Correct (E is active-low, low = all switches follow S0..S3). At reset RP2040 pads have pull-down on, so S0..S3 = 0 -> C0 selected: harmless. Only check the module for an EN pull-up resistor (0.3 mA waste, no harm).

### (f) Mux decoupling

Seller page shows no capacitor information; many 4067 breakouts have none. Add 100 nF 1206 directly across the module VCC/GND header pins (R8). 100 nF count: 88 key sensors + 1 pedal sensor + 1 PED TIP filter + 7 mux = 97 of 100 (3 spare).

### (g) Ratiometric reference, RP2040 ADC errata

- Sensors, mux and ADC_AVDD all come from the same RP2040-Zero 3V3 -> ratiometric. ADC_AVDD goes through 200 ohm/2.2 uF (Waveshare R6/C11): ~30 mV low (~1 % gain error, constant) and 3V3 noise above ~360 Hz is filtered on the reference but not on the sensors. Ribbon IR drop ~3 mV per supply wire (28 AWG 180 mm, ~70-150 mA). All constant -> per-key calibration absorbs it. No ADC input can exceed IOVDD because every source is powered from the same 3V3.
- E11: DNL spikes at 512/1536/2560/3584 = 0.41/1.24/2.06/2.89 V. Keys at rest ~1.65 V rising to ~3.1 V when pressed (S pole toward marked face) cross 2560 and 3584. Keep velocity thresholds >= 10 LSB away from those codes or apply a published E11 correction LUT. ENOB 8.7 bit -> average.
- ADC pins: use adc_gpio_init() (disables digital input and the default 50-80 k pull-down); otherwise the pull-down loads the pedal RC node.

### (h) ID straps GP6..8 + GP14

OK. Internal pull-ups 50-80 kohm vs a solder bridge to GND is robust. Pads reset with pull-down enabled, so firmware must switch to pull-up and wait >= 10 us before reading. No RP2040 erratum applies (the pull-down latch-up erratum E9 is RP2350-only). KiCad: SolderJumper_2_Open on GP6, GP7, GP8, GP14.

### (i) PED pedal circuit

Insertion sequence of a TRS plug into PJ-313: the jack's sleeve and ring contacts slide over the plug tip, then the tip/ring insulator, then the ring. With RING = 3V3 through 0 ohm:
1. Jack ring (3V3) on plug tip (= sensor OUT) while plug ring (= sensor VCC) touches the jack sleeve (GND): 3V3 is forced into OUT of an unpowered sensor, current limited only by the LDO (hundreds of mA) through the OUT clamp -> can damage the DRV5055.
2. Jack ring and sleeve both on the long plug tip, or any TS plug (normal sustain pedal, mono cable): 3V3 shorted to GND -> PED board browns out/resets (RT9013 current limit), USB port disappears (see R14).

Fix (R1/R2), all parts from BOM:
- PED board: 3V3 -> **4 x 100 ohm 1/4 W in parallel (25 ohm)** -> J(ring). Dead short: 132 mA, 0.11 W per resistor, LDO total ~170 mA -> no brownout.
- Pedal: DRV5055 OUT -> **1 kohm** -> cable TIP (right at the sensor). Case 1 current becomes (3.3-0.7)/1025 = 2.5 mA (safe), and the 3 m cable capacitance is isolated per TI 7.1.3.
- Sensor supply check: V = 3.3 - I x (25 ohm + 2 x cable ~0.6-1 ohm). rev C 4 mA max -> 3.19 V; old 6 mA typ -> 3.14 V; old 10 mA max -> 3.03 V (2.96 V if the LDO is 2 % low). Measure RING-SLEEVE at the pedal with it plugged in: must be >= 3.05 V; otherwise use 5 x 100 ohm (20 ohm).
- Keep TIP -> 1 kohm -> GP26 with 100 nF to GND (fc 1.6 kHz, good ESD/anti-alias). Total series 2 kohm with the 100 k pull-down = ~2 % gain error, calibrated.
- Replace "100 k to GP27 driven to released level" with **100 kohm TIP -> GND** (R3). GP27 = NC. Orient the pedal magnet S-pole toward the marked face so pressing raises OUT (same as the keys); unplugged reads ~0 V; firmware threshold < 0.15 V = no pedal (TI uses the same 150 mV band as "fault"). Optional zero-part extra: wire the PJ-313 tip-normal contact to GND so an empty jack is hard-grounded.
- ESD on the 3 m cable: TIP has 1 k + 100 nF, RING has 25 ohm into the 3V3 rail with LDO caps, SLEEVE = GND. Adequate; no TVS (R28).

### (j) Power

- **PD trigger (R5):** HUSB238 needs a PDO with V <= 20 V and I >= ISET. ISET open = 3.25 A. The 65 W charger (single port) offers 20 V 3.25 A -> OK. A 20 V/3 A power bank or the charger with two ports in use (20 V 2.25 A) -> no PDO passes -> output 5 V. Verify with each source before wiring. If the module brings out ISET, ~22 k to GND (10k+10k+1k+1k from BOM) sets a <= 3 A request (between the 2.75 A and 3.0 A table steps; both match a 3 A PDO).
- Before the contract the HUSB238 output is 5 V (GATE on at POR). XL4016 needs >= 8 V, so the 5.1 V rail stays off/low until 20 V arrives; harmless. Preferred habit: plug in USB-C with the switch OFF, then switch ON.
- **Fuse 5 A T:** the PD source limits at <= 3.25 A (3 A cables), so the fuse only acts as a last-resort short protection; AC-only rating is acceptable at 20 V with a current-limited source (R23).
- **Rocker KCD1-101A:** AC-rated; 20 V DC <= 3.25 A is below typical DC-arc sustain conditions; OK for a hobby build.
- **Inrush (R12):** amp + XL4016 bulk (~0.5-1.5 mF; read the markings, amp caps should be >= 25 V, preferably 35 V). Test 10 switch-ons per source.
- **XL4016 load:** Pi 5 2GB 1-2 A (FluidSynth), hub + 8 boards 0.6-1.3 A, dongle ~0.1 A -> 2-3.5 A peak vs 5 A module. OK with airflow. Output ripple (180 kHz) is filtered by each RP2040-Zero LDO.
- **Setting (R6/R24):** 5.10-5.15 V no-load; MT666 (0.2-0.29 m, gauge not stated) drops ~0.05-0.1 V at 2 A; check EXT5V_V >= 5.0 V under load (Pi 5 flags under-voltage below ~4.63 V per forum reports; aim well above).
- **Pi config:** PSU_MAX_CURRENT=5000 is correct and sufficient; usb_max_current_enable=1 is redundant but harmless. Pi USB load here is small (self-powered hub + dongle), so even 600 mA would do; the setting mainly removes the "not 5 A" warning.
- **Hub back-feed (R25):** check once with Pi lead unplugged, hub powered: Pi GPIO 5V pin must be 0 V.
- **Fallback voltages (R26):** 15 V -> amp ~12 W/ch into 8 ohm, 12 V -> ~8 W, 9 V -> ~4.5 W; XL4016 fine at >= 8-9 V. 5 V -> no amp, no Pi.
- **Power-off (R13):** the rocker kills the Pi without shutdown; use overlay (read-only) root FS.

### (k) Audio

- **HPF:** 2 uF (2 x 1 uF X7R 50 V leaded) series, 1 kohm to IN G: fc = 1/(2 pi 1k 2u) = 79.6 Hz. TPA3110 Zi (7.2-72 kohm incl. tolerance) in series with the board's own input cap parallels the 1 k: effective 0.88-0.99 k -> 80-90 Hz. The board's own input HPF (Cin x (Zi+1k)) sits at ~3-20 Hz (depends on its cap), so the 1 k network dominates. The 1 k also gives the board input caps a fast charge path (TI asks for <= 1 ms). OK (R20). X7R at ~1 Vrms on 50 V parts: distortion negligible.
- **Dongle driving 1 k:** designed for 32 ohm; 1 k is trivial. Level: 1 Vrms x 20 (26 dB) > clip -> limit software gain (R19). If you fit the optional 1 k series attenuator in front, use one 1 uF cap: 1/(2 pi x 2 k x 1 u) = 80 Hz and -6 dB.
- **Ground loop (R7):** dongle ground is the Pi ground; the amp input ground is the amp board ground; the audio cable shields close a loop through USB, MT666, buck and the 20 V wiring. Mitigation in order: (1) star point at XL4016 IN- (amp GND and PD GND wires meet only there; 16 AWG, short); (2) MT666 as short as possible; (3) the two 1 k shunts go to amp IN G, the jack sleeves only to IN G - no other ground connections from the audio path; (4) test at max volume, no notes playing, Pi under load; (5) if whine/hiss: 3.5 mm ground-loop isolator (purchase) between jack #3 and the HPF, or the TPA3110 "ground INN at the source" modification (advanced).
- **Class-D EMI near hall sensors:** speaker current 2 A at 20 mm gives ~0.02 mT (~0.6 mV, < 1 LSB) for a single wire and near zero for a twisted pair; DRV5055 BW 20 kHz rejects the ~300 kHz PWM ripple. The concern is capacitive pickup of PWM edges on the end-part EXT cable that shares the cable channel with speaker leads. Twist speaker pairs, keep >= 30 mm apart, twist EXT signal wires with GND (R22). Keep speakers >= 100 mm from sensors (D14 OK); also keep the XL4016 inductor away from the key bed.
- **BTL:** no speaker terminal to GND and no shared L-/R- return (would short the bridge outputs). XT30 per channel is correct. No series capacitor (D13) is correct.
- **Headphone jack switching (R21):** correct direction. No plug: dongle -> T/R springs -> TN/RN -> cable 2 -> jack #3 -> HPF -> amp. Headphones in: springs lift off TN/RN, dongle drives only the headphones; amp inputs held at GND by the 1 k shunts (no hum). Plug insertion momentarily shorts the dongle output to sleeve (normal for any headphone jack; the dongle is protected). PJ-313 pin numbering differs by maker: confirm spring vs normal pins with continuity (plug out: T-TN 0 ohm; plug in: open).

### (l) Other items

- **R4** EXT pull-downs (must-fix) - see table. Also: a pinched EXT cable can short O1's 3V3; no series resistor is possible (sensor VCC must stay >= 3.0 V), so rely on the locking JST-XH and strain relief.
- **R27** ribbon: use all 16 wires (2 x 3V3, 2 x GND), hot-glue strain relief at both solder ends.
- **R29** mounting holes / connector labeling.
- **R30** test points.
- **Polyfuses:** not needed on module 5 V (hub ports are current-limited by the hub's switch or its supply; loads < 0.25 A). Note only.
- **ESD at USB-C of RP2040-Zero:** no TVS on the board (27 ohm series only); modules are inside the plastic body; acceptable.
- **R14** USB re-enumeration vs midi.autoconnect: test by replugging one module; if it does not come back, add a udev/aconnect script. This also makes R1 more important (a pedal plug-in reset would kill the pedal until restart).

---

## 3. Schematic changes to enter in KiCad (net level)

Octave control board (identical PCB for all 7; populate per ID):
- C_MUX 100 nF 1206: mux module VCC <-> GND at the header pins (all boards).
- R_EXT1..R_EXT4 1 kohm: EXTn pad -> mux C(11+n) (footprints on all boards; fit on O1 n = 1..3, O7 n = 1; 0 ohm/wire elsewhere or leave open).
- R_PD1..R_PD4 100 kohm: mux C(11+n) -> GND (fit O1 n = 1..3, O7 n = 1).
- Optional: C15 -> GND wire (self-test channel).
- JP1..JP3 (GP6, GP7, GP8 -> GND), JP4 (GP14 -> GND): SolderJumper_2_Open.
- TP: 3V3, GND, SIG.

Octave sensor board:
- Ribbon 16 wires: OUT_C..OUT_B (12), 3V3 x2, GND x2.
- C_BULK 10 uF at the ribbon entry (purchase).

PED board:
- R_RING = 4 x 100 ohm in parallel: +3V3 -> J2 RING.
- R_TPD 100 kohm: J2 TIP -> GND.  (replaces the 100 k to GP27; GP27 = NC)
- R_TIP 1 kohm: J2 TIP -> GP26; C_TIP 100 nF: GP26 -> GND (unchanged).
- Optional: J2 tip-normal -> GND.
- TP: TIP, RING.

Pedal (inside):
- U 1 = DRV5055: pin1 VCC -> cable RING, pin2 GND -> cable SLEEVE, pin3 OUT -> **R 1 kohm** -> cable TIP; C 100 nF VCC-GND at the sensor.

CU:
- Star GND node at XL4016 IN-: PD trigger OUT-, amp GND. HPF: 2 x 1 uF per channel in series, 1 kohm per channel to amp IN G.
- Optional SMBJ5.0A across the 5.1 V rail (crowbar, fuse-backed) - purchase.

## 4. BOM impact

| Part | Bought | Used after review | Left |
|---|---|---|---|
| 100 nF 1206 | 100 | 88 keys + 1 pedal + 1 PED tip + 7 mux = 97 | 3 |
| 1 kohm | 10 | HPF 2 + PED tip 1 + pedal OUT 1 + EXT 4 = 8 (+2 if the optional attenuator is used) | 2 / 0 |
| 100 kohm | 10 | PED tip pull-down 1 + EXT 4 = 5 | 5 |
| 100 ohm | 10 | PED ring 4 (or 5) | 6 / 5 |
| 10 kohm | 10 | ISET option 2 | 8 |
| 1 uF MLCC | 5 | HPF 4 | 1 |
| New (should) | - | 10 uF x8 | buy |
| New (only if a test fails) | - | 3.5 mm ground-loop isolator; SMBJ5.0A | buy if needed |

## 5. Bring-up checklist (multimeter DT-832)

1. PD trigger alone: each source (charger 1-port, power bank) -> ~20 V. (R5)
2. XL4016 alone: set 5.10-5.15 V no load, glue pot. Polarity of MT666 and the cut hub lead. (R6)
3. Each control board before plugging sensors: 3V3-GND not shorted; ID reads correctly over USB.
4. O1 3V3 current 60-130 mA expected; LDO not too hot to touch (< 60 C). (R11)
5. Each key: rest value ~1.65 V +/- magnet offset; pressed rises. EXT unplugged reads < 0.15 V. (R4)
6. Pedal plugged: RING-SLEEVE at pedal >= 3.05 V; unplugged TIP reads ~0 V. (R1/R3)
7. Hub back-feed: Pi lead unplugged -> Pi 5V pin 0 V. (R25)
8. 10 switch-on cycles per source without reset. (R12)
9. Max volume, no notes: listen for whine. (R7)
10. Replug one module USB: port reconnects to FluidSynth. (R14)

## Sources

- [TI DRV5055 datasheet (SBAS640C, Jun 2026)](https://www.ti.com/lit/ds/symlink/drv5055.pdf); older revision ICC values: [Mouser copy](https://www.mouser.com/datasheet/2/405/drv5055-1285482.pdf), [TI E2E supply-current change thread](https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/1680901/drv5055-drv5055a1qdbz-supply-current-changes)
- [TI CD74HC4067 datasheet (SCHS209D)](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)
- [RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) (4.9 ADC, 2.19 pads, 5.5.3 pin specs, 5.7 power, Appendix B errata E6/E11)
- [Waveshare RP2040-Zero wiki](https://www.waveshare.com/wiki/RP2040-Zero), [RP2040-Zero schematic](https://files.waveshare.com/upload/4/4c/RP2040_Zero.pdf)
- [Richtek RT9013 datasheet](https://dl.linux-sunxi.org/T507/other_datasheets/richtek_ldo_RT9013.pdf)
- [Pico schematic ADC offset note](https://iot-kmutnb.github.io/blogs/rpi-rp2040/images/pico_schematic.pdf)
- [RP2040 E11 correction library](https://github.com/kitanokitsune/rp2040adc_correction)
- [parts-parts PP-A324 mux module](https://parts-parts.co.kr/product/detail.html?product_no=303), [parts-parts PP-A799-2 RP2040-Zero](https://parts-parts.co.kr/product/detail.html?product_no=2383)
- [Hynetek HUSB238 datasheet (Adafruit copy)](https://cdn-learn.adafruit.com/assets/assets/000/125/150/original/husb238_datasheet_full.pdf), [done.land HUSB238 notes](https://done.land/components/power/powersupplies/usb/usbtriggers/husb238/), [icbanq P017179277](https://www.icbanq.com/P017179277)
- [XL4016 datasheet summary (LCSC)](https://www.lcsc.com/product-detail/DC-DC-Converters_XLSEMI-XL4016E1_C55881.html), [icbanq P017179502](https://www.icbanq.com/P017179502)
- [TI TPA3110D2 datasheet](https://www.ti.com/lit/ds/symlink/tpa3110d2.pdf); XH-A232 specs: [Tayda](https://www.taydaelectronics.com/tpa3110-xh-a232-digital-stereo-audio-power-amplifier-board.html)
- [Raspberry Pi forum: usb_max_current_enable vs PSU_MAX_CURRENT](https://forums.raspberrypi.com/viewtopic.php?p=2313971), [Pi 5 USB PD white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-009856-WP-1-USB%20Power%20delivery%20on%20Raspberry%20Pi%205.pdf)
- [MAXTEK MT666 (eleparts)](https://www.eleparts.co.kr/goods/view?no=17358965)
- [Littelfuse 218 series datasheet](https://www.littelfuse.com/assetdocs/littelfuse_fuse_218_datasheet.pdf), [KCD1 guide (LCSC)](https://www.lcsc.com/blog/kcd1-switches-rocker-switches-guide/)
- [PJ-313 (JLCPCB part page)](https://jlcpcb.com/partdetail/SHOUHAN-PJ_3135JCJ/C668607)
- [Apple USB-C dongle output level (audioreviews)](https://www.audioreviews.org/apple-audio-adapter-review/)
- [FluidSynth MIDI settings](https://www.fluidsynth.org/api/settings_midi.html), [ArchWiki FluidSynth](https://wiki.archlinux.org/title/FluidSynth)
