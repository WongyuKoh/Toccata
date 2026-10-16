// Toccata — 모노리식(일체형) 컴플라이언트 건반 · 옥타브 모듈 (설계 문서 v2.0)
// 좌표계: x = 모듈 가로(왼쪽 0), y = 건반 길이(0 = 연주자 앞), z = 위(키베드 바닥 0)
// ★ v2.0: 금속 스프링·핀·요람을 전부 제거. 건반 1개 = PETG 단일 프린트.
//    ① 키 본체 ② 교차 판스프링 피벗(회전 전담) ③ 꼬리 사행 복귀 판스프링(복귀력 전담)
//    정지 위치는 스프링이 아니라 꼬리 밑 하드 업스톱이 정의한다.
//
//   openscad -o out.png --preview --viewall --autocenter -D 'PART="assembly"' toccata.scad
//   PART: assembly | pressed | exploded | section | bed12 | keys12 | key_white | key_black
//         | rail | free_key | coupons | full88 | ixcheck

PART = "assembly";
$fn = 40;

/* ---------- 0. 프린터 / 압출 폭 (모든 스프링 두께의 기준) ---------- */
nozzle_d = 0.4;
ew       = 0.42;                 // 압출 폭. 스프링 두께는 전부 ew의 정수배
bed_x    = 220;  bed_y = 220;    // 가정값 — 실제 프린터 확정 시 갱신

/* ---------- 1. 모듈 / 피치 ---------- */
white_pitch   = 23.5;
stem_pitch    = 164.5/12;        // 13.70833
key_gap       = 1.6;
key_len       = 218;
bed_len       = 230;
white_h       = 12.7;
black_rise    = 10.16;
black_front_y = 50.8;
black_top_end = 152.4;
tail_y0       = black_front_y - key_gap;      // 49.2

/* ---------- 2. 기구 기준면 ---------- */
bed_h       = 6;                 // 키베드 바닥판 두께
key_rest_z  = 18.3;              // 정지 시 건반 하면(피벗 앞쪽)
dip         = 10.8;
hinge_y     = 165;
hinge_z     = key_rest_z;        // ★ 피벗 중심을 자석면과 같은 높이로 → 자석 수평이동 0.118
press_angle = atan(dip / hinge_y);            // 3.7503°
felt        = 1.5;               // 다운스톱 TPU/펠트
white_top   = key_rest_z + white_h;           // 31.0
black_top   = white_top + black_rise;         // 41.16

/* ---------- 3. 교차 판스프링 피벗 ---------- */
t_blade   = 2*ew;                // 0.84  (2벽)
L_blade   = 16.0;
b_blade   = 2.5;                 // 4장 × 2.5 = 유효폭 5.0
blade_n   = 4;
blade_sp  = 0.6;                 // +45/−45 사이 x 간극
bhalf     = L_blade/2/sqrt(2);   // 5.657
blade_yf  = hinge_y - bhalf;     // 159.343
blade_yb  = hinge_y + bhalf;     // 170.657
blade_zlo = hinge_z - bhalf;     // 12.643
blade_zhi = hinge_z + bhalf;     // 23.957
post_top  = 12.2;                // 키베드 앵커 레일 상면
foot_w    = 11.8; foot_y0 = 157.5; foot_y1 = 172.5; foot_z0 = 9.2;  // 블레이드 고정단 발
pkt_w     = 12.1; pkt_y0  = 157.2; pkt_y1  = 172.8;                 // 키베드 드롭인 포켓
anchor_y0 = 155;  anchor_y1 = 174;
bridge_z0 = 24.0;  bridge_z1 = 36.0;          // 피벗 위 보강 브리지(꼬리 라이저)

/* ---------- 4. 사행 복귀 판스프링 ---------- */
t_leaf   = 5*ew;                 // 2.10 (5벽)
n_leaf   = 12;
leaf_y0  = 180;  leaf_y1 = 218;  // 세그먼트 길이 38, 중점 y=199 → 유효 반경 34
leaf_b   = 11.5;
leaf_gap = 2.2;                  // 출력(자유) 상태 간극 ≥ 2δ+0.4 = 2.21
preload  = 10.87;                // x0 — 설치 시 자유단 압축량
spine_z0 = 7;  spine_z1 = 11;    // 꼬리 스파인
conn_y0  = 176; conn_y1 = 180;   // 라이저 → 스파인 수직 웹 (앵커 레일 y=174 뒤)
leaf_z0  = 13.2;                 // = spine_z1 + leaf_gap — 판0은 뿌리에서만 스파인에 붙는다
rail_z0  = 55.7; rail_z1 = 61.7; // 리브 하면 45.6 = 설치 스택 상면(44.59)+노즈 1.0 → 접촉면
rail_y0  = 172;  rail_y1 = 186;

/* ---------- 5. 센싱 (v1.5 그대로 — 변경 없음) ---------- */
magnet_y = 110;  magnet_d = 2.9;  magnet_depth = 2.0;
pcb_y0 = 80;  pcb_y1 = 140;  pcb_t = 1.6;  pcb_lift = 0.2;
sensor_y = 110;  shim_h = 2.7;

/* ---------- 6. 다운스톱 / 가이드 콤 ---------- */
white_stop_y0 = 16; white_stop_y1 = 26;
black_stop_y0 = 62; black_stop_y1 = 70;
upstop_y0 = 196; upstop_y1 = 208; upstop_pad = 1.0;
combB2_y0 = 30;  combB2_y1 = 42;              // 백건 경계 8개
combB3_y0 = 72;  combB3_y1 = 78;              // 흑건 양옆 10개
combB1_y0 = 142; combB1_y1 = 154;             // 전 stem 경계 13개
fin_t = 1.3;  fin_top = 24;
mount_x = 8; mount_y_front = 5; mount_y_back = 224;

function dip_at(y)  = dip * (hinge_y - y) / hinge_y;
function stop_top(y)= key_rest_z - dip_at(y) - felt;
function stem_cx(j, p=stem_pitch) = p * (j + 0.5);
function stem_x0(j, p=stem_pitch) = p * j + key_gap/2;
function stem_w(p=stem_pitch)     = p - key_gap;

white_semis = [0,2,4,5,7,9,11];
black_semis = [1,3,6,8,10];
white_names = ["C","D","E","F","G","B_","A","B"];

assert(t_leaf  > 2*ew,  "판 두께는 최소 3벽");
assert(leaf_b  < stem_w(), "판 폭이 stem 폭을 넘음");
assert(blade_n*b_blade + (blade_n-1)*blade_sp < stem_w(), "블레이드가 stem 폭을 넘음");

/* ================= 건반 (모노리식) ================= */

// 교차 판스프링 1장: (y,z) 평면 안에서 ±45°, x 방향 폭 b_blade
//  s = +1 → 앞아래(고정) ~ 뒤위(가동),  s = -1 → 뒤아래(고정) ~ 앞위(가동)
module blade(cx, xo, s) {
    y0 = s > 0 ? blade_yf : blade_yb;
    translate([cx + xo, y0, blade_zlo])
        rotate([s*45, 0, 0])
            translate([-b_blade/2, -t_blade/2, 0])
                cube([b_blade, t_blade, L_blade]);
}
// 4장을 x 방향으로 교대 배치 → +45 와 −45 가 서로 닿지 않는다
module blades(cx) {
    step = b_blade + blade_sp;
    for (k = [0:blade_n-1]) blade(cx, (k - (blade_n-1)/2)*step, (k % 2 == 0) ? 1 : -1);
    blade_foot(cx);
}
// 블레이드 4장의 고정단을 하나로 묶은 발. 키베드 포켓에 위에서 떨어뜨려 넣고,
// 예하중 레일이 눌러 붙잡는다 → 레일을 풀면 12키가 통째로 빠지고 1키만 교체 가능.
module blade_foot(cx) {
    translate([cx-foot_w/2, foot_y0, foot_z0]) cube([foot_w, foot_y1-foot_y0, blade_zlo+0.2-foot_z0]);
}

// 사행 판스프링 (자유/출력 상태). inst=true 면 설치(예압) 상태를 근사 표시
module serpentine(cx, inst=false) {
    d   = preload / n_leaf;                       // 세그먼트당 상대 변위
    g   = inst ? leaf_gap - d : leaf_gap;
    translate([cx - leaf_b/2, leaf_y1-t_leaf, spine_z1]) cube([leaf_b, t_leaf, leaf_z0-spine_z1+t_leaf]); // 뿌리 기둥
    for (k = [0:n_leaf-1]) {
        z = leaf_z0 + k*(t_leaf + g);
        translate([cx - leaf_b/2, leaf_y0, z]) cube([leaf_b, leaf_y1-leaf_y0, t_leaf]);
        if (k < n_leaf-1) {                       // 접힘부: 짝수 k는 앞(y0), 홀수 k는 뒤(y1)
            fy = (k % 2 == 0) ? leaf_y0 : leaf_y1 - t_leaf;
            translate([cx - leaf_b/2, fy, z]) cube([leaf_b, t_leaf, t_leaf + g + 0.02]);
        }
    }
    // 자유단 노즈 (레일과 선접촉) — 최상단 판(짝수 인덱스 → 앞끝)
    ztop = leaf_z0 + (n_leaf-1)*(t_leaf + g);
    translate([cx, leaf_y0, ztop + t_leaf]) rotate([0,90,0])
        translate([0,0,-leaf_b/2]) cylinder(h=leaf_b, d=2.0);
}

// 건반 공통 골격: 라이저 + 웹 + 스파인 + 스프링
module key_back(cx, w, inst=false) {
    translate([cx-w/2, 152, bridge_z0]) cube([w, conn_y1-152, bridge_z1-bridge_z0]);      // 피벗 위 브리지
    translate([cx-w/2, conn_y0, spine_z1]) cube([w, conn_y1-conn_y0, bridge_z1-spine_z1]); // 수직 웹
    translate([cx-w/2, conn_y0, spine_z0]) cube([w, key_len-conn_y0, spine_z1-spine_z0]);  // 스파인
    blades(cx);
    serpentine(cx, inst);
}
module magnet_pocket(cx) { translate([cx, magnet_y, key_rest_z-0.01]) cylinder(h=magnet_depth, d=magnet_d); }
// 이웃 stem 격자칸 외포락 — 백건 앞블록 뒷부분을 자기 stem 폭으로 축소 (§2.1, v1.5에서 유지)
module stem_envelope(k, p) {
    translate([stem_cx(k,p)-(p+key_gap)/2, tail_y0, 0]) cube([p+key_gap, key_len, black_top+2]);
}
module white_key(i, j, p=stem_pitch, wp=white_pitch, n_stems=12, inst=false) {
    cx = stem_cx(j,p); w = stem_w(p);
    difference() {
        union() {
            translate([wp*i+key_gap/2, 0, key_rest_z]) cube([wp-key_gap, black_front_y, white_h]);
            translate([cx-w/2, tail_y0, key_rest_z]) cube([w, 158-tail_y0, white_h]);
            key_back(cx, w, inst);
        }
        for (k = [0:n_stems-1]) if (k != j) stem_envelope(k, p);
        magnet_pocket(cx);
    }
}
module black_key(j, p=stem_pitch, n_stems=12, inst=false) {
    cx = stem_cx(j,p); w = stem_w(p);
    difference() {
        union() {
            translate([cx-w/2, tail_y0, key_rest_z]) cube([w, 158-tail_y0, white_h]);
            translate([cx-w/2, black_front_y, key_rest_z]) difference() {
                cube([w, black_top_end-black_front_y, black_rise+white_h]);
                translate([-1,0,black_rise+white_h-10]) rotate([60,0,0]) cube([w+2,100,100]);
            }
            key_back(cx, w, inst);
        }
        for (k = [0:n_stems-1]) if (k != j) stem_envelope(k, p);
        magnet_pocket(cx);
    }
}
module keys12(p=stem_pitch, inst=false) {
    for (i = [0:6]) color("ivory")        white_key(i, white_semis[i], p, white_pitch, 12, inst);
    for (k = [0:4]) color([.12,.12,.12])  black_key(black_semis[k], p, 12, inst);
}

/* ================= 키베드 ================= */

module comb(y0, y1, xs, top=fin_top) {
    for (x = xs) translate([x - fin_t/2, y0, 0]) cube([fin_t, y1-y0, top]);
}
// 피벗 앵커 레일: 전 폭 연속 블록 + 건반별 y축 T 슬롯(뒤에서 삽입, 앞끝 막힘)
module pivot_rail(n, p, width) {
    difference() {
        translate([0, anchor_y0, 0]) cube([width, anchor_y1-anchor_y0, post_top]);
        for (j = [0:n-1]) translate([stem_cx(j,p)-pkt_w/2, pkt_y0, foot_z0])
            cube([pkt_w, pkt_y1-pkt_y0, post_top-foot_z0+1]);
    }
}
module bed(n=12, p=stem_pitch, width=164.5, blacks=black_semis) {
    ws_h = stop_top(white_stop_y0) - bed_h;     // 1.047
    bs_h = stop_top(black_stop_y0) - bed_h;     // 4.058
    difference() {
        intersection() {                       // 모듈 폭 밖으로 콤 핀이 삐져나가지 않게 클리핑
        union() {
            cube([width, bed_len, bed_h]);
            translate([0, white_stop_y0, 0]) cube([width, white_stop_y1-white_stop_y0, bed_h+ws_h]);
            for (k = blacks) translate([stem_cx(k,p)-stem_w(p)/2, black_stop_y0, 0])
                cube([stem_w(p), black_stop_y1-black_stop_y0, bed_h+bs_h]);
            comb(combB2_y0, combB2_y1, [for (i=[0:7]) white_pitch*i]);
            comb(combB3_y0, combB3_y1, [for (k=blacks) each [p*k, p*(k+1)]]);
            comb(combB1_y0, combB1_y1, [for (j=[0:n]) p*j]);
            pivot_rail(n, p, width);
            translate([0, upstop_y0, 0]) cube([width, upstop_y1-upstop_y0, bed_h+upstop_pad]);  // 업스톱(+TPU)
            translate([0, 220, 0]) cube([width, bed_len-220, rail_z1]);                          // 후방 벽 = 레일 지지
            for (x=[4,width-4]) for (y=[pcb_y0+4,pcb_y1-4]) translate([x,y,bed_h]) cylinder(h=pcb_lift,d=6);
        }
        cube([width, bed_len, rail_z1+10]); }
        translate([12, 86, -1]) cube([width-24, 48, bed_h+2]);                 // 필라멘트 절약 (PCB 아래)
        for (x=[mount_x,width-mount_x]) for (y=[mount_y_front,mount_y_back]) {
            translate([x,y,-1]) cylinder(h=rail_z1+2, d=4.4);
            translate([x,y,bed_h-3.5]) cylinder(h=4, d=13.5);
        }
        for (x=[mount_x,width-mount_x]) translate([x, 218, rail_z0-3]) rotate([-90,0,0]) cylinder(h=14, d=3.4);
    }
}
module bed12() bed(12, stem_pitch, 164.5, black_semis);
module bed13() bed(13, stem_pitch, 188.0, black_semis);
module bed3()  bed(3,  47/3,    47.0,  [1]);

// 예하중 레일 (별도 출력 · M3 2개로 높이 ±2mm 조절 · 전 건반 자유단을 한 번에 눌러 예압)
module rail(width=164.5) color([.55,.55,.6]) {
    difference() {
        union() {
            translate([0, rail_y0, rail_z0]) cube([width, 222-rail_y0, rail_z1-rail_z0]);
            translate([0, rail_y0, rail_z0-2]) cube([width, rail_y1-rail_y0, 2]);   // 접촉 리브(TPU 2mm 자리)
        }
        for (x=[mount_x,width-mount_x]) translate([x, 216, rail_z0+3]) rotate([-90,0,0]) {
            cylinder(h=10, d=3.4); translate([0,0,4]) cylinder(h=8, d=6.5);
        }
    }
}
/* ================= 전자부 자리표시 ================= */
module pcb(width=164.5, n=12, p=stem_pitch) {
    translate([0,pcb_y0,bed_h+pcb_lift]) color([.1,.45,.2]) cube([width,pcb_y1-pcb_y0,pcb_t]);
    for (j=[0:n-1]) translate([stem_cx(j,p)-2, sensor_y-1.5, bed_h+pcb_lift+pcb_t]) {
        color([.75,.75,.75]) cube([4,3,shim_h]);
        translate([0,0,shim_h]) color([.15,.15,.15]) cube([4,3,1.5]);
    }
    translate([width-32,84,bed_h+pcb_lift+pcb_t]) color([.2,.5,.25]) cube([21,51,4]);
    translate([width-70,130,bed_h+pcb_lift+pcb_t]) color([.2,.2,.2]) cube([31,8,4.6]);
}
module magnets(n=12, p=stem_pitch) { for (j=[0:n-1]) translate([stem_cx(j,p),magnet_y,key_rest_z]) color("red") cylinder(h=2,d=3); }

module pressed(a=press_angle) {
    translate([0,hinge_y,hinge_z]) rotate([a,0,0]) translate([0,-hinge_y,-hinge_z]) children();
}
module assembly(width=164.5, n=12, p=stem_pitch, board=true, cover=true, press_idx=-1) {
    bed(n,p,width,black_semis);
    if (board) { pcb(width,n,p); magnets(n,p); rail(width); }
    for (i=[0:6]) if (white_semis[i]==press_idx) pressed() color([1,.6,.3]) white_key(i,white_semis[i],p,white_pitch,n,true);
                  else color("ivory") white_key(i,white_semis[i],p,white_pitch,n,true);
    for (k=[0:4]) if (black_semis[k]==press_idx) pressed() color([1,.6,.3]) black_key(black_semis[k],p,n,true);
                  else color([.12,.12,.12]) black_key(black_semis[k],p,n,true);
}
module exploded() {
    bed12(); translate([0,0,-30]) pcb(); translate([0,0,60]) keys12(inst=true); translate([0,0,110]) rail();
}
module section_side() {
    cx = stem_cx(0);
    intersection() { assembly(cover=false); translate([cx-2.5,-1,-10]) cube([5,bed_len+2,120]); }
}
module full88() {
    bed3(); keys3();
    for (m=[0:5]) translate([47+164.5*m,0,0]) assembly(board=false);
    translate([47+164.5*6,0,0]) { bed13(); keys12(inst=true); }
    translate([-14,-22,-18]) color([.82,.7,.5]) cube([1250,275,18]);
    for (y=[20,190]) translate([-14,y,-3]) color([.8,.8,.82]) cube([1250,25,3]);
}
module keys3() { p=47/3;
    color("ivory") white_key(0,0,p,23.5,3,true);
    color([.12,.12,.12]) black_key(1,p,3,true);
    color("ivory") white_key(1,2,p,23.5,3,true);
}
/* ================= 단계 0 쿠폰 ================= */
module coupons() {
    for (i=[0:2]) translate([i*20,0,0]) {        // T1/T2: 판 두께 4/5/6벽 고정-가이드 쿠폰
        t = (4+i)*ew;
        translate([0,0,0]) cube([leaf_b, 40, t]);
        for (y=[0,40-6]) translate([-4,y,0]) cube([leaf_b+8,6,8]);
    }
    for (i=[0:2]) translate([70+i*18,0,0]) {     // T6: 블레이드 두께 2/3/4벽
        tb=(2+i)*ew; cube([12,4.5,post_top]);
        translate([6,blade_yf-hinge_y+bhalf,post_top]) rotate([45,0,0]) translate([-b_blade/2,-tb/2,0]) cube([b_blade,tb,L_blade]);
    }
    for (i=[0:3]) translate([130+i*20,0,0])      // T7: 아치 Q = 1.5/1.8/2.0/2.2
        linear_extrude(3) polygon([[0,0],[16,0],[16,0.42],[8,0.42+0.42*(1.5+0.25*i)],[0,0.42]]);
}
module ixcheck() { intersection() { keys12(inst=true); union() { bed12(); rail(); } } }

/* ================= 출력 선택 ================= */
if (PART=="assembly")  assembly();
if (PART=="pressed")   assembly(press_idx=5);
if (PART=="exploded")  exploded();
if (PART=="section")   section_side();
if (PART=="bed12")     bed12();
if (PART=="bed13")     bed13();
if (PART=="bed3")      bed3();
if (PART=="keys12")    keys12(inst=true);
if (PART=="free_key")  white_key(0,0);
if (PART=="key_white") white_key(0,0);
if (PART=="key_black") black_key(1);
if (PART=="rail")      rail();
if (PART=="coupons")   coupons();
if (PART=="full88")    full88();
if (PART=="ixcheck")   ixcheck();
