# Toccata: mapping the parts to the KiCad standard library (research notes)

Date: 2026-09-28. Everything below was checked against the official KiCad library repos (GitLab `kicad/libraries/kicad-symbols` and `kicad-footprints`):
- Main check: tag **9.0.9.1**.
- Spot checks: tags **8.0.9** and **10.0.6** (the current release). In these tags every symbol and footprint name used below exists with the same name.
- Since KiCad 10 / master, the symbol repo stores symbols as `.kicad_symdir` folders with one file per symbol. Library and symbol names did not change.

Pin tables come from parsing the actual `.kicad_sym` and `.kicad_mod` files.

Status labels used below:
- **VERIFIED**: I read the library file.
- **DATASHEET**: taken from the manufacturer's document.
- **MEASURE**: the physical part must be checked with calipers or a multimeter.

---

## 0. Summary of the key findings

1. **KiCad has no official RP2040-Zero symbol or footprint.**
   - Use a custom part. The best third-party option is `dj505/RP2040-Zero-KiCAD` (CERN-OHL-P-2.0), and its symbol and footprint match each other.
   - Do NOT use `CountParadox/RP2040-Zero-Kicad`. Its own README says "DO NOT USE … this footprint is wrong".
2. **The CD74HC4067 symbols are in the `74xx` library, not `Analog_Switch`.**
   - They are `74xx:CD74HC4067M` (SOIC-24W) and `74xx:CD74HC4067SM` (SSOP-24).
   - `Analog_Switch` only has `HEF4067BT` and `HEF4067BTT`.
   - Toccata uses a breakout module, so use a custom symbol, or `Conn_01x08` + `Conn_01x16`.
3. **The DRV5055 symbol exists, but only under the "-Q1" names.**
   - Use `Sensor_Magnetic:DRV5055A2xLPGxQ1` for the TO-92 package and set its Value to `DRV5055A2QLPG`. The pinout is the same.
   - **The SOT-23 (DBZ) package has a different pin order** (1 VCC, 2 OUT, 3 GND). Never reuse TO-92 pad numbers for it.
4. **`Connector_Audio:AudioJack3_SwitchTR` uses letters as pin numbers.**
   - The pin numbers are `T`, `TN`, `R`, `RN`, `S`, and the pin names are empty (`~`).
   - Any footprint must name its pads with the same letters. `Jack_3.5mm_CUI_SJ1-3525N_Horizontal` does; there is no PJ-313 footprint in the library.
5. **There are no `+20V` or `+5V1` power symbols.**
   - Since KiCad 8, a power symbol's **Value field is the net name**.
   - So either edit the Value of `power:VCC` / `power:+VDC`, or (better) add `+20V` and `+5V1` to a project power library.
6. **In the XT30 footprints, pad 1 is marked "−" and pad 2 is marked "+".** This holds for `AMASS_XT30U-M`, `-F` and `XT30PW-M` (read from the silkscreen text positions).
7. **Annotation:** Tools → Annotate Schematic → Numbering "First free after sheet number × 100".
   - A sheet file reused 7 times creates 7 instances, and each instance gets its own reference designators and page number.
   - **Caveat:** power symbols are global, so `+3V3` would join all 7 boards' separate 3V3 rails into one net (see §4).

---

## 1. Symbol and footprint mapping table

"Excl. board" means: set the symbol attribute **Exclude from board**. The symbol stays in the schematic but gets no footprint on the PCB. Use it for panel or cable parts such as the fuse holder, rocker switch, XT30, speakers, cable plugs and modules. (KiCad manual: "Exclude from board means that the symbol is schematic-only".)

| # | Part (Toccata) | Ref | Symbol `lib:name` | Footprint `lib:name` | Confidence |
|---|---|---|---|---|---|
| 1 | Resistor, 1/4 W THT (1 kΩ, 100 kΩ, 0 Ω) | R | `Device:R` | `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal` (KiCad describes it as "0.25W = 1/4W", 6.3×2.5 mm body, 0.8 mm drill). Alternatives: `..._P10.16mm_Horizontal` (KiCad's default spacing) and `..._P2.54mm_Vertical` | VERIFIED |
| 2 | 100 nF 1206 (Samsung CL31B104KCFNNNE) | C | `Device:C` | `Capacitor_SMD:C_1206_3216Metric`. For hand soldering, `Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` is better | VERIFIED |
| 3 | 1 µF X7R 50 V leaded MLCC (80 Hz high-pass filter, 2 in parallel) | C | `Device:C` | For 5.0 / 5.08 mm lead spacing: `Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm`, or the MKS-style `Capacitor_THT:C_Rect_L7.2mm_W2.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2`. For 2.5 / 2.54 mm spacing: `Capacitor_THT:C_Rect_L4.0mm_W2.5mm_P2.50mm`. **MEASURE the lead spacing of the part you buy** | VERIFIED names; the spacing depends on the part |
| 4 | 10 µF bulk capacitor at each end of the 3V3 bus (not in the BOM yet) | C | Preferred: `Device:C` with a 10 µF ≥10 V X5R/X7R 1206 MLCC → `Capacitor_SMD:C_1206_3216Metric` (same footprint as the 100 nF). Alternative: `Device:C_Polarized` → `Capacitor_THT:CP_Radial_D5.0mm_P2.00mm` (**pin 1 = +**, square/rounded-rect pad; the symbol puts pin 1 at the top, the + side) | see left | VERIFIED |
| 5 | DRV5055A2QLPG (TO-92 "LPG") | U | `Sensor_Magnetic:DRV5055A2xLPGxQ1` (change Value to `DRV5055A2QLPG`) | Symbol default: `Package_TO_SOT_THT:TO-92_Inline` (1.27 mm pitch, standing). For lying face-up with leads bent down: `Package_TO_SOT_THT:TO-92_Inline_W4.0mm_Horizontal_FlatSideUp` (1.27 mm pitch; the body is drawn on the −Y side of the pads, bounding box y −9.14…+1.0). For 2.54 mm lead spacing (standing): `Package_TO_SOT_THT:TO-92_Inline_Wide`. **No "Wide + Horizontal" footprint exists.** To keep the perfboard's fanned 2.54 mm lead layout on a PCB, make a custom copy of the FlatSideUp footprint with pads moved to a 2.54 mm pitch | VERIFIED (lib) + DATASHEET (pins) |
| 6 | CD74HC4067 chip (reference only) | U | `74xx:CD74HC4067M` (SOIC-24W, footprint `Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm`), or `74xx:CD74HC4067SM` (SSOP-24, `Package_SO:SSOP-24_5.3x8.2mm_P0.65mm`) | n/a (the chip sits on the breakout) | VERIFIED |
| 7 | CD74HC4067 breakout module (parts-parts PP-A324, "TENSTAR ROBOT" board, 41×18 mm) | A or U | Custom `Toccata:CD74HC4067_Breakout` (recommended; pin names shown in §2.3). Minimal option: `Connector_Generic:Conn_01x08` (control row) + `Connector_Generic:Conn_01x16` (channel row) plus net labels | Custom `Toccata:CD74HC4067_Breakout_41x18mm` with both rows, or 2 separate footprints `Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical` + `PinHeader_1x16_P2.54mm_Vertical`. **MEASURE the row-to-row spacing and the X offset of the 8-pin row relative to the 16-pin row** | Pin order from the seller photo = high; offsets = unknown |
| 8 | RP2040-Zero (Waveshare or clone, soldered flat by its castellated edges) | U or A | No official symbol. Use `dj505/RP2040-Zero-KiCAD` `RP2040-Zero` (23 pins), or make your own (§2.2) | dj505 `RP2040-Zero.pretty/RP2040 Zero.kicad_mod`: each pad has a 3.5×1.7 mm SMD pad **and** a 0.8 mm through-hole, so it works flat or with headers. Rename it without the space, e.g. `Toccata:RP2040-Zero_Castellated` | pinout DATASHEET-verified; dj505 files VERIFIED as consistent; **print 1:1 and check against the module** |
| 9 | Solder jumpers (ID0..ID2, PED detect) | JP | `Jumper:SolderJumper_2_Open` (pin 1 = A, pin 2 = B) | `Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm` (SMD, pads "1" and "2", 1.0×1.5 mm, 0.3 mm gap). Alternatives: `…_Open_RoundedPad1.0x1.5mm` and `…_Open_TrianglePad1.0x1.5mm`. On perfboard, two adjacent holes (`PinHeader_1x02_P2.54mm_Vertical`) bridged with solder do the same job | VERIFIED |
| 10 | EXT pads (6 at 2.54 mm pitch) | J | `Connector_Generic:Conn_01x06` (pins 1..6 = `Pin_1`..`Pin_6`) | `Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical` (pad 1 is square, 1.0 mm drill) | VERIFIED |
| 11 | JST-XH 6-pin locking connector (a LiPo balance lead cut in half; cable-to-cable) | J | `Connector_Generic:Conn_01x06`. Optionally show the gender with `Connector:Conn_01x06_Pin` / `Connector:Conn_01x06_Socket` | Cable-to-cable: Excl. board. If board-mounted: `Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical` (top entry) or `Connector_JST:JST_XH_S6B-XH-A_1x06_P2.50mm_Horizontal` (side entry). **Pitch is 2.50 mm, not 2.54** | VERIFIED |
| 12 | Sensor ribbon, 14 wires (1.27 mm flat cable, EUNSUNG 2651-16P cut to 14) | J | `Connector_Generic:Conn_01x14` on each board (sensor side and control side) | For wires splayed onto 2.54 mm pads: `Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical`. For direct 1.27 mm soldering: `Connector_PinHeader_1.27mm:PinHeader_1x14_P1.27mm_Vertical`. PCB option: keep all 16 wires and use `Connector_Generic:Conn_02x08_Odd_Even` + `Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical`. With Odd_Even numbering, ribbon wire n = pin n. **Check the v4 keep-out: the header must sit at x ≤ 81.42** | VERIFIED |
| 13 | 3.5 mm stereo jack with switched T and R contacts (PJ-313 ×3: headphone, pedal, amp input) | J | `Connector_Audio:AudioJack3_SwitchTR` (pin table in §2.4) | No PJ-313 in the library. Make a custom `Toccata:Jack_3.5mm_PJ-313` whose **pads are named `S`, `T`, `TN`, `R`, `RN`**. `Connector_Audio:Jack_3.5mm_CUI_SJ1-3525N_Horizontal` already uses those names and can serve as a placeholder or template. For the pedal jack, use the same symbol and put no-connect flags on TN and RN | VERIFIED (lib); PJ-313 pinout = **MEASURE** |
| 14 | 3.5 mm plugs (dongle cable, pedal cable) | P | `Connector_Audio:AudioPlug3` (pins `T`, `R`, `S`) | Excl. board | VERIFIED |
| 15 | Fuse 5 A slow-blow 5×20 mm (Littelfuse 0218005.MXP) in a Coms BU914 inline holder | F | `Device:Fuse` (pins 1, 2) | Inline holder, so Excl. board. On-board alternatives: `Fuse:Fuseholder_Clip-5x20mm_Littelfuse_111_Inline_P20.00x5.00mm_D1.05mm_Horizontal`, `Fuse:Fuseholder_Cylinder-5x20mm_Schurter_FAB_0031-355x_Horizontal_Closed` | VERIFIED |
| 16 | Rocker switch KCD1-101A (SPST, 2 pins) | SW | `Switch:SW_SPST` (pin 1 = A, pin 2 = B) | Panel-mounted, so Excl. board. If wires land on a PCB: `Connector_Wire:SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm` | VERIFIED |
| 17 | Speakers (삼미 CW-100B25, 8 Ω, ×2) | LS | `Device:Speaker` (pins 1, 2; no + mark on the symbol, so treat pin 1 as + and add a "+" text) | Excl. board | VERIFIED |
| 18 | XT30U-M (amp side) / XT30U-F (speaker side) | J | `Connector:Conn_01x02_Pin` (male) / `Connector:Conn_01x02_Socket` (female), or `Connector_Generic:Conn_01x02` | `Connector_AMASS:AMASS_XT30U-M_1x02_P5.0mm_Vertical` / `Connector_AMASS:AMASS_XT30U-F_1x02_P5.0mm_Vertical` (5.0 mm pitch, 2.7 mm drill). **Pad 1 = "−", pad 2 = "+"** per the silkscreen. These are wire-mounted here, so Excl. board. The amp outputs are bridge-tied (BTL): "−" is the amp's OUT−, **not GND** | VERIFIED |
| 19 | USB-C power-only receptacle (the HUSB238 trigger module's input) | J | `Connector:USB_C_Receptacle_PowerOnly_6P` | It sits on the module, so Excl. board (or draw it inside the module symbol). On-board option: `Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal` (pads A5, A9, A12, B5, B9, B12, S1) | VERIFIED |
| 20 | Barrel jack: the hub's DC input, fed by the plug end of the hub's cut adapter cable | J | `Connector:Barrel_Jack` (pin 1 = centre pin, pin 2 = sleeve; the symbol draws pin 1 at the top). If the 3rd sleeve-switch pin matters: `Connector:Barrel_Jack_Switch` | It is the hub's own jack, so Excl. board. Standard footprint: `Connector_BarrelJack:BarrelJack_Horizontal` (pads 1, 2, 3). **MEASURE: confirm centre-positive on the hub adapter** | VERIFIED names; the centre = pin 1 convention is high confidence |
| 21 | Pi 5 power lead (MAXTEK MT666, 2-wire USB-C male) | P | `Connector:USB_C_Plug_USB2.0` with only VBUS (A4) and GND (A1) wired, or simply `Connector_Generic:Conn_01x02` labelled "USB-C plug (VBUS, GND)" | Excl. board | VERIFIED |
| 22 | Power rails | #PWR | `power:+3V3`, `power:GND`, `power:+5V` exist. There is no `+20V` or `+5V1` (the library has +12V, +15V, +24V, +28V…). Either use `power:VCC` / `power:+VDC` and set Value to `+20V` / `+5V1`, or add them to the project library `Toccata_power` (copy `+24V`, rename) | n/a | VERIFIED |
| 23 | Power flag | #FLG | `power:PWR_FLAG` (pin 1 is power_out) | n/a | VERIFIED |
| 24 | M3 mounting hole | H | `Mechanical:MountingHole` (no pins) | `MountingHole:MountingHole_3.2mm_M3` (NPTH, 3.2 mm). For a grounded hole: `Mechanical:MountingHole_Pad` + `MountingHole:MountingHole_3.2mm_M3_Pad_Via` | VERIFIED |
| 25 | Wire pads, general | TP or J | `Connector_Generic:Conn_01xNN`, or `Connector:TestPoint` | `TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm`, `Connector_Wire:SolderWire-0.25sqmm_1x02_P4.2mm_D0.65mm_OD1.7mm` | VERIFIED |
| 26 | Modules: Pi 5, NEXTU 710U3 hub, HUSB238 PD trigger, XL4016 buck, XH-A232 (TPA3110) amp, Apple USB-C dongle | A | Custom symbols in the project library `Toccata.kicad_sym` (a box with its terminals, e.g. XL4016 IN+, IN−, OUT+, OUT−) | Excl. board | Suggested approach |

---

## 2. Pin tables

### 2.1 DRV5055, TO-92 "LPG" (TI datasheet SBAS640C, Table 4-1; KiCad symbol matches)

| Pin | Name | KiCad pin type | Toccata net |
|---|---|---|---|
| 1 | VCC | power_in | +3V3 (100 nF 1206 to GND right at the pin; TI says "at least 0.01 µF") |
| 2 | GND | power_in | GND |
| 3 | OUT | output | KEY_x → ribbon → MUX Cn |

The SOT-23 "DBZ" package (`DRV5055A2xDBZxQ1`, `Package_TO_SOT_SMD:SOT-23`) is different: **1 = VCC, 2 = OUT, 3 = GND**.

The LPG lead pitch is 1.27 mm (TI package drawing LPG0003A).

### 2.2 RP2040-Zero

Physical layout, from the Waveshare pinout and dimension drawings, top view, USB-C at the top:

| Edge | Pads, in order |
|---|---|
| Left edge, top → bottom | 5V, GND, 3V3, GP29, GP28, GP27, GP26, GP15, GP14 |
| Right edge, top → bottom | GP0 … GP8 |
| Bottom edge, left → right | GP13, GP12, GP11, GP10, GP9 |
| Underside pads | GP17–GP25 + GND |

- GP16 drives the on-board WS2812 LED and has no pad.
- Board size 18.00 × 23.50 mm, pad pitch 2.54 mm.
- The first side pad centre is 1.59 mm below the top edge.
- The GP9 pad centre is 3.92 mm from the right edge.
- On a PCB, keep exposed copper and vias away from the underside pads (the v3 build used Kapton for this).

The Waveshare schematic header P1 (1..23) numbers the pads differently from dj505. Both numberings are valid, but the symbol and footprint must use the same one. The dj505 numbering was verified: its symbol and footprint pad positions match the physical layout above.

Only the pins Toccata uses are listed:

| Signal (Toccata) | Pad | dj505 pin # | Waveshare P1 pin # |
|---|---|---|---|
| 5V (VBUS/VSYS) | left 1 | 1 | 23 ("VSYS") |
| GND | left 2 | 2 | 22 |
| 3V3 (on-board regulator OUTPUT) | left 3 | 3 | 21 |
| GP27 (pedal bias drive) | left 6 | 6 | 18 |
| GP26 / ADC0 (mux SIG, pedal in) | left 7 | 7 | 17 |
| GP14 (PED detect) | left 9 | 9 | 15 |
| GP2 → MUX S0 | right 3 | 12 | 3 |
| GP3 → MUX S1 | right 4 | 13 | 4 |
| GP4 → MUX S2 | right 5 | 14 | 5 |
| GP5 → MUX S3 | right 6 | 15 | 6 |
| GP6 = ID0 | right 7 | 16 | 7 |
| GP7 = ID1 | right 8 | 17 | 8 |
| GP8 = ID2 | right 9 | 18 | 9 |

Full dj505 numbering:

| dj505 pins | Signals |
|---|---|
| 1–9 | 5V, GND, 3V3, GP29, GP28, GP27, GP26, GP15, GP14 |
| 10–18 | GP0 … GP8 |
| 19–23 | GP13, GP12, GP11, GP10, GP9 |

Footprint check (dj505): the side columns are at x = 2.54 and 17.78 (15.24 apart), and the bottom row is at x = 5.08 … 15.24 on the same row as the last side pads. The outline is about 18.3 × 23.9 mm.

Two edits to make to the dj505 symbol:
- It marks 5V, GND and 3V3 as `power_in`. Either change **3V3 to `power_out`** (the pin really is the regulator output), or place `PWR_FLAG` on +3V3 and GND. Otherwise ERC reports "Input Power pin not driven".
- Put the used GPIO names first, e.g. `GP26/ADC0`.

### 2.3 CD74HC4067 breakout module (PP-A324, from the seller's photos)

Seen from the top (chip side up) with the channel row at the bottom, both rows read left → right:
- Control row (8 pins): `SIG, S3, S2, S1, S0, EN, VCC, GND`. The GND pad is square.
- Channel row (16 pins): `C15, C14, …, C1, C0`.
- Board size 41 × 18 mm.

Suggested custom symbol numbering, in the same reading order:

| Pins | Signals |
|---|---|
| 1–8 | SIG, S3, S2, S1, S0, EN, VCC, GND |
| 9–24 | C15 … C0 |

EN is active-low; tie it to GND.

For reference, the chip `74xx:CD74HC4067M/SM`:

| Pins | Signals |
|---|---|
| 1 | COM (the module's SIG) |
| 2–9 | I7 … I0 |
| 10 | S0 |
| 11 | S1 |
| 12 | GND |
| 13 | S3 |
| 14 | S2 |
| 15 | ~E |
| 16–23 | I15 … I8 |
| 24 | VCC |

### 2.4 `Connector_Audio:AudioJack3_SwitchTR` (the pin NUMBER is the letter; the pin name is `~`)

| Pin number | Meaning | Toccata headphone jack (#1, left cheek) | Toccata amp-input jack (#3) | Pedal jack (#2) |
|---|---|---|---|---|
| T | Tip (L) | dongle L in | cable-2 L | pedal sensor OUT → 1 kΩ → GP26 |
| TN | Tip normal (closed to T when no plug) | → amp L (via cable 2) | — (no-connect) | no-connect |
| R | Ring (R) | dongle R in | cable-2 R | 3V3 (via 0 Ω) |
| RN | Ring normal | → amp R | — | no-connect |
| S | Sleeve | GND | GND | GND |

The PJ-313 name is used by several vendors (BSUN at eleparts; SHOUHAN "PJ-313 5JCJ", LCSC C668607), and their 1..5 pin numbering differs. **Map it by continuity test:**
1. Plug inserted: find the pins that connect to the plug's T, R and S.
2. No plug: find the pins that are closed to T and to R. Those are TN and RN.

Then name the custom footprint's pads `T`, `TN`, `R`, `RN`, `S`.

### 2.5 Other pin notes
- `Device:R`, `Device:C`, `Device:Fuse`: pins 1 and 2, passive.
- `Device:C_Polarized`: pin 1 = +.
- `Switch:SW_SPST` and `Jumper:SolderJumper_2_Open`: pins 1 and 2, named A and B.
- `Connector_Generic:Conn_01xNN`: pin n is named `Pin_n`.
- `Connector:USB_C_Receptacle_PowerOnly_6P`:
  - A9 VBUS (B9 VBUS hidden)
  - A12 GND (B12 GND hidden)
  - A5 CC1, B5 CC2
  - S1 SHIELD
- `Connector:USB_C_Plug_USB2.0`:
  - A4 VBUS (A9, B4, B9 hidden)
  - A1 GND (A12, B1, B12 hidden)
  - A5 CC, B5 VCONN, A6 D+, A7 D−
  - S1 SHIELD
- `Connector:Barrel_Jack`: pin 1 = centre, pin 2 = sleeve.
- `Device:Speaker`: pins 1 and 2.

---

## 3. Annotation scheme for a multi-sheet project

**Settings.** In Tools → Annotate Schematic:
- Numbering = "**First free after sheet number × 100**".
- Order = "Sort symbols by **X** position", so that sensors numbered left to right follow key order.
- Auto-annotation is under Preferences → Schematic Editor → Annotation Options.
- Set sheet page numbers with Edit → *Edit Sheet Page Number…* or in the Hierarchy Navigator.

The ×100 rule is safe while no single sheet has more than 99 parts of one letter. An octave sheet has at most about 14 U and 14 C.

**Suggested system (documentation) project, e.g. `pcb/toccata-system/`:**

| Page | Sheet file | Instances (sheet name) | Ref ranges |
|---|---|---|---|
| 1 | root `toccata-system.kicad_sch` | block diagram, USB topology, sheet symbols | 1xx |
| 2–8 | `octave.kicad_sch` (**same file, reused 7×**) | O1 … O7 | O1 = U201…, R201…, JP201…; … O7 = U801… |
| 9 | `end_parts.kicad_sch` | END (left A0/A#0/B0 + right C8) | 9xx |
| 10 | `ped.kicad_sch` | PED | 10xx |
| 11 | `cu_power.kicad_sch` | CU power | 11xx |
| 12 | `cu_audio.kicad_sch` | CU audio | 12xx |

Suggested order inside `octave.kicad_sch`:
- U1–U12 = sensors C … B, which become U201–U212 on O1.
- U13 = RP2040-Zero, U14 = mux module.
- C1–C12 = per-sensor 100 nF, C13–C14 = 10 µF.
- JP1–JP3 = ID0–ID2, JP4 = PED detect.
- J1 = ribbon, J2 = EXT.

**Reusing one sheet 7 times.** Place 7 hierarchical sheet symbols that all use the file name `octave.kicad_sch`. The manual says "the circuit drawn in the sheet will be instantiated once per usage, and any edits in one instance will be reflected in the other instances".
- Each instance keeps its own reference designators, stored per instance in the file.
- Each instance has its own page number.
- Local labels become path-qualified per instance (`/O1/KEY_C`).
- Connect to the parent with hierarchical labels (EXT1..4, USB).

**Caveats for reused sheets:**
1. **Power symbols are global.** A `power:+3V3` inside `octave.kicad_sch` joins all 7 boards' separate RP2040-Zero 3V3 rails (plus the PED and end-part rails) into one net. GND really is common, through USB.
   - For a documentation schematic, either accept this and add a note, or use a local label `3V3` inside the octave sheet. That works best when the RP2040-Zero symbol's 3V3 pin is `power_out`, so ERC is satisfied.
   - KiCad 10 adds a "Define as local power symbol" option, which gives a sheet-local power symbol.
2. **Per-board differences cannot differ between instances in KiCad ≤ 9.** These are the ID bridges (O1 = 001 … O7 = 111) and the EXT connector, which is fitted only on O1 and O7.
   - Keep all JPs "open" and add a text table "Bridge JP1/JP2/JP3 per board".
   - KiCad 10 "design variants" store variant data per symbol instance, so the same symbol in different places of a hierarchy can have different DNP/field overrides.
3. **One PCB per project.** The 7 octave boards are one physical design built 7 times, and the sensor and control boards are separate boards joined by a ribbon. For real PCBs, make separate projects, each annotated from 1 with power symbols used normally:
   - `pcb/octave-sensor/` (order 7; the end parts can stay perfboard)
   - `pcb/octave-control/` (order 8: 7 octaves + PED). The PED input parts (jack header, 1 kΩ, 100 kΩ, 100 nF) can be DNP on octave boards. In KiCad 10 that becomes a "PED" variant.

   Do not place the reused system sheet into a single PCB. It would drop 7 copies of every footprint onto one board.

   If both boards are ever panelled in one PCB file, model the ribbon as an "Exclude from board" cable symbol with separate nets on each side. Otherwise ratsnest and DRC report the ribbon wires as unrouted.
4. **ERC flags.** Place `PWR_FLAG` on nets that no power_out pin drives:
   - +20V (PD module output)
   - +5V1 (XL4016 output)
   - +3V3 on the sensor-board project (it arrives over the ribbon)
   - GND in every project

   The manual says PWR_FLAG marks "a power net that is supplied by an off-board connector".
5. **Custom power nets.** If you use the Value-edited `power:VCC` trick for `+20V` / `+5V1`, the "Update Symbols from Library" dialog has a "Reset custom power symbols" checkbox. Leave it unchecked. Otherwise the Values revert and the nets are renamed. A project library `Toccata_power` avoids this problem.

KiCad 9 also has "Repeat layout" tools (placement rule areas) for multi-channel copies on one PCB, and schematic design blocks. Neither is needed here, since each octave is its own PCB.

---

## 4. Open items to verify on the real parts
- PJ-313 pin numbering to S/T/TN/R/RN (vendor-dependent): continuity test.
- CD74HC4067 module: row-to-row spacing and the X offset of the 8-pin row (calipers). Does the module already pull EN up or down?
- RP2040-Zero: print the chosen footprint 1:1 and lay the module on it. Also check the clone's outline (PP-A799-2 is sold as a "RP2040-ZERO" clone).
- 1 µF leaded MLCC lead spacing (2.54 vs 5.08 mm).
- Hub DC-plug polarity and size, and JST-XH pin 1 on the balance lead (the wire colours are not a reliable guide).

---

## Sources
- KiCad symbols (tags 9.0.9.1 / 8.0.9 / 10.0.6): https://gitlab.com/kicad/libraries/kicad-symbols
- KiCad footprints (tags 9.0.9.1 / 8.0.9 / 10.0.6): https://gitlab.com/kicad/libraries/kicad-footprints
- KiCad 9 Schematic Editor manual (annotation, power symbols, PWR_FLAG, sheet reuse, Exclude from board): https://docs.kicad.org/9.0/en/eeschema/eeschema.html
- KiCad 10 Schematic Editor manual (local power symbols, design variants): https://docs.kicad.org/10.0/en/eeschema/eeschema.html
- KiCad 9.0.0 release notes (multi-channel, design blocks): https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/
- KiCad 10.0.0 release notes (design variants): https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/
- TI DRV5055 datasheet SBAS640C (pin table, LPG0003A package): https://www.ti.com/lit/ds/symlink/drv5055.pdf
- TI CD74HC4067 datasheet: https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf
- Waveshare RP2040-Zero wiki (pinout, dimensions): https://www.waveshare.com/wiki/RP2040-Zero ; schematic: https://files.waveshare.com/upload/4/4c/RP2040_Zero.pdf
- dj505 RP2040-Zero KiCad library (CERN-OHL-P-2.0): https://github.com/dj505/RP2040-Zero-KiCAD
- CountParadox RP2040-Zero library (README warns the footprint is wrong): https://github.com/CountParadox/RP2040-Zero-Kicad
- parts-parts PP-A324 mux module (photos, 41×18 mm): https://parts-parts.co.kr/product/pp-a324-16%EC%B1%84%EB%84%90-%EC%95%84%EB%82%A0%EB%A1%9C%EA%B7%B8%EB%94%94%EC%A7%80%ED%84%B8-%EB%A9%80%ED%8B%B0%ED%94%8C%EB%A0%89%EC%84%9C-%EB%AA%A8%EB%93%88/303/
- parts-parts PP-A799-2 RP2040-Zero: https://parts-parts.co.kr/product/detail.html?product_no=2383
- SHOUHAN PJ-313 5JCJ (LCSC C668607) drawing: https://www.lcsc.com/product-detail/C668607.html
- eleparts BSUN PJ-313 (no datasheet on the page): https://www.eleparts.co.kr/goods/view?no=67811
