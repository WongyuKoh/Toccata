# Hall sensor, capacitors, XH balance lead, 2651 ribbon: verified facts for the KiCad schematic

Research date 2026-09-28. Primary sources: the TI DRV5055 datasheet SBAS640**C** (revised June 2026), an older copy SBAS640**A** (June 2020), the DRV5053 datasheet (for TI's LPG marking figure), the Samsung spec sheet, the JST XH catalog, the EUNSUNG 2651 datasheet (the PDF linked on the eleparts product page), and the rcbank and eleparts product pages and photos. The local KiCad `Sensor_Magnetic.kicad_sym` was checked as well.

---

## 1. TI DRV5055A2QLPG (TO-92, TI package code LPG0003A)

### 1.1 Pinout (confirmed)

| Pin | Name | Type | Net on sensor board |
|---|---|---|---|
| 1 | VCC | power in | +3V3 bus (row y64.46) |
| 2 | GND | ground | GND bus (row y67.00) |
| 3 | OUT | analog output | OUT_x (row y69.54) → ribbon |

- Source: datasheet Table 4-1, TO-92 column: VCC = 1, GND = 2, OUT = 3. The SOT-23 part uses a different order (VCC 1, OUT 2, GND 3), so do not reuse a SOT-23 symbol.
- KiCad: the official library has `Sensor_Magnetic:DRV5055A2xLPGxQ1`, which has the same pins (1 VCC power_in, 2 GND power_in, 3 OUT output) and the footprint `Package_TO_SOT_THT:TO-92_Inline` (1.27 mm pitch). Use this symbol and set the Value to `DRV5055A2QLPG`. The symbol's description says "50 mV/mT, ±42 mT", but those are the **5 V** figures. At 3.3 V the numbers are in section 1.2.
- On a 2.54 mm perfboard or PCB, use a 2.54 mm pitch footprint. Examples: `TO-92_Inline_Wide`, if your KiCad version has it, or a 1×03 2.54 mm pad footprint. Pin 1 must stay VCC.

### 1.2 Which face is the "top" / branded face, and the orientation rule

- TI's LPG body has a **flat face** and a face with **two 45° chamfered edges**. TI marks the chamfered face. The DRV5053 datasheet, Fig. 19 "TO-92 (LPG) Package", labels this face "Marked Side Front", and its bottom view puts the "Marked Side" on the chamfered edge. In the DRV5055 datasheet, the "Top View" in Fig. 4-2, the package outline, and the side view in Fig. 6-5 show the same geometry.
- The DRV5055 datasheet (6.3.1) calls this marked face the **"top (marked-side)"** of the package. The sensor measures flux perpendicular to this face. **B is positive, so OUT rises above VCC/2, when a SOUTH pole faces the marked face.**
- **Orientation rule:** hold the part with the marked (printed "55A2", chamfered) face toward you and the leads pointing down. Then **pin 1 VCC is on the left, pin 2 GND is in the middle and pin 3 OUT is on the right.** Looking at the flat back face instead, pin 1 is on the right.
- Lying flat, marked face up (the BOM already says "표시면을 위로 눕혀"), viewed from above:
  - leads pointing to your **right** → pin 1 (VCC) is the lead **nearest you** and pin 3 (OUT) the farthest.
  - leads pointing to your **left** → pin 1 is the **farthest** lead.
  Map this to the board's y-axis direction before you bend the leads. If in doubt, run the magnet test below.
- **Bench check (recommended, one part):** power the part at 3.3 V. With no magnet, OUT should read 1.59–1.71 V. Bring the S pole of a magnet toward the printed face: OUT should **rise**. If OUT falls, you are facing the N pole or the back face.
- Hall element position (from Fig. 6-5): centred across the width (2 mm from each side, ±50 µm), 1.54 mm below the top edge of the body (1.61 mm above the edge where the leads exit), and **1.03 ± 0.115 mm from the flat back face**. The body is 1.42–1.62 mm thick, so the element sits **about 0.4–0.6 mm below the marked face**. Mounting marked face up puts the element about 0.5 mm closer to the magnet than mounting it flat face up.
- Body dimensions (LPG0003A): 3.9–4.1 mm wide, 3.05–3.25 mm tall, 1.42–1.62 mm thick. The narrow width of the chamfered face is 2.28–2.68 mm. Lead pitch is 1.27 ± 0.05 mm. Leads are 0.35–0.48 × 0.36–0.51 mm and 15.1–15.5 mm long, with a wider dambar section about 0.8 mm below the body. Bend the leads below that section, not at the body.

### 1.3 Electrical and magnetic specs at VCC = 3.3 V (Rev C, June 2026, unless noted)

| Parameter | Value |
|---|---|
| Recommended VCC | **3.0 – 3.63 V** (a separate 4.5 – 5.5 V window also exists; between 3.63 and 4.5 V the sensitivity is "less known") |
| Absolute max | VCC −0.3 … 7 V; OUT −0.3 … VCC+0.3 V; ESD HBM ±2.5 kV, CDM ±750 V |
| Sensitivity A2 @3.3 V, 25 °C | **28.5 / 30 / 31.5 mV/mT** (min/typ/max). At 5 V it is 47.5 / 50 / 52.5 |
| Linear range B_L (A2 @3.3 V) | **±44 mT** (minimum guaranteed; ±42 mT at 5 V) |
| Linear output range V_L | 0.2 V … VCC − 0.2 V (0.2 … 3.1 V). Outside this range the output compresses |
| Quiescent V_Q (B = 0) @3.3 V | **1.59 / 1.65 / 1.71 V**; temperature drift ±1 % of VCC; ratiometric error ±0.2 % |
| Sensitivity temperature coefficient (A versions) | +0.12 %/°C typ (compensates NdFeB magnets) |
| Supply current I_CC @3.3 V, B = 0 | **Rev C (2026): 2 mA typ, 4 mA max.** Rev A/B (2020/21): 6 mA typ, 10 mA max (not split by VCC). Budget with **10 mA** to be safe |
| Output drive | **±1 mA continuous** (recommended operating conditions) |
| Bandwidth / delay | 20 kHz; propagation delay 10 µs |
| Noise @3.3 V | 215 nT/√Hz; 0.2 mT p-p input-referred; **6 mV p-p output-referred for A2** (full bandwidth) |
| Power-on time t_ON | Rev A: **175 µs typ, 330 µs max** (from VCC crossing 3 V until OUT is within 5 % of V_Q, no load). Rev C keeps the definition (6.3.7) but no longer prints a number. Use "wait ≥ 1 ms" in firmware |
| θJA (TO-92) | 121 °C/W (self-heating is negligible: 3.3 V × 4 mA = 13 mW) |

### 1.4 Output loading, RC filter, short circuit

- TI (7.1.3): "Do not connect a capacitor directly to the device output without a resistor in between because doing so can make the output unstable." **No maximum load capacitance is published** in Rev A or Rev C. The only output limit given is I_O = ±1 mA.
- Implications for this design:
  - The mux input, the 180 mm ribbon (a few pF per conductor) and the RP2040 ADC input add only pF-level loading. This is normal practice and needs nothing extra.
  - An optional noise filter must be **series R, then C to GND**, for example 1 kΩ + 10–47 nF at each mux input (fc ≈ 3.4–16 kHz). Never put a bare C on OUT.
  - **Pedal (PED): caution.** The 3 m 3.5 mm cable puts roughly several hundred pF (typical for audio cable, not measured) directly on OUT at the pedal end. The planned 1 kΩ + 100 nF sits at the jack end, after the cable. **Recommendation:** add a 470 Ω – 1 kΩ series resistor at the DRV5055 OUT pin inside the pedal, before the cable. This is an engineering judgement based on TI's warning, not a TI number.
- Short circuit: the datasheet gives **no short-circuit protection or current-limit spec**. Table 7-1 lists "VCC shorts to OUT" and "GND shorts to OUT" only as faults that can be detected. Treat OUT as unprotected. Shorting it to GND or VCC probably survives briefly, but nothing guarantees it. Applying a voltage to OUT while VCC = 0 exceeds the absolute maximum (OUT ≤ VCC + 0.3 V).
  - **TRS hot-plug (PED):** inserting a 3.5 mm plug slides the plug TIP (sensor OUT) past the jack's SLEEVE (GND) and RING (3V3) contacts. The TIP can therefore see 3V3 while the sensor's VCC is not yet connected. It can also briefly bridge RING to SLEEVE, which shorts 3V3 to GND. The series resistor at OUT (above) limits the current into OUT. A **10 Ω resistor in the RING 3V3 feed** limits a momentary 3V3–GND bridge to about 330 mA, which keeps the PED board's 500 mA LDO from browning out. The drop calculation is in 1.6.
- Wire-break detection (optional, TI 7.1.4): a 20–100 kΩ pull-up from OUT to VCC, then treat a reading within 150 mV of a rail as a fault. The planned 100 kΩ to GP27 on the PED board is a similar idea. Its load is at most about 33 µA, well inside ±1 mA.

### 1.5 Bypass capacitor: value and placement

- TI: "ceramic capacitor with a value of at least 0.01 µF" from VCC to GND, placed "close to the device … minimal inductance" (7.4). The layout example in Fig. 7-5 puts the capacitor directly across the VCC and GND pads.
- Plan: 100 nF 1206 (CL31B104KCFNNNE), which is 10× the minimum. **Put one per sensor on the bottom side, bridging the pin-1 (y64.46) and pin-2 (y67.00) pads at that sensor's x position.** A 1206 (3.2 mm long, 0.5 mm terminations) sits well across two adjacent 2.54 mm perfboard pads. Keep the loop under about 5 mm. On a PCB, place C next to pins 1 and 2 with a short GND return.
- Add bulk capacitance on the 3V3 bus: 10 µF at the ribbon entry and 10 µF at the far end of the bus (parts in section 3).

### 1.6 Is a series resistor in VCC OK?

- Available headroom: the RP2040-Zero 3V3 comes from an LDO. The Waveshare schematic shows an RT9013-33 (500 mA, ±2 %); the product page says ME6217C33 (800 mA). Worst-case low output is about 3.23 V. The ribbon adds 2 × 0.040 Ω (224 Ω/km × 0.18 m, supply and return). At 15 sensors × 10 mA this drops about 12 mV, so the bus is ≥ about 3.22 V. The DRV5055 needs ≥ 3.0 V.
- Maximum per-sensor series R = (3.22 − 3.0) / I_CC,max = **about 22 Ω if you assume the older 10 mA maximum, about 55 Ω with the Rev C 4 mA maximum.**
- Recommendation: **sensor board: 0 Ω (direct bus)**. A per-sensor R ≤ 10 Ω is allowed but buys almost no filtering (10 Ω with 100 nF gives fc ≈ 160 kHz). If you want supply filtering, one ferrite bead (DCR < 0.5 Ω) at the ribbon entry is fine.
- **PED ring feed:** 0 Ω is OK. **10 Ω** is better for hot-plug. It drops 40 mV at 4 mA and 100 mV at 10 mA, leaving ≥ 3.12 V. The 3 m cable resistance is negligible, about 1 Ω loop. Do not use more than 22 Ω.
- Ratiometric note: any drop in VCC shifts V_Q and sensitivity relative to the ADC reference (the RP2040 3V3). A 40 mV drop is about 1.2 %, which per-key or boot calibration removes.
- Current budget per octave board: 12 × 2–4 mA = 24–48 mA by Rev C (up to 120 mA with the old 10 mA maximum). O1 has 15 sensors: 30–60 mA (up to 150 mA). All of these are well inside the LDO rating.

---

## 2. Samsung CL31B104KCFNNNE (confirmed from the Samsung spec sheet)

- 100 nF, ±10 % (K), **100 V**, **X7R** (−55 to 125 °C, ΔC ≤ ±15 %), 1206 / 3216 metric.
- Size: L 3.20 ± 0.15 × W 1.60 ± 0.15 × **T 1.25 ± 0.15 mm**; termination band 0.50 ± 0.30 mm; Ni/Sn 100 % plating; DF ≤ 0.025.
- Part-code breakdown: CL (series), 31 (1206), B (X7R), 104 (100 nF), K (±10 %), C (100 V), F (thickness 1.25 mm), N/N/N, E (7" embossed reel).
- At 3.3 V the DC-bias loss on a 100 V X7R 1206 is negligible.
- Seller: icbanq P014968846, 40 won (44 won incl. VAT) per piece, minimum order 1, overseas stock, about 1 week.
- KiCad: `Device:C`, footprint `Capacitor_SMD:C_1206_3216Metric`. Non-polarised; pin 1 and pin 2 are interchangeable.

---

## 3. 10 µF bulk capacitor for the 3.3 V bus (2 per sensor board, plus spares)

| Option | Part / seller | Price checked 2026-09-28 | Notes |
|---|---|---|---|
| **A (recommended, same shop as the sensors)** | icbanq **P001248090** "C3216-10UF(K 16V)-50개 단위" | 7,150 won incl. VAT for 50 pcs, ships in 1–2 days | 1206, 10 µF ±10 %, 16 V. Brand ("Any vendor") and dielectric not stated (likely X5R). Solders across two 2.54 mm pads like the 100 nF. At 3.3 V on a 16 V part expect about 7–9 µF effective, which is fine |
| A' (named brand) | icbanq **P008153296** "CC3216-10UF50V(±10%/X5R)" | 18,623 won / 100 pcs, about 1 week | 1206 X5R 50 V; less DC-bias loss |
| B (named brand, single pieces) | eleparts **no=2684677** Taiyo Yuden **TMK316BJ106KL-T** | 566 won/pc incl. VAT, 29k in stock (overseas, about 4.5 days) | 1206, 10 µF ±10 %, 25 V, X5R |
| C (THT alternative) | eleparts **no=7451908** SamYoung **KMG 25V10 5×11** | 78 won/pc, pack of 20; **out of stock** when checked | Radial electrolytic, 2.0 mm lead spacing, 105 °C. **Polarised:** mark + to 3V3 in the schematic |
| (reel only) | icbanq P012677075 CL31A106KBHNNNE (1 REEL) | 66,000 won / 2,000 pcs | too many parts |

KiCad: `Device:C` + `C_1206_3216Metric` for A, A' and B, or `Device:C_Polarized` + `CP_Radial_D5.0mm_P2.00mm` for C. The RP2040-Zero's LDO (RT9013 or ME6217) is specified as stable with ceramic output capacitors, so about 21 µF of MLCC at the end of the ribbon is fine.

---

## 4. JST-XH 6-pin 5S balance extension (rcbank goodsno=29812, "BU-LP 5S", 200 mm)

- Seller page: 3,000 won; **22 AWG silicone wire, 200 mm**; one end is a white XHP-type housing (socket contacts) and the other is a heat-shrink-covered pin housing (the "male" end that accepts a battery plug). The seller warns the heat-shrink sometimes overhangs the face and should be trimmed with a knife.
- **Wire colours (from the seller photo of the 5S version): 1 red + 5 black.** The red wire is on one edge and every other wire is black, so wires can only be identified by position.
- LiPo convention: the black edge wire is the pack negative (tap 0, called "pin 1") and the wire on the other edge is pack positive (on this lead, the red one).
- JST XH facts (JST catalog): **pitch 2.50 mm** (not 2.54), 3 A with AWG 22, 250 V, AWG 30–22 wire, contacts SXH-001T-P0.6. The genuine XHP housing has a moulded **"Circuit No.1 mark"** next to circuit 1. Clone balance housings may lack this mark, so use the red wire as the reference edge.
- The halves are held by friction/lock ramp only. The balance-extension pin housing is not a latching header, so tape the mated pair or cable-tie it to a strain-relief point.
- **Suggested J_EXT numbering for the schematic** (position counted from the black edge opposite red):

| Pos | Wire | Net | Left end part (A0, A#0, B0) | Right end part (C8) |
|---|---|---|---|---|
| 1 | black (edge) | GND | used | used |
| 2 | black | EXT1 → mux ch12 | A0 | C8 |
| 3 | black | EXT2 → mux ch13 | A#0 | NC |
| 4 | black | EXT3 → mux ch14 | B0 | NC |
| 5 | black | EXT4 → mux ch15 | NC (spare) | NC |
| 6 | red (edge) | +3V3 | used | used |

  The brief's EXT pad order is 1–4 = ch12–15, 5 = 3V3, 6 = GND. Either re-order the pads to match the table (GND, EXT1–4, 3V3) or record the crossing in the schematic. Pads and wires don't have to match; the net labels do.
- **Procedure:** flag each wire position with numbered tape on both sides of the cut **before** cutting the extension in half. After soldering, mate the halves and beep every position end-to-end with a multimeter. A mated pair passes position 1 to position 1 straight through.
- The board side of this connector is wires soldered to pads, not a header, so the 2.50 vs 2.54 mm pitch mismatch does not matter. A B6B-XH-A header would fit 2.54 mm holes only with a slight squeeze (0.2 mm over 5 pitches).

---

## 5. EUNSUNG 2651-16P flat cable (eleparts no=425, 1,529 won/m)

- **Manufacturer datasheet** (the PDF linked from the eleparts page): UL "2651 AWM", **105 °C, 300 V**, UL Subject 758; **28 AWG, 7/0.127 mm stranded, conductor Ø 0.38 mm**; **pitch 1.27 mm**. The 16-conductor version is 20.32 mm wide (19.05 mm between outer conductors) and 0.89 mm thick. **Max conductor resistance 224 Ω/km** at 20 °C. Insulation is heat-resistant PVC. Standard **red side mark** on conductor 1. Plating is not stated; "TA-SC alloyed" is an option. Dielectric withstand 2,000 VAC for 1 min.
- 180 mm run: 0.040 Ω per conductor. At a 150 mA worst-case bus current the supply and return together drop 12 mV, which is negligible.
- **Soldering 14 of 16 conductors straight to 2.54 mm perfboard: practical.** Doing it neatly takes a method:
  1. Tear off 2 conductors, or keep all 16 and use the extra two as a second 3V3 and a second GND, at no cost.
  2. Split the web with a blade and pull the conductors apart for about 15–20 mm. Strip 1.5–2 mm with a 30 AWG notch or a thermal stripper; the 7 × 0.127 strands nick easily. Twist and pre-tin.
  3. **Easy trick:** 14 × 1.27 mm = 17.78 mm = 7 × 2.54 mm. Put odd conductors (1, 3, 5, …) into row A and even conductors into row B of a **2 × 7 block of 2.54 mm holes**, in column order. This needs no fan-out, and conductor *n* lands on pin *n* of a standard 2 × 7 IDC header. The same schematic symbol (a 2 × 7 2.54 mm header, `Connector_Generic:Conn_02x07_Odd_Even`) then also fits a later upgrade to a box header plus an FC-14P IDC socket, with no netlist change. With 16 conductors, use 2 × 8 and FC-16P.
  4. PVC insulation shrinks back quickly, so keep iron contact short. Anchor the cable with hot-melt glue or a cable tie through spare holes: 28 AWG stranded wire breaks at the solder wick line if it flexes.
  - Effort: 7 boards × 2 ends × 14 conductors = **196 joints**. IDC (2 × 7 box header plus FC-14P, pressed in a vice) is faster and more reliable if you are willing to add those parts. Neither is in the BOM now.
- **Suggested conductor assignment (14C):** 1 (red) = +3V3, 2 = GND, 3–14 = OUT_C, OUT_C#, OUT_D, OUT_D#, OUT_E, OUT_F, OUT_F#, OUT_G, OUT_G#, OUT_A, OUT_A#, OUT_B. Keeping 3V3 and GND adjacent gives the smallest supply-loop inductance. The outputs are low-impedance and slow, so crosstalk is not a concern. **16C variant:** add 15 = GND and 16 = +3V3.

---

## 6. Discrepancies and open points

1. **I_CC:** Rev C (June 2026) gives 2 typ / 4 max mA at 3.3 V; Rev A (2020) gives 6 typ / 10 max mA. The date code of stocked parts is unknown. Budget with 10 mA, or measure one board: 12 sensors should draw about 24–72 mA.
2. **t_ON:** Rev C removed the number and Rev A gives 175 / 330 µs. Firmware should allow ≥ 1 ms after power or after the pedal is plugged in.
3. **Load capacitance:** TI publishes no number, only "never a bare C on OUT". The ≈ several-hundred-pF figure for the 3 m pedal cable is an estimate. The recommended pedal-end series resistor is engineering judgement.
4. **Marked face:** the marked face is the chamfered face. This comes from TI's DRV5053 LPG marking figure together with the DRV5055 drawings; no DRV5055 photo was checked. The magnet test in 1.2 settles it on a real part.
5. The KiCad symbol text "50 mV/mT, ±42 mT" is the 5 V figure. Use 30 mV/mT, ±44 mT for 3.3 V.
6. 10 µF option A is a generic brand with no stated dielectric. If you want a named part, use A' or B.

---

## Sources

- TI DRV5055 datasheet SBAS640C (Jun 2026): https://www.ti.com/lit/ds/symlink/drv5055.pdf (Table 4-1; 5.3–5.6; 6.3.1, 6.3.7, 6.3.8 Fig. 6-5; 7.1.3; 7.1.4; 7.4; 7.5 Fig. 7-5; LPG0003A outline)
- TI DRV5055 SBAS640A (Jun 2020) copy: https://datasheet.sisoog.com/file/zmedia/dex/a218c383b357f72eb48801df33642a07_drv5055.pdf (I_CC 6/10 mA, t_ON 175/330 µs)
- TI DRV5053 datasheet, Fig. 19 LPG "Marked Side": https://cdn.sparkfun.com/assets/3/c/4/0/6/drv5053.pdf
- TI product page: https://www.ti.com/product/DRV5055/part-details/DRV5055A2QLPG
- icbanq DRV5055A2QLPG: https://www.icbanq.com/P018076669
- Samsung CL31B104KCFNNNE spec: https://media.digikey.com/pdf/Data%20Sheets/Samsung%20PDFs/CL31B104KCFNNNE_Spec.pdf ; icbanq https://www.icbanq.com/P014968846
- 10 µF: https://www.icbanq.com/P001248090 , https://www.icbanq.com/P008153296 , https://eleparts.co.kr/goods/view?no=2684677 , https://eleparts.co.kr/goods/view?no=7451908 , https://www.icbanq.com/P012677075
- rcbank 5S balance extension: https://www.rcbank.co.kr/shop/goods/goods_view.php?goodsno=29812 (photos /shop/data/editor/552cf2e1ec635560.jpg, 1fac4c87dfbadf75.jpg)
- JST XH catalog: https://www.jst.com/wp-content/uploads/2021/01/eXH-new.pdf
- LiPo balance-lead convention (black = negative), secondary: https://hobbyking.com/blog/lipo-balance-plug-repair-replace-guide , https://oscarliang.com/fix-balance-plug-lipo-replace/
- EUNSUNG 2651 datasheet: https://www.eleparts.co.kr/data/goods_attach/0/goodpdf4251_1784868576.pdf ; product https://www.eleparts.co.kr/goods/view?no=425
- Waveshare RP2040-Zero (LDO rating): https://www.waveshare.com/rp2040-zero.htm ; schematic https://www.waveshare.com/w/upload/4/4c/RP2040_Zero.pdf
- KiCad library checked locally: scratchpad/research/kicadlib/v8/Sensor_Magnetic.kicad_sym (DRV5055A2xLPGxQ1)
