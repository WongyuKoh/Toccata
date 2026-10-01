# MCU research: RP2040-Zero + CD74HC4067 16-ch mux module

Written 2026-09-28 for the Toccata KiCad schematics. The goal is to get pin names and numbers right.
Working files (images, datasheet text, the SparkFun Eagle files) are in `scratchpad/research/img/`.

Coordinate convention for the footprints: **module-local, component side up, origin = top-left corner of the PCB outline, +x right, +y down (KiCad).** For the RP2040-Zero, "top" is the USB-C edge.

---

## Part 1: Waveshare RP2040-Zero (parts-parts PP-A799-2, product_no=2383)

### 1.1 Genuine or clone?

- **Seller page.** The title is "(PP-A799-2) 라즈베리 파이 피코 PICO RP2040-ZERO", 3,300 KRW. Origin is given as "아시아 중국 OEM". Waveshare is not mentioned anywhere. The page reuses the photo `PP-A799-1.jpg`.
- **Photos.** The layout and silkscreen are 1:1 with Waveshare's, including the "Waveshare" and "RP2040-Zero" text, the pin labels, 10 underside pads, a SOT-23-5 LDO next to USB-C, a USON-8 flash on top and a WS2812 between the buttons. The chip is a genuine RP2040 marked "RP2-B2", so it is B2 silicon.
- **Differences from Waveshare.** The **Waveshare "W®" logo is missing.** On the genuine board it sits between the LED and the GP11/GP10 pads. The flash looks unmarked in the photo. Waveshare's own wiki carries an anti-piracy notice about copies of this board.
- **Verdict.** This is most likely a **layout-identical clone**, or at best grey-market stock. Confidence is medium.
- **The pinout is identical either way:** the silkscreen matches Waveshare pad for pad.
- **Clone risks that don't affect the schematic:**
  - The LDO part is unknown. Measure 3V3 under load.
  - Some clones don't boot after flashing until `PICO_XOSC_STARTUP_DELAY_MULTIPLIER=64` is set. This is a known fix for RP2040-Zero-class boards; add it to the firmware board config anyway.
  - The flash part may differ. The pico-sdk `waveshare_rp2040_zero.h` already uses the conservative `PICO_FLASH_SPI_CLKDIV 4` with 2 MB.
- **Check on arrival.** With USB at the top, the top-left pad must be labelled "5V" and the top-right pad "0". Check the WS2812 colour order: it is GRB on the Waveshare board.

### 1.2 Castellated edge pads, in physical order (23 pads, 2.54 mm pitch)

**Pin numbers.** The table uses the numbering from Waveshare's own schematic (connector **P1, "Header 23"**): pin 1 = GP0 at the top right, going clockwise when viewed from the top. Waveshare's FAQ uses the same numbering ("Pin 21 (the 3V3)", "VSYS … (named Pin23)"). The CountParadox KiCad footprint also uses it.

NuttX documents the opposite direction (pad 1 = 5V, anticlockwise). It describes the same physical pads. **Pick one convention and use it in both the symbol and the footprint.** Waveshare P1 is recommended.

**Column headings:**
- **Hole (x, y)** is the round plated hole inside each pad. Header pins go here.
- **Castellation** is the half-hole on the board edge.

| P1 pin | Name | Side (USB up, top view) | Order on that side | Hole (x, y) mm | Castellation (x, y) mm | Function notes |
|---|---|---|---|---|---|---|
| 1 | GP0 | Right | 1 (top) | 16.62, 1.59 | ≈17.89, 1.59 | UART0 TX default |
| 2 | GP1 | Right | 2 | 16.62, 4.13 | ≈17.89, 4.13 | UART0 RX |
| 3 | GP2 | Right | 3 | 16.62, 6.67 | ≈17.89, 6.67 | Toccata MUX_S0 |
| 4 | GP3 | Right | 4 | 16.62, 9.21 | ≈17.89, 9.21 | Toccata MUX_S1 |
| 5 | GP4 | Right | 5 | 16.62, 11.75 | ≈17.89, 11.75 | Toccata MUX_S2 |
| 6 | GP5 | Right | 6 | 16.62, 14.29 | ≈17.89, 14.29 | Toccata MUX_S3 |
| 7 | GP6 | Right | 7 | 16.62, 16.83 | ≈17.89, 16.83 | Toccata ID0 |
| 8 | GP7 | Right | 8 | 16.62, 19.37 | ≈17.89, 19.37 | Toccata ID1 |
| 9 | GP8 | Right | 9 (bottom) | 16.62, 21.91 | ≈17.89, 21.91 | Toccata ID2 |
| 10 | GP9 | Bottom | 1 (rightmost) | 14.08, 21.91* | 14.08, ≈23.2 | |
| 11 | GP10 | Bottom | 2 | 11.54, 21.91* | 11.54, ≈23.2 | |
| 12 | GP11 | Bottom | 3 (centre) | 9.00, 21.91* | 9.00, ≈23.2 | |
| 13 | GP12 | Bottom | 4 | 6.46, 21.91* | 6.46, ≈23.2 | |
| 14 | GP13 | Bottom | 5 (leftmost) | 3.92, 21.91* | 3.92, ≈23.2 | |
| 15 | GP14 | Left | 9 (bottom) | 1.38, 21.91 | ≈0.11, 21.91 | Toccata PED_DET |
| 16 | GP15 | Left | 8 | 1.38, 19.37 | ≈0.11, 19.37 | |
| 17 | GP26 / ADC0 | Left | 7 | 1.38, 16.83 | ≈0.11, 16.83 | Toccata MUX_SIG (ADC0) |
| 18 | GP27 / ADC1 | Left | 6 | 1.38, 14.29 | ≈0.11, 14.29 | PED: pedal-detect drive |
| 19 | GP28 / ADC2 | Left | 5 | 1.38, 11.75 | ≈0.11, 11.75 | |
| 20 | GP29 / ADC3 | Left | 4 | 1.38, 9.21 | ≈0.11, 9.21 | Free on the Zero (the Pico uses it for VSYS/3) |
| 21 | 3V3 | Left | 3 | 1.38, 6.67 | ≈0.11, 6.67 | RT9013-33 LDO output |
| 22 | GND | Left | 2 | 1.38, 4.13 | ≈0.11, 4.13 | |
| 23 | 5V (= VSYS = VBUS) | Left | 1 (top) | 1.38, 1.59 | ≈0.11, 1.59 | Tied directly to USB-C VBUS; no diode |

\* **Bottom-row hole y.** Waveshare's own footprint image (FAQ, the "10 pads underneath" answer) and the product photo both put the bottom-row holes on the same line as GP14/GP8 (y = 21.91). That puts **all 23 holes on one 2.54 mm grid**: x = 1.38 + 2.54·i, y = 1.59 + 2.54·j. The community CountParadox footprint uses y = 22.12 instead (1.38 mm from the bottom edge, assuming symmetry). The 0.21 mm difference doesn't matter for hand soldering. Use 21.91 if you want the module to drop onto a 2.54 mm perfboard or header grid.

**Where these numbers come from:**
- **Waveshare dimension drawing:**
  - Board 18.00 × 23.50 mm, corner radius R1.00, pitch 2.54 mm.
  - The first side pad is 1.59 mm from the top edge.
  - The hole centre is 1.38 mm in from the side edge.
  - The bottom pad "9" is 3.92 mm from the right edge.
- **Waveshare FAQ footprint image:**
  - Each edge pad has an edge half-hole with its centre about 0.1 mm inside the outline.
  - It also has a full hole 1.27 mm further in.
  - The two edge rows are therefore 17.78 mm apart (7 × 2.54). The two hole rows are 15.24 mm apart (6 × 2.54).
- **Pad copper:** about 1.5 mm wide along the edge and about 2.0 mm deep from the edge on the finished board.
- **Hole diameter:** about 0.85 mm as drawn. It is tight for 0.64 mm square header pins. For a carrier footprint that takes header pins, use a 1.0 mm drill; the bobu01 "1 mm" footprint exists for exactly this reason.

**Placing the module in the brief's control-board coordinates.** This assumes the module is viewed component side up with USB-C toward +y, centre x = 84 and the USB edge at y = 195.5:

X = 75 + x_local, Y = 195.5 − y_local

Examples: GP26 at (76.38, 178.67), GP2 at (91.62, 188.83), 3V3 at (76.38, 188.83), GND at (76.38, 191.37).

### 1.3 Underside pads (bottom layer, SMD, no holes)

- There are 10 pads at **1.27 mm pitch**, each about 1.0 × 0.63 mm.
- They sit in one column at **x = 3.01 mm**. In the top view that is behind the **left** column (5V…GP14 side), 1.63 mm inboard of the left hole column.
- Order from the USB end: GND is nearest USB, GP17 is farthest.

| Waveshare conn./pin | Name | y (mm from USB edge) |
|---|---|---|
| P3-5 | GND | 6.99 |
| P3-4 | GP25 | 8.26 |
| P3-3 | GP24 | 9.53 |
| P3-2 | GP23 | 10.80 |
| P3-1 | GP22 | 12.07 |
| P2-5 | GP21 | 13.34 |
| P2-4 | GP20 | 14.61 |
| P2-3 | GP19 | 15.88 |
| P2-2 | GP18 | 17.15 |
| P2-1 | GP17 | 18.42 (5.08 from the bottom edge) |

Sources: Waveshare FAQ image, dimensioned 6.99 / 1.27 / 5.09 / 3.01, and the bottom-view pinout image.

**GP16 has no pad at all.** It drives the WS2812 DIN; DOUT is not connected.

Toccata uses none of the underside pads. On a carrier PCB, keep those areas free of copper and covered by solder mask, or use Kapton as the brief already says.

### 1.4 Mechanical notes for the footprint

- **Outline:** 18.00 × 23.50 mm, R1.0 corners.
- **USB-C receptacle:**
  - Standard 8.94 mm wide. It sits 4.67 mm in from the right edge, which leaves about 4.4 mm on the left, so it is roughly centred.
  - It overhangs the top edge by **about 1.0–1.5 mm**. CountParadox's Fab layer shows 1.0 mm; the Waveshare photo suggests about 1.4 mm. Take the exact value from the Waveshare STEP file (`RP2040_Zero_stp.zip`) if it matters.
- **Parts on the underside:**
  - **The RP2040 (QFN-56, about 0.9 mm tall), the 12 MHz crystal, the LDO (SOT-23-5, up to about 1.45 mm) and most passives are on the underside.**
  - **The top side** has USB-C, BOOT, RESET, the flash and the LED.
  - As a result, **the module cannot sit flush on a carrier.** Laid "flat" on castellations, it rests on its own parts (Kapton in between) with a gap of roughly 1.1–1.5 mm. The castellation solder joints then have to bridge that gap. This complaint is known on the Raspberry Pi forum, and the suggested fix there is a carrier with a hole under the module.
- **Mounting options:**
  - **(a) Perfboard (v3 style), recommended.** Use short male header pins in the inner holes. They sit on a true 2.54 mm grid (x = 1.38…16.62, y = 1.59…21.91), so the module drops straight onto a perfboard.
  - **(b) KiCad PCB.** Use a castellation SMD footprint plus a **board cutout inside the pad ring**, roughly x 2.2–15.8, y 0.5–20.8. Confirm the cutout against the STEP file.
  - **(c)** Solder flat on Kapton as in v3, accepting the stand-off. This works, but the joints are poor.

### 1.5 On-board circuit (Waveshare schematic `RP2040_Zero.pdf`)

- **USB-C.**
  - VBUS (A4/B9, A9/B4) goes **straight to the net VSYS, which is the "5V" pad**. There is no diode, fuse or polyfuse.
  - CC1 and CC2 each have **5.1 kΩ to GND** (R5, R9), so it works with C-to-C and A-to-C cables.
  - D+ and D− go through 27 Ω (R3, R4).
- **5V pad behaviour.** It is the USB VBUS. Waveshare's FAQ says VSYS "is connected to the VUSB pin directly" and recommends adding a diode if you power the board from the pin.
  - **For Toccata:** leave the 5V pad unconnected and power each module only from USB. Never tie the 5V pads of several boards together, and never feed it while USB is plugged in: that would back-feed the hub's VBUS.
- **3V3 regulator.**
  - The part is **U1 RT9013-33** (Richtek, SOT-23-5): VIN = VSYS, EN tied to VIN, BP pin with 100 nF (C4), output 1 µF (C5), input 3 × 2.2 µF (C1, C2, C6).
  - RT9013 ratings: 500 mA rated, current limit 0.5 / 0.6 / 0.85 A (min / typ / max), dropout 250 mV typ at 500 mA, **VIN 2.2–5.5 V (abs max 6 V)**, thermal shutdown 170 °C.
  - Thermal: **SOT-23-5 θJA = 250 °C/W, PD(max) = 0.4 W at 25 °C**.
- **ADC reference.**
  - The RP2040 has no internal reference. **ADC_AVDD = 3V3 through R6 200 Ω, with C11 2.2 µF to GND** (the net is named ADC_VREF). That is an RC low-pass with fc ≈ 360 Hz, identical to the Pico.
  - ADC_VREF and AGND are **not** brought out to pads, so an external reference is impossible without rework.
  - The Pico datasheet says the ADC draws about 150 µA, giving a **30 mV offset (ADC_AVDD ≈ 3V3 − 30 mV)** that varies with sampling and temperature.
- **Crystal:** 12 MHz, 15 pF load caps (C16, C17), 1 kΩ R8 on XOUT.
- **Flash:** W25Q16JVUXIQ, 2 MB.
- **Buttons:**
  - **BOOT** (Key1) pulls QSPI_SS_N to GND through R2 1 kΩ.
  - **RESET** (Key2) pulls RUN to GND.
  - Neither RUN nor SWD is on a pad; Waveshare confirms SWD is not brought out.
  - Flashing: hold BOOT and plug in USB, or hold BOOT, tap RESET and release BOOT.
- **RGB LED:** WS2812B, VDD from 3V3, **DIN on GP16**, GRB colour order. The WS2812B is officially rated from 3.5 V and runs at 3.3 V here. Keep brightness low; full white can draw tens of mA from the same LDO.
- **GPIO count:** 20 GPIO on the edges plus 9 underneath (GP17–25). GP16 is used by the LED.

### 1.6 3V3 current available to external loads

- **The limit is thermal, not the 500 mA rating.**
  - With VIN about 5.0–5.1 V, the LDO drops about 1.75 V.
  - At 0.4 W that allows **about 220 mA total at 25 °C ambient**, or about 165 mA at 50 °C (Tj ≤ 125 °C, θJA 250 °C/W).
  - Subtract the RP2040, flash and LED at roughly 25–40 mA. That leaves **about 150 mA of external 3V3 load as a comfortable limit**, and at most about 180 mA.
- **Toccata load per octave board:**
  - DRV5055 ICC at 3.3 V, TI datasheet **Rev C (June 2026): 2 mA typ, 4 mA max**. Rev B (2021) listed 6 mA typ / 10 mA max; Rev C records a change to the operating supply current.
  - 12 sensors = 24 mA typ / 48 mA max. O1 has 15 sensors (12 + 3 via EXT) = 30 / 60 mA.
  - Adding the MCU, the total is about 60–100 mA, so the LDO dissipates about 0.1–0.18 W. That is fine.
  - With the older Rev B figures, O1 worst case is about 185 mA total, about 0.33 W and Tj ≈ 110–120 °C. That is marginal but still within ratings.
- **On a clone with an unknown LDO:** measure 3V3 with all sensors attached. Also check the LDO body temperature (it should stay below about 70 °C to the touch or on a thermocouple).

### 1.7 RP2040 facts used in the design (RP2040 datasheet, build 2025-02-20)

- **ADC channels:** AINSEL 0–3 = **GP26 = ADC0, GP27 = ADC1, GP28 = ADC2, GP29 = ADC3**, and AINSEL 4 = on-chip temperature sensor.
  - Resolution 12 bit, **ENOB 8.7** (8.6–8.8 measured), 500 ksps with a 48 MHz clk_adc (96 cycles, 2 µs per sample).
  - The input puts about 1 pF across the pin while sampling. Effective impedance is over 100 kΩ, so no buffer is needed for DC.
  - The input range is 0 to ADC_AVDD, and it must never exceed IOVDD.
- **Errata RP2040-E11, "DNL error peaks in ADC".** The DNL is below 1 LSB except at **codes 512, 1536, 2560 and 3584**. That works out to about 0.41, 1.24, 2.06 and 2.89 V with a 3.3 V reference.
  - **Workaround: none. Affects B0, B1 and B2. Not fixed.**
  - Software correction is possible; for example, kitanokitsune/rp2040adc_correction.
  - For Toccata: the DRV5055 rests at VCC/2, which is about code 2048. Travel toward either pole will cross 1536 or 2560. Don't put note-on or velocity thresholds within a few codes of those values, or apply a DNL correction table.
- **Errata RP2040-E6.** The GPIO26–29 digital input is enabled after reset. The B2 bootrom and the SDK disable it. It only matters for bare-metal code.
- **Internal pulls:** **pull-up RPU = 50–80 kΩ, pull-down RPD = 50–80 kΩ** (datasheet Table 625, min/max).
  - Pad reset state is pull-down enabled (PDE = 1, PUE = 0) with Schmitt trigger on. That means MUX S0..S3 read low until firmware drives them.
  - Input leakage is at most 1 µA, so the ID pull-up plus solder-bridge scheme is fine.
  - The RP2350 "E9" pull-down latching bug does **not** apply to the RP2040.
- **GPIO levels at IOVDD = 3.3 V:** VIH ≥ 2.0 V, VIL ≤ 0.8 V, VOH ≥ 2.62 V.
  - Total current sourced by all IO is at most 50 mA; sunk current is also at most 50 mA.

### 1.8 Suggested KiCad symbol for the module

Create a single-unit symbol "RP2040-Zero_Module" with 23 edge pins numbered like Waveshare P1:

1 GP0, 2 GP1, 3 GP2, 4 GP3, 5 GP4, 6 GP5, 7 GP6, 8 GP7, 9 GP8, 10 GP9, 11 GP10, 12 GP11, 13 GP12, 14 GP13, 15 GP14, 16 GP15, 17 GP26/ADC0, 18 GP27/ADC1, 19 GP28/ADC2, 20 GP29/ADC3, 21 3V3 (power output), 22 GND (power input), 23 5V/VBUS (power output; leave unconnected in Toccata).

Optionally add pins 24–33 for the underside pads (GND, GP25…GP17) and mark them no-connect. The CountParadox/RP2040-Zero-Kicad footprint and symbol use the same numbering for 1–23.

---

## Part 2: CD74HC4067 16-channel mux module (parts-parts PP-A324, product_no=303)

### 2.1 What the module is

- **Seller page.** The title is "(PP-A324) 16채널 아날로그/디지털 멀티플렉서 모듈", 500 KRW, origin China OEM. The text says it uses the CD74HC4067 and reads 16 signals with 4 digital pins and 1 analog pin. No dimensions or pin list are given.
- **Photo.** It shows a blue board with the silkscreen **"TENSTAR ROBOT"** and "16-Channel Analog Multiplexer", and an SSOP-24 chip marked 74HC4067.
- **It is a copy of the SparkFun BOB-09056 "Analog/Digital MUX Breakout" v11.** Evidence:
  - The label texts and positions are the same.
  - The 0603 capacitor is next to VCC/GND in the same place as SparkFun's C1.
  - A resistor marked "**103**" (10 kΩ) is next to S3, in the same place as SparkFun's R1.
  - The GND pin lines up with C4, as it does on SparkFun's board. This was checked by perspective reconstruction of the photo.
- The SparkFun Eagle files (`Analog-Digital-Mux-Breakout-v11.brd/.sch`) were parsed for the numbers below.

### 2.2 Pin order and geometry

Photo orientation: chip side up, with the long control row at the far edge.
- Far row, left to right: **SIG, S3, S2, S1, S0, EN, VCC, GND.** GND has the square pad.
- Near row, left to right: **C15, C14, … C1, C0.**
- **C0 is at the same end as GND. C15 is at the same end as SIG.**

**Coordinates.** Module-local: u runs along the long axis from the **C0/GND end** (0 → 40.64). w runs across the board, from the channel-row edge (0) to the control-row edge (17.78). SparkFun v11 geometry, confirmed from the Eagle file:

| Header | Pin (hdr#) | Name | u (mm) | w (mm) | Aligned with |
|---|---|---|---|---|---|
| J1 (1×16) | 1 | C0 | 1.27 | 1.27 | |
| J1 | 2 | C1 | 3.81 | 1.27 | |
| J1 | 3 | C2 | 6.35 | 1.27 | |
| J1 | 4 | C3 | 8.89 | 1.27 | |
| J1 | 5 | C4 | 11.43 | 1.27 | GND |
| J1 | 6 | C5 | 13.97 | 1.27 | VCC |
| J1 | 7 | C6 | 16.51 | 1.27 | EN |
| J1 | 8 | C7 | 19.05 | 1.27 | S0 |
| J1 | 9 | C8 | 21.59 | 1.27 | S1 |
| J1 | 10 | C9 | 24.13 | 1.27 | S2 |
| J1 | 11 | C10 | 26.67 | 1.27 | S3 |
| J1 | 12 | C11 | 29.21 | 1.27 | SIG |
| J1 | 13 | C12 | 31.75 | 1.27 | |
| J1 | 14 | C13 | 34.29 | 1.27 | |
| J1 | 15 | C14 | 36.83 | 1.27 | |
| J1 | 16 | C15 | 39.37 | 1.27 | |
| J2 (1×8) | 1 | GND | 11.43 | 16.51 | C4 |
| J2 | 2 | VCC | 13.97 | 16.51 | C5 |
| J2 | 3 | EN | 16.51 | 16.51 | C6 |
| J2 | 4 | S0 | 19.05 | 16.51 | C7 |
| J2 | 5 | S1 | 21.59 | 16.51 | C8 |
| J2 | 6 | S2 | 24.13 | 16.51 | C9 |
| J2 | 7 | S3 | 26.67 | 16.51 | C10 |
| J2 | 8 | SIG | 29.21 | 16.51 | C11 |

- **Board:** **40.64 × 17.78 mm** (1.6 × 0.7 in) on SparkFun; clone listings say "40 × 18 mm".
- **Pins:** pitch **2.54 mm**. The **two rows are 15.24 mm apart** (0.6 in, 6 pitches), so the module sits on a 2.54 mm perfboard grid. Pads are Ø1.88 mm with a 1.016 mm drill.
- **Mounting holes:** **Ø3.3 mm** (for #4 or M3) at (u 2.54, w 15.24) and (u 38.10, w 15.24). Both are on the control-row side, one near each end, which matches the photo.
- **Measure the clone with calipers before fixing the footprint.** Clones often differ by a few tenths of a mm, and the chip may sit slightly differently. The pin grid is what matters.

**Header to chip pin mapping** (TI SSOP-24 "DB" package, same pin-out for SOIC and PDIP):

| Header name | IC pin | IC pin name |
|---|---|---|
| SIG | 1 | COMMON I/O |
| C7…C0 | 2…9 | I7…I0 (C7 = pin 2, C6 = 3, C5 = 4, C4 = 5, C3 = 6, C2 = 7, C1 = 8, **C0 = 9**) |
| S0 | 10 | S0 |
| S1 | 11 | S1 |
| GND | 12 | GND |
| S3 | 13 | S3 |
| S2 | 14 | S2 |
| EN | 15 | E (active low) |
| C15…C8 | 16…23 | I15 = 16, I14 = 17, I13 = 18, I12 = 19, I11 = 20, I10 = 21, I9 = 22, **I8 = 23** |
| VCC | 24 | VCC |

Truth table: channel = S3·8 + S2·4 + S1·2 + S0, with **E = 0 enabling** the selected channel and **E = 1 turning all switches off**.

### 2.3 On-board parts

- **C1 = 0.1 µF (0603) from VCC to GND**, next to the VCC/GND pins. This is the decoupling capacitor.
- **R1 = 10 kΩ (0603, marked "103") from EN to GND**, a pull-down, so the module is enabled by default. This is from the SparkFun schematic; the clone's copy of R1 is in the same spot. **Verify it by measuring EN–GND with a multimeter, expecting about 10 kΩ.** Tying EN to GND as the brief does is harmless either way.
- There are **no pull-downs on S0–S3**, no series resistors, no ESD protection and **no LED**.

### 2.4 CD74HC4067 electrical characteristics relevant at VCC = 3.3 V

Sources: TI datasheet SCHS209D (Dec 2024) and the Nexperia 74HC4067 datasheet (Rev 10, Jul 2024).

- **Supply:** HC types 2–6 V. The HCT variant needs 4.5–5.5 V, so a **74HCT4067 must not be used at 3.3 V**; confirm the chip marking reads HC. Absolute max VCC is −0.5 to 7 V.
- **Switch voltage range:** VIS from 0 to VCC.
  - Input and output clamp-diode current: ±20 mA max beyond −0.5 V or VCC + 0.5 V.
  - Switch current: ±25 mA max. VCC/GND current: ±50 mA max.
- **Ron:** neither TI nor Nexperia specifies it at 3.3 V.
  - TI at VCC = 4.5 V, 25 °C: 70 Ω typ / 160 Ω max at the rails, and 90 / 180 Ω across the range. Over −40 to 85 °C the maxima are 200 / 225 Ω.
  - Nexperia at 4.5 V: Ron(peak) 110 Ω typ / 180 Ω max. At 2.0 V: Ron(rail) 150 Ω typ, with Ron(peak) described as "extremely non-linear".
  - **Estimate for 3.3 V: about 150–300 Ω typ peak near mid-supply.** Design as if it were 1 kΩ worst case. It is irrelevant for DC because the source is the low-impedance DRV5055 output and the ADC is high impedance.
  - ΔRon between channels: 10 Ω typ at 4.5 V.
- **Break-before-make:** yes, built in. TI gives 6 ns typ at 4.5 V; Nexperia says "typical break before make built-in".
- **Switching times (CL = 50 pF, 25 °C):**
  - Sn to output turn-on: 60 ns max at 4.5 V and 300 ns max at 2 V, so **about 150 ns at 3.3 V** by estimate.
  - E to output: 55 ns at 4.5 V and 275 ns at 2 V.
- **Capacitances:** switch input 5 pF, common (SIG) **50 pF**, control input 10 pF.
- **Leakage:** off-switch leakage ±0.8 µA at 25 °C and ±8 µA over temperature (VCC = 6 V). Control input leakage ±0.1 µA, ICC 8 µA max at 25 °C.
- **Control logic levels at 3.3 V:** TI only gives 2 V and 4.5 V points. Interpolated, VIH ≈ 2.3 V and VIL ≈ 1.0 V. The RP2040 VOH (≥ 2.62 V) is enough because both run from the same 3V3.
- **ESD:** Nexperia specifies HBM > 2 kV (JS-001 class 2) and CDM > 1 kV. TI's Rev D mentions an ESD table but gives no numbers in the text extract.

### 2.5 Design consequences for Toccata

- **Settling after changing S0..S3:** allow ≥ 1 µs (or throw away the first conversion) before starting the ADC. The time constant is roughly 300 Ω × (50 + 5 + 1 pF) ≈ 20 ns plus about 150 ns of switching time, so 1 µs leaves plenty of margin. Twelve to fifteen channels at about 3 µs each is under 50 µs per scan.
- **EXT channels C12–C15** leave the board through about 350 mm of wire on O1 and O7. They are unprotected CMOS inputs.
  - Optional: 1 kΩ in series at the EXT pads. Its effect on settling is negligible (about 55 ns).
  - On O2–O6 they float; firmware ignores them, which is harmless.
- **VCC** must come from the same 3V3 that powers the sensors, so that VIS ≤ VCC always holds. The brief already does this, using the RP2040-Zero 3V3.
- **Use an "HC" part**, not HCT, at 3.3 V; see 2.4.

---

## Open questions / verify on arrival

1. **Is the RP2040-Zero genuine?** The missing "W" logo points to a clone. Measure the 3V3 rail under full sensor load and look at the LDO marking. If the clone doesn't boot reliably, add `PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64`.
2. **Bottom-row hole y:** 21.91 (Waveshare image) vs 22.12 (CountParadox). Check with calipers against the side-column holes if you are making a header-pin footprint.
3. **USB-C overhang:** 1.0 mm (CountParadox) vs about 1.4 mm (photo). Take it from the Waveshare STEP file if the enclosure is tight.
4. **Mux module:** measure its outline (about 40.6 × 17.8 mm) and the row spacing (15.24 mm), check the chip marking (HC, not HCT), and confirm EN–GND ≈ 10 kΩ.
5. **DRV5055 supply current:** the Rev C figure is 2 / 4 mA, older revisions said 6 / 10 mA. Use the older numbers for the 3V3 budget if the sensors come from old stock.
6. **Mounting (layout decision, not a pin question):** "soldered flat by castellation" doesn't give a flush fit because the RP2040, crystal and LDO are on the underside. On a perfboard, use header pins in the 2.54 mm-grid inner holes. On a PCB, use a cutout.

## Sources

- Waveshare RP2040-Zero wiki (pinout, dimensions, FAQ, anti-piracy notice): https://www.waveshare.com/wiki/RP2040-Zero
- Waveshare RP2040-Zero schematic: https://files.waveshare.com/upload/4/4c/RP2040_Zero.pdf
- Waveshare RP2040-Zero STEP file: https://files.waveshare.com/upload/f/f7/RP2040_Zero_stp.zip
- Seller page for PP-A799-2: https://parts-parts.co.kr/product/detail.html?product_no=2383 (photos: /web/upload/01-ARDUINO/PP-A799-1.jpg)
- Seller page for PP-A324: https://parts-parts.co.kr/product/detail.html?product_no=303 (photo: /web/product/big/201801/303_shop1_188438.jpg)
- RP2040 datasheet (errata E6 and E11, Table 625, section 4.9): https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
- Raspberry Pi Pico datasheet (ADC_AVDD 200 Ω / 2.2 µF, 30 mV offset): https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf
- Richtek RT9013 datasheet: https://dl.linux-sunxi.org/T507/other_datasheets/richtek_ldo_RT9013.pdf
- TI CD74HC4067 datasheet SCHS209D: https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf
- Nexperia 74HC4067 datasheet: https://assets.nexperia.com/documents/data-sheet/74HC_HCT4067.pdf
- SparkFun BOB-09056 schematic and Eagle files: https://cdn.sparkfun.com/datasheets/BreakoutBoards/Analog-Digital-Mux-Breakout-v11.pdf and https://cdn.sparkfun.com/datasheets/BreakoutBoards/Analog-Digital-Mux-Breakout-v11.zip
- TI DRV5055 datasheet SBAS640C: https://www.ti.com/lit/ds/symlink/drv5055.pdf
- CountParadox KiCad footprint: https://github.com/CountParadox/RP2040-Zero-Kicad
- bobu01 1 mm-hole footprint: https://github.com/bobu01/RP2040-Zero-Kicad-Footprint-1mm
- NuttX board page (anticlockwise pad numbering): https://nuttx.apache.org/docs/latest/platforms/arm/rp2040/boards/waveshare-rp2040-zero/index.html
- pico-sdk board header: https://github.com/raspberrypi/pico-sdk/blob/master/src/boards/include/boards/waveshare_rp2040_zero.h
- XOSC startup-delay fix for clones: https://github.com/marcopoloFR/debugprobe_rp2040-zero
- Raspberry Pi forum on the non-flat backside and a carrier with a hole: https://forums.raspberrypi.com/viewtopic.php?t=324718
- RP2040 ADC DNL software correction: https://github.com/kitanokitsune/rp2040adc_correction
