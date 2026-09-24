// Toccata — 옥타브 모듈 키베드·건반 파라메트릭 모델 (설계 문서 v1.5)
// 좌표계: x = 모듈 가로(왼쪽 0), y = 건반 길이(0 = 연주자 앞, 216 = 뒤), z = 위
// 건반은 밑면 z=0으로 모델링(밑면이 베드에 닿게 출력). 키베드는 바닥 z=0, 상면 z=bed_h.
// 조립 시 건반 밑면(정지) = key_rest_z = bed_h + key_elev + 0.2 = 18.3
// 원작 개념 참고: joewing/organ (핀 일체 힌지 + 30° 열린 요람 + 꼬리 당김 리턴). 코드는 독자 작성.
//
//   openscad -o out.png --preview --viewall --autocenter -D 'PART="assembly"' toccata.scad
//   PART: assembly | pressed | exploded | section | bed12 | bed13 | bed3 | keys12 |
//         white_C..white_B | black | fallboard | coupons | full88 | ixcheck

PART = "assembly";
$fn = 48;

// ---------- §1·§2 파라미터 ----------
white_pitch   = 23.5;
stem_pitch    = 164.5/12;          // 13.7083 — 균등. 이웃 stem 외포락 컷으로 간섭 제거(§2.1)
key_gap       = 1.6;
key_len       = 216;
white_h       = 12.7;
black_h       = white_h + 10.16;   // 22.86
black_front_y = 50.8;
black_top_end = 152.4;
tail_y0       = black_front_y - key_gap;   // 49.2 — 꼬리가 앞블록과 1.6 겹쳐 연결
hinge_y       = 165;  hinge_z = 3.6;  hinge_r = 3.0;  cradle_r = hinge_r + 0.1;
slot_w  = 7.0;  slot_y0 = 153;  slot_len = 42;   // → y 195 (스프링 포켓 앞 7mm 벽)
fin_w   = 6.7;  fin_y0  = 157;  fin_len  = 26;   // → y 183
key_elev = 12.1;  bed_h = 6;  felt = 1.5;  punch = 0.3;
key_rest_z = bed_h + key_elev + 0.2;             // 18.3
cradle_z   = key_rest_z + hinge_z + (cradle_r - hinge_r);   // 22.0 (핀 착좌 시 하면 18.3)
dip = 10.8;
press_angle = atan(dip / hinge_y);               // 3.75°
stand_y0 = 165;  stand_y1 = 178;  stand_top = bed_h + key_elev;      // 18.1
stop_y0  = 208;  stop_y1  = 216;                                      // 정지 블록
white_stop_y0 = 16; white_stop_y1 = 26;                               // 마운트 y=5와 분리
black_stop_y0 = 52; black_stop_y1 = 60;
magnet_y = 110;  magnet_d = 2.9;  magnet_depth = 2.0;                 // 리밍 후 면일치
pin_y = 204.5;  pin_d = 1.5;  pin_z = 2.6;
hook_y0 = 202;  hook_y1 = 207;  hook_w = 4;  hook_h = 4.5;            // 스프링 훅 개구
spring_hole_d = 5.5;
pcb_y0 = 80;  pcb_y1 = 140;  pcb_t = 1.6;  pcb_lift = 0.2;            // PCB 상면 = 베드 +1.8
sensor_y = 110;  shim_h = 2.7;                                        // Honeywell 로트
notch_x = 148.5; notch_w = 5; notch_h = 4;                            // fin10↔fin11 사이
mount_x = 8; mount_y_front = 5; mount_y_back = 192;
mount_cb_d = 13.5; mount_cb_h = 3.5; slot_hole_x = 6.4; slot_hole_w = 4.4;
fb_y0 = 156;  fb_leg_y0 = 216;  fb_leg_y1 = 224;  fb_t = 2;

function dip_at(y) = dip * (hinge_y - y) / hinge_y;
function stop_top(y) = key_rest_z - dip_at(y) - felt;     // 다운스톱 블록 상면
function stem_cx(j, p=stem_pitch) = p * (j + 0.5);
function stem_x0(j, p=stem_pitch) = p * j + key_gap/2;
function stem_w(p=stem_pitch)     = p - key_gap;

white_semis = [0,2,4,5,7,9,11];
black_semis = [1,3,6,8,10];
white_names = ["C","D","E","F","G","A","B"];

// ---------- 건반 ----------
module hinge_bar(j, p) { translate([stem_x0(j,p), hinge_y, hinge_z]) rotate([0,90,0]) cylinder(h=stem_w(p), r=hinge_r); }
module guide_slot(j, p) { translate([stem_cx(j,p)-slot_w/2, slot_y0, -1]) cube([slot_w, slot_len, black_h+2]); }
module magnet_pocket(j, p) { translate([stem_cx(j,p), magnet_y, -0.01]) cylinder(h=magnet_depth, d=magnet_d); }
// 횡핀 구멍 + 아래로 열린 훅 개구 (스프링이 핀에 걸리도록)
module spring_anchor(j, p) {
    translate([stem_x0(j,p)-1, pin_y, pin_z]) rotate([0,90,0]) cylinder(h=stem_w(p)+2, d=pin_d);
    translate([stem_cx(j,p)-hook_w/2, hook_y0, -0.01]) cube([hook_w, hook_y1-hook_y0, hook_h]);
}
// 이웃 stem 격자칸 외포락 (폭 p+gap) — 앞블록 뒷부분을 자기 stem 폭으로 축소
module stem_envelope(k, p) { translate([stem_cx(k,p)-(p+key_gap)/2, tail_y0, -1]) cube([p+key_gap, key_len, black_h+2]); }
module key_cuts(j, p, n_stems) {
    for (k = [0:n_stems-1]) if (k != j) stem_envelope(k, p);
    guide_slot(j,p); magnet_pocket(j,p); spring_anchor(j,p);
}
module white_key(i, j, p=stem_pitch, wp=white_pitch, n_stems=12) {
    difference() {
        union() {
            translate([wp*i+key_gap/2, 0, 0]) cube([wp-key_gap, black_front_y, white_h]);   // 앞블록
            translate([stem_x0(j,p), tail_y0, 0]) cube([stem_w(p), key_len-tail_y0, white_h]); // 꼬리
        }
        key_cuts(j,p,n_stems);
    }
    hinge_bar(j,p);
}
module black_key(j, p=stem_pitch, n_stems=12) {
    w = stem_w(p);
    difference() {
        union() {
            translate([stem_x0(j,p), tail_y0, 0]) cube([w, key_len-tail_y0, white_h]);       // 꼬리
            translate([stem_x0(j,p), black_front_y, 0]) difference() {                        // 융기부
                cube([w, black_top_end-black_front_y, black_h]);
                translate([-1, 0, black_h-10]) rotate([60,0,0]) cube([w+2, 100, 100]);        // 전면 60° 챔퍼
            }
        }
        key_cuts(j,p,n_stems);
    }
    hinge_bar(j,p);
}
module keys12(p=stem_pitch, extra_c=false) {
    n = extra_c ? 13 : 12;
    for (i = [0:6]) color("ivory") white_key(i, white_semis[i], p, white_pitch, n);
    for (k = [0:4]) color([0.12,0.12,0.12]) black_key(black_semis[k], p, n);
    if (extra_c) color("ivory") white_key(7, 12, p, white_pitch, n);      // C8
}
module keys3() {
    p = 47/3;
    color("ivory") white_key(0, 0, p, 23.5, 3);
    color([0.12,0.12,0.12]) black_key(1, p, 3);
    color("ivory") white_key(1, 2, p, 23.5, 3);
}

// ---------- 키베드 ----------
module cradle_cut(j, p) {
    translate([stem_x0(j,p)-1, hinge_y, cradle_z]) {
        rotate([0,90,0]) cylinder(h=stem_w(p)+2, r=cradle_r);
        rotate([-30,0,0]) translate([0,-cradle_r,0]) cube([stem_w(p)+2, cradle_r*2, 30]);
    }
}
module key_stand(j, p) {
    x0 = stem_x0(j,p); w = stem_w(p); cx = stem_cx(j,p);
    fin_top = key_rest_z + white_h + 3;                     // 백건 윗면 +3 = 34.0
    difference() {
        union() {
            translate([x0, stand_y0, 0]) cube([w, stand_y1-stand_y0, stand_top]);
            translate([cx-fin_w/2, fin_y0, 0]) cube([fin_w, fin_len, fin_top]);
        }
        cradle_cut(j,p);
        // fin 뒤 모서리 45° 모따기 (위로만 걸침)
        translate([cx-fin_w/2-1, fin_y0+fin_len, fin_top]) rotate([45,0,0]) cube([fin_w+2, 14, 14]);
    }
}
module bed(n_stems=12, p=stem_pitch, width=164.5, black_list=black_semis) {
    ws_h = stop_top(white_stop_y0) - bed_h;      // 1.047
    bs_h = stop_top(black_stop_y0) - bed_h;      // 3.404
    difference() {
        union() {
            cube([width, key_len, bed_h]);
            for (j = [0:n_stems-1]) key_stand(j,p);
            translate([0, stop_y0, 0]) cube([width, stop_y1-stop_y0, key_rest_z-felt-punch]);   // 정지 16.5
            translate([0, white_stop_y0, 0]) cube([width, white_stop_y1-white_stop_y0, bed_h+ws_h]);
            for (k = black_list) translate([stem_cx(k,p)-(p-key_gap)/2, black_stop_y0, 0])
                cube([p-key_gap, black_stop_y1-black_stop_y0, bed_h+bs_h]);
            for (x = [4, width-4]) for (y = [pcb_y0+4, pcb_y1-4]) translate([x,y,bed_h]) cylinder(h=pcb_lift, d=6);
        }
        for (j = [0:n_stems-1]) translate([stem_cx(j,p), pin_y, -1]) cylinder(h=bed_h+2, d=spring_hole_d);
        translate([12, 28, -1]) cube([width-24, 14, bed_h+2]);          // 필라멘트 절약 (다운스톱 회피)
        translate([12, 142, -1]) cube([width-24, 10, bed_h+2]);
        translate([notch_x, stand_y0-1, bed_h-0.01]) cube([notch_w, stand_y1-stand_y0+2, notch_h]);
        translate([notch_x, stop_y0-1,  bed_h-0.01]) cube([notch_w, stop_y1-stop_y0+2, notch_h]);
        for (x = [mount_x, width-mount_x]) for (y = [mount_y_front, mount_y_back]) {
            hull() for (dx = [-(slot_hole_x-slot_hole_w)/2, (slot_hole_x-slot_hole_w)/2])
                translate([x+dx, y, -1]) cylinder(h=bed_h+2, d=slot_hole_w);
            translate([x, y, bed_h-mount_cb_h]) cylinder(h=mount_cb_h+1, d=mount_cb_d);
        }
    }
}
module bed12() bed(12, stem_pitch, 164.5, black_semis);
module bed13() bed(13, stem_pitch, 188.0, black_semis);
module bed3()  bed(3, 47/3, 47.0, [1]);

// ---------- 전자부·기구 자리표시 ----------
module pcb(width=164.5, n=12, p=stem_pitch) {
    translate([0, pcb_y0, bed_h+pcb_lift]) color([0.1,0.45,0.2]) cube([width, pcb_y1-pcb_y0, pcb_t]);
    for (j = [0:n-1]) translate([stem_cx(j,p)-2, sensor_y-1.5, bed_h+pcb_lift+pcb_t]) {
        color([0.75,0.75,0.75]) cube([4,3,shim_h]);
        translate([0,0,shim_h]) color([0.15,0.15,0.15]) cube([4,3,1.5]);      // SS49E 눕힘, 상면 6.0
    }
    translate([width-32, 84, bed_h+pcb_lift+pcb_t]) color([0.2,0.5,0.25]) cube([21,51,4]);   // Pico 직납, USB 에지 y=135
    translate([width-70, 130, bed_h+pcb_lift+pcb_t]) color([0.2,0.2,0.2]) cube([31,8,4.6]);  // 먹스 DIP-24 (x 방향)
}
module magnets(n=12, p=stem_pitch, z=key_rest_z) { for (j=[0:n-1]) translate([stem_cx(j,p), magnet_y, z]) color("red") cylinder(h=2, d=3); }
module springs(n=12, p=stem_pitch) { for (j=[0:n-1]) translate([stem_cx(j,p), pin_y, -18]) color([0.6,0.6,0.65]) cylinder(h=key_rest_z+pin_z+18, d=5, $fn=16); }
// 폴보드: 덮개판 + 베드 뒤(y>216) 다리 → 건반과 간섭 없음
module fallboard(width=164.5) {
    top = key_rest_z + white_h + 3 + 3;      // fin 상단 +3 = 37.0
    color([0.25,0.25,0.28]) {
        translate([0, fb_y0, top]) cube([width, fb_leg_y1-fb_y0, fb_t]);
        for (x = [0, width-10]) translate([x, fb_leg_y0, 0]) cube([10, fb_leg_y1-fb_leg_y0, top]);
    }
}
module pressed(angle=press_angle) {
    translate([0, hinge_y, key_rest_z+hinge_z]) rotate([angle,0,0]) translate([0,-hinge_y,-(key_rest_z+hinge_z)]) children();
}
module assembly(width=164.5, n=12, p=stem_pitch, board=true, cover=true, press_idx=-1, keys=true) {
    bed(n, p, width, black_semis);
    if (board) { pcb(width,n,p); magnets(n,p); springs(n,p); }
    if (keys) translate([0,0,key_rest_z]) {
        for (i = [0:6]) if (white_semis[i]==press_idx) pressed() color([1,0.6,0.3]) white_key(i, white_semis[i], p, white_pitch, n);
                        else color("ivory") white_key(i, white_semis[i], p, white_pitch, n);
        for (k = [0:4]) if (black_semis[k]==press_idx) pressed() color([1,0.6,0.3]) black_key(black_semis[k], p, n);
                        else color([0.12,0.12,0.12]) black_key(black_semis[k], p, n);
    }
    if (cover) fallboard(width);
}
module exploded() {
    bed12(); springs();
    translate([0,0,-26]) pcb();
    translate([0,0,46]) keys12();
    translate([0,0,46]) magnets(z=0);
    translate([0,0,92]) fallboard();
}
module section_side() {
    cx = stem_cx(0);
    intersection() { assembly(cover=false); translate([cx-2.5,-1,-30]) cube([5, key_len+2, 130]); }
}
module full88() {
    bed3(); translate([0,0,key_rest_z]) keys3();
    for (m = [0:5]) translate([47+164.5*m,0,0]) assembly(cover=false, board=false);
    translate([47+164.5*6,0,0]) { bed13(); translate([0,0,key_rest_z]) keys12(extra_c=true); }
    translate([-14,-22,-18]) color([0.82,0.7,0.5]) cube([1250,260,18]);          // 합판 베이스
    translate([-14,174.5,-3]) color([0.8,0.8,0.82]) cube([1250,25,3]);           // 평철 매립 (스프링 통로 회피)
}
// ---------- 단계 0 쿠폰 ----------
module coupons() {
    for (i = [0:2]) translate([i*30,0,0]) difference() {          // 요람 r 3.0/3.1/3.2
        cube([26,40,cradle_z-key_rest_z+bed_h+key_elev+4]);
        cr = 3.0+0.1*i;
        translate([-1,20,cradle_z]) { rotate([0,90,0]) cylinder(h=28, r=cr); rotate([-30,0,0]) translate([0,-cr,0]) cube([28,cr*2,30]); }
    }
    for (i = [0:2]) for (k = [0:1]) translate([i*20, 50+k*50, 0]) difference() {   // 슬롯 3종 × hinge_z 2종
        union() { cube([stem_w(),45,white_h]); translate([0,20,[3.6,3.0][k]]) rotate([0,90,0]) cylinder(h=stem_w(), r=hinge_r); }
        sw = 6.7+0.3*i;
        translate([stem_w()/2-sw/2, 25, -1]) cube([sw,15,white_h+2]);
    }
    for (i = [0:2]) translate([70+i*12,0,0]) difference() { cube([10,10,4]); translate([5,5,-0.01]) cylinder(h=magnet_depth, d=2.9+0.1*i); }
    for (i = [0:2]) translate([70+i*12,14,0]) cube([6,5,[1.9,2.4,2.7][i]]);       // 심: 로트별 (§3.1)
}
// 간섭 검사용: 건반 전체 ∩ (키베드 + 폴보드) — 비어 있어야 함
module ixcheck() {
    intersection() {
        translate([0,0,key_rest_z]) keys12();
        union() { bed12(); fallboard(); springs(); }
    }
}

// ---------- 출력 선택 ----------
if (PART=="assembly")  assembly();
if (PART=="pressed")   assembly(press_idx=4);
if (PART=="exploded")  exploded();
if (PART=="section")   section_side();
if (PART=="bed12")     bed12();
if (PART=="bed13")     bed13();
if (PART=="bed3")      bed3();
if (PART=="keys12")    keys12();
if (PART=="black")     black_key(1);
if (PART=="fallboard") fallboard();
if (PART=="coupons")   coupons();
if (PART=="full88")    full88();
if (PART=="ixcheck")   ixcheck();
for (i = [0:6]) if (PART == str("white_", white_names[i])) white_key(i, white_semis[i]);
