# Toccata audio chain: part facts for the KiCad schematic

Research date 2026-09-28. Scope: XH-A232 amp, PJ-313 jack, Apple USB-C dongle, XT30U, CW-100B25, and the 80 Hz input HPF.
Confidence: **H** = primary source (datasheet or clear photo), **M** = consistent secondary sources, **L** = inference only. Nothing in the repo was edited.

---

## 0. Findings that change the schematic

1. **The XH-A232 ships at 36 dB gain (M).** At that setting the TPA3110 input impedance is 9 kΩ typ (7.2 kΩ min). At 20 V into 8 Ω, about 0.2 Vrms at the input drives the amp to full power. The dongle gives 0.5 to 1.0 Vrms, which is 8 to 14 dB more than that. **You must cap the level**, either with an ALSA/FluidSynth volume ceiling or with a resistor pad (see §6).
2. **The corner of the "80 Hz" HPF is about 93 Hz, not 80 Hz (H, by calculation).** This assumes 2 µF + 1 kΩ with the board's 9 kΩ input and its own coupling cap. To get about 80 Hz, change the shunt resistor to **1.2 kΩ** and keep 2 µF (§6).
3. **The part name "PJ-313" does not tell you the pin numbering, and it does not guarantee normal contacts (H).** The SHOU HAN "PJ-313 5JCJ" drawing has 5 pads but shows only 3 poles in its contact schematic. The BSUN seller page (eleparts 67811) has no drawing. The TN/RN normals, which the headphone cut-off (R15) needs, must be confirmed on the real part with a meter (§2).
4. **KiCad `AudioJack3_SwitchTR` uses letters as pin numbers** (`S`, `T`, `TN`, `R`, `RN`), not 1 to 5 (H). The footprint pads must use the same letters.
5. **The Korean Apple dongle's output level is not documented.** The US A2049 gives about 1.0 Vrms and the EU A2155 about 0.5 Vrms. Read the model number printed on the USB-C plug (§3).
6. **The CW-100B25 is also listed as 4 Ω by at least one seller.** Measure Re: about 6 to 7 Ω means 8 Ω, about 3 to 3.5 Ω means 4 Ω.

---

## 1. XH-A232 / HW-404 (TPA3110D2) 2-channel class-D board — icbanq P017179248, 제노 HAM6104

### 1.1 Terminals

Source: the icbanq/제노 product photo HAM6104.jpg (component side, silkscreen readable). Orientation: heatsink up, **VCC/GND edge toward you (bottom)**.

| Group | Position (component side, bottom edge toward you) | Silkscreen | Net in Toccata | Notes |
|---|---|---|---|---|
| Speaker out | top edge, 1st pad from left | `L+` | SPK_L+ | BTL. Neither output pin is ground. |
| Speaker out | top edge, 2nd pad | `L-` | SPK_L- | BTL, about Vcc/2 average, switching |
| Speaker out | top edge, 3rd pad | `R+` | SPK_R+ | BTL |
| Speaker out | top edge, 4th (rightmost) pad | `R-` | SPK_R- | BTL |
| Audio in | bottom edge, left, 3-hole header `P1`, left hole | `L` | AMP_IN_L | about 2.54 mm pitch (estimated from photo; the outline looks like a 3-pin 2.54 header or JST-XH). Holes are empty. |
| Audio in | `P1` middle hole | (no label) | AGND / IN_G | Assumed GND (M). **Check with a meter**: middle hole to the `GND` power pad should read 0 Ω. |
| Audio in | `P1` right hole | `R` | AMP_IN_R | |
| Power | bottom edge, centre-right, square pad | `GND` | GND_20V | Solder pad with hole (no screw terminal on this version) |
| Power | bottom edge, right, square pad | `VCC` | +20V | 8–26 V |

- Pad pairing is from the silkscreen: `L+` is left of pad 1, `L-` right of pad 2, `R+` left of pad 3, `R-` right of pad 4. The labels are printed rotated. **H** for the photographed board. Clones may differ, so check against your board.
- There are 4 mounting holes in the corners. The board is about 54 × 46 × 14 mm (seller specs; one says 53 × 45 × 14–15 mm).
- Other parts visible: 4 × 220 µF/35 V electrolytics, 4 × "220" (22 µH) output inductors, LED `D3` (power indicator), SMA diode `D1` next to VCC (marked SS3x). D1 is probably reverse-polarity protection; its topology (series or shunt) is unknown, so do not rely on it. Resistors `R1`/`R2` are marked 102/201, which is LED/misc, not gain.

### 1.2 Suggested KiCad representation (custom symbol "XH-A232", no library part exists)

- `J_PWR`: 1 = VCC, 2 = GND
- `J_IN` (P1): 1 = L, 2 = GND, 3 = R (numbered left to right in the orientation above)
- `J_OUT`: 1 = L+, 2 = L−, 3 = R+, 4 = R−

### 1.3 Electrical facts

| Item | Value | Conf. | Source |
|---|---|---|---|
| Supply | 8–26 V recommended (TPA3110D2 PVCC/AVCC); abs max 30 V; board caps are 35 V. **20 V is OK.** | H | TI SLOS528F Rec. Op. Cond. / Abs Max |
| Gain as shipped | **36 dB** (GAIN0 = GAIN1 = high). Forum summaries say both gain pins are tied together to the AVCC/PVCC rail. | M | electropeak.com product page ("factory-set to maximum 36 dB on many units"); diyAudio "TPA3110D2 board mods" thread (summary only, the thread itself is behind a bot check) |
| TPA3110 gain table | GAIN1,GAIN0 = 00 → 20 dB, Zi 60 kΩ; 01 → 26 dB, 30 kΩ; 10 → 32 dB, 15 kΩ; 11 → **36 dB, 9 kΩ** (typ, ±20 %; TI says design for 7.2 kΩ min) | H | TI datasheet Table 2 |
| GAIN0 / GAIN1 pins | IC pin 5 / pin 6 (HTSSOP-28). Logic high ≥ 2 V, low ≤ 0.8 V. | H | TI Table 1 |
| Input coupling caps on board | **Value not confirmed.** The TI reference design uses 1 µF on each of LINP/LINN/RINP/RINN; the small caps C21–C27 near P1 are probably these. Board fc with 1 µF and 9 kΩ = 17.7 Hz. | L | TI typical application; photo |
| Input type | Single-ended in on P1. The board AC-grounds LINN/RINN internally (assumed). Input DC bias at the IC is 3 V, blocked by the board caps. | M | TI §9.3.3 |
| SD (mute) / FAULT | **Not brought out**, no pad or label on the board. SD is tied high on the board, so the amp is always enabled when powered. There is no mute input; the TPA3110 soft start handles pop. | M | Photo (no pad); TI Table 1: SD pin 1, FAULT pin 2 |
| PLIMIT | Not brought out; setting unknown (probably tied to GVDD = no limit) | L | |
| Volume pot | **None on board** | H | photo; electropeak |
| Output power at 20 V, 8 Ω BTL | about 19–21 W/ch at 1 % THD, about 24 W/ch at 10 % THD. This is a calculation from Rds(on) 240 mΩ; TI's headline is 15 W/ch at 10 % THD at 16 V. | M | TI features + calc |
| Speaker outputs | BTL: **never connect L− or R− to GND or to each other.** Filterless (inductors fitted). | H | TI |

**Checks when the board arrives (meter):**
1. Power the board at 20 V with no input. Measure IC pin 5 and pin 6 against GND. Both > 2 V means 36 dB; confirm that.
2. P1 middle hole to the `GND` pad should read 0 Ω.
3. Measure `L-` to `GND`: it must **not** read 0 Ω (it is BTL).

---

## 2. BSUN PJ-313 3.5 mm stereo jack (eleparts no=67811)

### 2.1 What the sources show

| Source | What it says |
|---|---|
| eleparts 67811 (BSUN PJ-313, the part in the BOM) | Name and price only. **No drawing, no pinout.** It says to see the maker's datasheet. |
| SHOU HAN "PJ-313 5JCJ" datasheet (LCSC C668607) | 5 PCB pads (3 in a row at 1.8 / 3.2 / 3.5 mm steps, plus 2 on the other side). The contact schematic shows **only 3 poles (1, 2, 3), with no switch/normal contacts drawn.** The parts table maps contact ① → terminal 1, ② (qty 2) → 2–3, ③ → 4, base → 5, which is self-inconsistent. |
| HOOYA "PJ-313D" datasheet (LCSC C2939579) | A different part: SMD, 3-pole, pads numbered 2/3/4, **no normals**. |
| Generic listings (iFuture, Sharvi, Amazon/uxcell) | "5 pins: Left, Right, Ground + 2 switch contacts". No numbering given. |

**Conclusion: pin numbering varies by vendor, and some parts sold as "PJ-313" have no normals.** Do not put numbers 1–5 on the schematic. Use functional names, then map them to physical pins with the check below.

### 2.2 Functional pins and behaviour (switched TRS jack, R15 scheme)

| Name | Function | Plug out | Plug in |
|---|---|---|---|
| S | Sleeve (GND) | — | touches plug sleeve |
| T | Tip spring (L) | closed to TN | touches plug tip; **T–TN opens** |
| TN | Tip normal | closed to T | open |
| R | Ring spring (R) | closed to RN | touches plug ring; **R–RN opens** |
| RN | Ring normal | closed to R | open |

For jack #1 (headphone jack in the left cheek): the dongle feeds T/R/S. TN/RN/S go to the amp through cable 2. With no headphones, the dongle reaches the amp through T→TN and R→RN. When headphones are plugged in, the springs lift, the normals open, and the amp input is cut. The 1 kΩ shunt on the amp side then holds the amp input at GND, so it stays quiet.

### 2.3 Meter check (do this on each jack before soldering)

1. **No plug.** Beep all 10 pin pairs. You should find **exactly two closed pairs** (T–TN and R–RN) and one isolated pin (S).
   - No closed pair means the jack has **no normals** and cannot do R15. Buy a switched jack (for example CUI SJ1-3525N, which has a KiCad footprint).
2. **Plug in a TRS plug** (use the uncut end of the 1.5 m cable; first beep its tip/ring/sleeve at the far end).
   - Plug tip to jack pin with continuity = **T**
   - Plug ring = **R**
   - Plug sleeve = **S**
3. With the plug in, both pairs from step 1 must now be **open**. T's step-1 partner is **TN**; R's partner is **RN**.
4. Pull the plug out and confirm T–TN and R–RN close again. Mark the pins on the perfboard.

Usual geometry (hint only, **L**): S is the pin nearest the opening, and the tip contact is the deepest (farthest from the opening).

### 2.4 KiCad

- Symbol `Connector_Audio:AudioJack3_SwitchTR` ("Audio Jack, 3 Poles (Stereo / TRS), Switched TR Poles (Normalling)").
- **Pin "numbers" are letters:** `S`, `T`, `TN`, `R`, `RN`. In the symbol, top to bottom on the right side: S (y +2.54), R (0), RN (−2.54), T (−5.08), TN (−7.62). **H** (kicad-symbols master, KiCad 10 format).
- Library footprints use the same letters (for example `Jack_3.5mm_CUI_SJ1-3525N_Horizontal` pads S/T/TN/R/RN). **There is no PJ-313 footprint** in the KiCad library. For a PCB, draw your own and **name the pads with the letters** found in §2.3. If you build on perfboard, the pin letters are only for labelling.
- In the schematic, add a note next to each jack: `PJ-313: pad letters per meter check §2.3`.

---

## 3. Apple USB-C to 3.5 mm adapter (MW2Q3KH/A)

| Item | Value | Conf. | Source |
|---|---|---|---|
| Hardware | Same product as MU7E2 (retailers list MW2Q3 and MU7E2 together). DAC/amp chip is Cirrus Logic CS46L06-class. | M | Best Buy listing; frieve review |
| Max output | **US A2049 ≈ 1.0 Vrms; EU A2155 ≈ 0.5 Vrms** (RAA measured 0.5 Vrms on A2155). **The Korean KH/A model number is not confirmed.** Read the fine print on the plug. Design for 0.5–1.0 Vrms. | M/H | head-fi / audioreviews; reference-audio-analyzer A2155 report |
| Output impedance | about 0.3–0.4 Ω (RAA, A2155); 0.9 Ω (frieve). Well under 1 Ω either way. | H/M | RAA; frieve |
| USB | VID:PID **05ac:110a**. Interface class 01-01-**20** means bInterfaceProtocol 0x20 = **USB Audio Class 2.0**. Linux driver: `snd-usb-audio` (standard, no quirk needed to play). | H | linux-hardware.org |
| Rates on Linux | **48 kHz only** (alt 1 S24_3LE, alt 2 S16_LE, 2 ch). 44.1 kHz is not offered, which is fine for FluidSynth at 48 kHz. | H | alsa-lib issue #322; RPi forum t=290387 |
| Mixer | ALSA control `Headphone`; `amixer -c <card> sset Headphone 120` = 0 dB (max). | M | RPi forum t=290387 |
| Known Pi issue | One report (RPi 4, Bullseye) of it showing in `lsusb` but not in `aplay -l`; unresolved. Use `hw:CARD=<id>,DEV=0` by card name, not by number. | M | shairport-sync #1597 |
| Output type | Ground-referenced headphone out (no DC). A 1 kΩ load is easy (it is rated for 32 Ω headphones). | M | |

---

## 4. AMASS XT30U-M / XT30U-F (eleparts 12779720 / 12779721)

| Item | Value | Conf. |
|---|---|---|
| Rating | **15 A rated, 30 A instantaneous, DC 500 V**, contact R 0.70 mΩ, 1000 mating cycles, 18 AWG cable, −20…120 °C, PA UL94 V0, gold-plated brass | H (AMASS catalogue p.13, via LCSC C99101) |
| Size | 10.2 × 5.2 mm face, contacts 5.0 mm apart; length F 12.4 mm, M 13.7 mm | H |
| Polarity | The housing has one **flat (straight) end** and one **chamfered (angled) end**. Convention (AMASS XT family, with small +/− moulded on the housing): **flat side = +, chamfered side = −.** The AMASS catalogue drawing does not print it. | M (done.land XT60 page; the same convention is used for XT30) |
| AMASS recommended use | XT30U-**F** = battery (source) side; XT30U-**M** = controller (load) side | H |

Speaker wiring: SPK_L+ / SPK_R+ go to the **flat-side** contact and L− / R− to the chamfered contact, the same on both channels, so both speakers are in phase. After soldering, beep each contact through to the speaker terminal.
Minor note: the BOM puts the male on the amp (source) side, which is the reverse of AMASS's source=female habit. The male contacts are shrouded, so the risk is low. A short on an unplugged lead only trips the TPA3110 short protection, which latches until power is cycled.

---

## 5. 삼미 (SAMMI/SAAT) CW-100B25 4" full range

| Item | Value | Conf. |
|---|---|---|
| Power | **Rated 25 W, max 50 W** (the seller spec sheet used in v3 BOM line L07). The model suffix "B25" also points to 25 W. Most shop titles show only "50W", which is the max/peak figure. | M |
| Impedance | 8 Ω (Re 6.2 Ω per the v3 spec sheet). **Warning: a G마켓 listing titles "CW-100B25 4옴".** Measure Re before building. | M |
| Other (from v3 BOM, not re-verified) | 86 dB/1W/1m (seller) or 89±2 dB (maker test sheet); Fs 128 Hz (seller T/S) vs 90±18 Hz (maker); Qts 0.72; frame 105 × 105, depth 57 + 4 mm | L (not re-checked) |

At 20 V the amp can give about 20 W clean and about 24 W at 10 % THD. That is at the 25 W rating, so keep the FluidSynth limiter on and cap the level (§6). A hard-clipped amp at full dongle level could push the drivers past 25 W average.

---

## 6. HPF and level check (2 µF series + 1 kΩ shunt → XH-A232)

Model: dongle Rs 1 Ω → C1 (2 µF) → node A. Node A → R1 (1 kΩ) → GND, and node A → board cap Cb → TPA3110 Zi (9 kΩ typ at 36 dB). Output is the current into Zi. The −3 dB point is solved numerically.

| Case | fc (−3 dB) |
|---|---|
| Ideal 2 µF + 1 kΩ only | 79.6 Hz |
| **With board, Zi 9 kΩ, Cb 1 µF (expected)** | **93 Hz** (−3.7 dB at 80 Hz, −8.5 dB at 40 Hz, −15.4 dB at 20 Hz) |
| Zi 7.2 k / 10.8 k (±20 %), Cb 1 µF | 98 / 91 Hz |
| Zi 9 k, Cb 0.47 µF / 10 µF | 104 / 89 Hz |
| If gain were 26 dB (30 k) / 20 dB (60 k) | 83 / 81 Hz |

Why: at 36 dB the 9 kΩ board input sits in parallel with 1 kΩ (giving about 0.9 kΩ), and the board's own 1 µF/9 kΩ pole adds a little more cut.

**To get 80 Hz at 36 dB:** use **R1 = 1.2 kΩ** with 2 µF (fc 81 Hz typ, 78–85 Hz across the ±20 % Zi spread). Another option is 2.2 µF with 1 kΩ (85 Hz typ).

**Driving the network from the dongle:** the load is 0.90 kΩ at 1 kHz and up, 1.36 kΩ at 80 Hz, and 4.1 kΩ at 20 Hz. That is no problem for a headphone amp rated for 32 Ω. There is no DC on either side, so X7R caps are fine. With headphones plugged in, the normals open and R1 holds the amp input at GND, so there is no hum.

**Level (important):** at 36 dB (×63), full power at 20 V/8 Ω needs only about **0.20 Vrms** in. The dongle gives 0.5 Vrms (A2155) or 1.0 Vrms (A2049), which is +8 to +14 dB over that. Pick one:
- **Software:** set a ceiling on ALSA `Headphone` (or on FluidSynth `synth.gain`) so the peak output is about 0.2 Vrms, and keep `synth.limiter` on. This costs no parts, but a mistake can clip the amp and overdrive the 25 W drivers.
- **Hardware L-pad (keeps about 80 Hz):** C1 **0.47 µF** → series **3.3 kΩ** → node A, with R1 **1 kΩ** shunt. Result: **−13.4 dB, fc ≈ 84 Hz**. The v3 BOM idea of "series 1 kΩ, −6 dB" with 2 µF would move fc to about 50 Hz; if you use it, C1 = 1 µF gives 88 Hz at −6.5 dB.

(Not asked, noted for the schematic: the dongle GND (USB, via Pi, via the XL4016 buck) and the amp GND (20 V bus) are joined through the non-isolated buck, so the audio sleeve closes a ground loop. Run the amp power GND and the Pi 5 V GND back to one star point at the fuse/switch. If a whine appears, the fix is a ground-loop isolator on the audio line.)

---

## Sources

- TI TPA3110D2 datasheet SLOS528F: https://www.ti.com/lit/ds/symlink/tpa3110d2.pdf
- icbanq 제노 HAM6104 page + photo: https://www.icbanq.com/P017179248 , https://www.icbanq.com/icdownload/data/ICBShop/Product/core_images/JENO/HAM6104.jpg
- Electropeak XH-A232 page (36 dB, no volume control): https://electropeak.com/xh-a232-2x30w-class-d-digital-audio-power-amplifier-board
- diyAudio "TPA3110D2 board mods" (bot-check; used via search summary only): https://www.diyaudio.com/community/threads/tpa3110d2-board-mods.368076/
- SHOU HAN PJ-313 5JCJ datasheet: https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2006181822_SHOU-HAN-PJ-313-5JCJ_C668607.pdf
- HOOYA PJ-313D datasheet: https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2201201600_HOOYA-PJ-313D_C2939579.pdf
- eleparts BSUN PJ-313: https://www.eleparts.co.kr/goods/view?no=67811
- KiCad symbol: https://gitlab.com/kicad/libraries/kicad-symbols/-/raw/master/Connector_Audio.kicad_symdir/AudioJack3_SwitchTR.kicad_sym
- KiCad footprint (pad letters): https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/master/Connector_Audio.pretty/Jack_3.5mm_CUI_SJ1-3525N_Horizontal.kicad_mod
- Apple dongle: https://reference-audio-analyzer.pro/en/report/amp/apple-usb-c.php , https://audioreview.frieve.com/products/en/apple-usb-c-3-5mm-headphone-jack-adapter/ , https://www.audioreviews.org/apple-audio-adapter-review/ , https://linux-hardware.org/?id=usb:05ac-110a , https://github.com/alsa-project/alsa-lib/issues/322 , https://forums.raspberrypi.com/viewtopic.php?t=290387 , https://github.com/mikebrady/shairport-sync/issues/1597 , https://www.bestbuy.com/site/apple-usb-c-to-3-5mm-headphone-jack-adapter-white/6228671.p?skuId=6228671
- AMASS XT30U catalogue (LCSC C99101): https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1811011911_Changzhou-Amass-Elec-XT30U-M_C99101.pdf
- XT polarity convention: https://done.land/components/power/cables/connectors/xt60/
- CW-100B25 listings: https://www.11st.co.kr/products/1565354988 , https://www.11st.co.kr/products/2814945680 , http://item.gmarket.co.kr/Item?goodscode=635034537
