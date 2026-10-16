// Toccata v3.0 "해머포크" — 중력복귀 회전해머 + 포크 양방향 구속 + 해머측 광학 dt 센싱
// 좌표계: x = 모듈 가로(왼쪽 0), y = 건반 길이(0 = 연주자 앞끝), z = 위(키베드 바닥 0)
//
//   설계 근거: 타건감의 본질은 정적 무게가 아니라 지렛대의 제곱이다.
//   해머 질량 m_h 가 레버비 R 로 반사될 때
//        손끝 정적 힘 = m_h · R      (1승)
//        손끝 등가관성 = m_h · R²    (2승)
//   R = 2.00 하나로 강봉 21 g 이 정적 46 gf 와 관성 99 g 을 동시에 만든다.
//   v2.0 일체형 건반의 등가관성 5.2 g 대비 19배.
//
//   openscad -o out.png --preview --viewall --autocenter -D 'PART="assembly"' toccata-v3.scad
//   PART: assembly | pressed | section | exploded | octave | key_white | key_black
//         | hammer | vane | frame | pcb | ixcheck

PART = "assembly";
$fn = 36;

/* ═══ 0. 피치 · 키 ═══ */
white_pitch = 23.5;
semi_pitch  = 164.5/12;            // 13.70833
key_gap     = 1.6;
key_len     = 216;
key_bot     = 15;                  // 키 하면 (키베드 바닥 0 기준)
key_top     = 30;                  // 키 상면 — 앞부분 두께 15
tail_top    = 21;                  // ★ 꼬리는 6mm 로 낮춘다 (베인·센서 자리를 비우려고)
tail_y0     = 172;
key_front_w = white_pitch - key_gap;   // 21.9
key_stem_w  = semi_pitch - key_gap;    // 12.108
key_tail_w  = 8.0;                 // ★ 꼬리를 좁혀 베인이 지나갈 옆틈 2.85mm 확보
black_front_y = 50.8;  black_top_end = 152.4;  black_rise = 10.16;

/* ═══ 1. 회전 기하 ═══ */
dip      = 10.8;
bal_y    = 165;                    // 밸런스 피벗
bal_z    = 22.5;                   // 키 두께 중앙
key_ang  = atan(dip/bal_y);        // 3.7503°
fork_y   = 214.5;                  // 포크 = 캡스턴. 유효 꼬리팔 c = 49.5
tail_lift = dip * (fork_y-bal_y)/bal_y;   // 3.240 — 꼬리 상승량

ham_piv_y = 222;  ham_piv_z = 36;  // 해머 축 (밸런스핀보다 뒤, 12키 모듈당 1개 관통)
knuckle_b = 7.5;                   // 힐 접촉반경 — 포크가 미는 점
ham_ang   = tail_lift/knuckle_b*180/PI;   // 24.75°
wt_r      = 50;                    // 웨이트 중심반경 → 헤드 행정 21.6, R = 2.00
arm_rest_ang = 6.84;               // 정지 시 암 경사 (앞으로 올라감)

/* ═══ 2. 해머 ═══ */
arm_len = 62;  arm_w = 10;  arm_t = 6;
wt_d = 10;  wt_len = 34;           // Ø10 스틸 환봉 34mm = 21.0 g
knuckle_d = 4;                     // Ø4 너클핀 (SUS)
piv_d = 2;                         // Ø2 SUS 축 + PTFE 부싱

/* ═══ 3. 광학 센싱 ═══ */
vane_r      = 40;                  // 베인 반경 → y = 182, 행정 17.28 (증폭 1.60배)
vane_y      = ham_piv_y - vane_r;  // 182
vane_x_off  = 5.85;                // ★ 키 중심에서 옆으로 — 좁힌 꼬리 옆틈으로 지나간다
vane_t      = 1.5;                 // 흑색 PETG (자연색은 940nm 를 투과한다)
vane_z0     = 17;  vane_z1 = 41;
vane_win_z0 = 22.12;               // 정지 시 창 하단
vane_win_h  = 6.20;                // = 0.2 레이어 × 31. ★ 반드시 레이어 정수배
beam_z      = 37;                  // ITR9608 광로 높이
pcb_z       = 31.6;                // 센서 PCB 상면
sens_w = 6.4; sens_h = 10.8; sens_slot = 5.0;

/* ═══ 4. 스톱 ═══ */
upstop_z   = 63;                   // PORON 4701-30 3T — 반발 e ≤ 0.15 (백체크를 재료로 대체)
front_felt_y = 18;                 // 프론트 펀칭 펠트 2T (하드 백스톱)
downstop_z = 5;                    // EVA 2T — 88키 정지 높이를 한 줄로 정의
bed_h = 5;

function stem_cx(j) = semi_pitch*(j+0.5);
white_semis = [0,2,4,5,7,9,11];
black_semis = [1,3,6,8,10];

/* ═══════════ 건반 ═══════════ */
module fork(cx) {                                   // U자 포크 + M3 셋스크류 자리
    difference() {
        translate([cx-6, fork_y-5, tail_top-0.01]) cube([12, 10, fork_top_h()]);
        translate([cx-knuckle_d/2-0.6, fork_y-6, tail_top+9])
            cube([knuckle_d+1.2, 12, fork_top_h()]);          // 핀이 들어앉는 U홈
        translate([cx, fork_y, tail_top-1]) cylinder(h=10, d=2.9);  // M3 탭
    }
}
function fork_top_h() = (ham_piv_z - knuckle_d/2) - tail_top + 2;   // 핀 밑까지 + 여유

module key_body(i, j, black=false) {
    cx = stem_cx(j);
    union() {
        if (black) {
            translate([cx-key_stem_w/2, black_front_y-key_gap, key_bot])
                cube([key_stem_w, tail_y0-black_front_y+key_gap, key_top-key_bot]);
            translate([cx-key_stem_w/2, black_front_y, key_top]) difference() {
                cube([key_stem_w, black_top_end-black_front_y, black_rise]);
                translate([-1,0,black_rise-8]) rotate([60,0,0]) cube([key_stem_w+2,90,90]);
            }
        } else {
            translate([white_pitch*i+key_gap/2, 0, key_bot])
                cube([key_front_w, black_front_y, key_top-key_bot]);
            translate([cx-key_stem_w/2, black_front_y-key_gap, key_bot])
                cube([key_stem_w, tail_y0-black_front_y+key_gap, key_top-key_bot]);
        }
        translate([cx-key_tail_w/2, tail_y0-2, key_bot])            // 낮고 좁은 꼬리
            cube([key_tail_w, key_len-tail_y0+2, tail_top-key_bot]);
        fork(cx);
    }
}
module key(i, j, black=false) {
    cx = stem_cx(j);
    difference() {
        key_body(i, j, black);
        translate([cx-20, bal_y, bal_z]) rotate([0,90,0]) cylinder(h=40, d=piv_d+0.3);  // 밸런스핀
        translate([cx-20, front_felt_y, key_bot-0.01]) rotate([0,90,0]) cylinder(h=40, d=3.2);
    }
}

/* ═══════════ 해머 ═══════════ */
module vane() {                                     // 창 1개 · 엣지 2개 → dt 측정
    difference() {
        translate([-vane_t/2, vane_y-9, vane_z0]) cube([vane_t, 18, vane_z1-vane_z0]);
        translate([-vane_t, vane_y-10, vane_win_z0]) cube([vane_t*3, 20, vane_win_h]);
    }
}
module hammer(cx) {
    translate([cx, ham_piv_y, ham_piv_z]) rotate([-arm_rest_ang,0,0]) translate([-cx,-ham_piv_y,-ham_piv_z]) {
        color([0.16,0.16,0.18]) {
            translate([cx-arm_w/2, ham_piv_y-arm_len, ham_piv_z-arm_t/2])
                cube([arm_w, arm_len+8, arm_t]);                       // 암
            translate([cx+arm_w/2-0.01, vane_y-9, ham_piv_z-arm_t/2])  // 베인 브래킷
                cube([vane_x_off-arm_w/2+vane_t/2+0.5, 18, arm_t]);
            translate([cx+vane_x_off, 0, 0]) vane();
        }
        color([0.62,0.64,0.68]) {                                      // Ø10 스틸 환봉 21.0 g
            translate([cx-wt_len/2, ham_piv_y-wt_r, ham_piv_z]) rotate([0,90,0])
                cylinder(h=wt_len, d=wt_d);
            translate([cx-9, ham_piv_y-knuckle_b, ham_piv_z]) rotate([0,90,0])   // Ø4 너클핀
                cylinder(h=18, d=knuckle_d);
            translate([cx-9, ham_piv_y, ham_piv_z]) rotate([0,90,0])             // Ø2 축
                cylinder(h=18, d=piv_d);
        }
    }
}

/* ═══════════ 키베드 · 전자 ═══════════ */
module sensor(cx) {
    translate([cx+vane_x_off, vane_y, beam_z]) {
        color([0.12,0.12,0.12]) for (s=[-1,1])
            translate([s*(sens_slot/2), -sens_w/2, -(beam_z-pcb_z)])
                cube([2.2*(s>0?1:-1), sens_w, sens_h], center=false);
    }
}
module pcb(width) {
    color([0.10,0.42,0.22]) translate([0, vane_y-11, pcb_z-1.6]) cube([width, 22, 1.6]);
}
module frame(width) {
    color([0.80,0.78,0.74]) {
        cube([width, key_len+34, bed_h]);                                   // 바닥판
        translate([0, front_felt_y-6, bed_h]) cube([width, 12, downstop_z-bed_h]);   // 다운스톱 받침
        translate([0, bal_y-5, bed_h]) cube([width, 10, bal_z-bed_h-1]);            // 밸런스 레일
        translate([0, ham_piv_y-5, bed_h]) cube([width, 10, ham_piv_z-bed_h]);      // 해머 축 레일
        translate([0, vane_y-13, bed_h]) cube([4, 26, pcb_z-bed_h-1.6]);            // PCB 스탠드오프
        translate([width-4, vane_y-13, bed_h]) cube([4, 26, pcb_z-bed_h-1.6]);
        translate([0, 150, upstop_z]) cube([width, 40, 6]);                          // 업스톱 레일
        translate([0, ham_piv_y-8, upstop_z-18]) cube([6, 16, 24]);                  // 레일 지주
        translate([width-6, ham_piv_y-8, upstop_z-18]) cube([6, 16, 24]);
    }
    color([0.76,0.33,0.25]) {                                                        // 감쇠재
        translate([0, 150, upstop_z-3]) cube([width, 40, 3]);                        // PORON 3T
        translate([0, front_felt_y-6, downstop_z]) cube([width, 12, 2]);             // EVA 2T
    }
}

/* ═══════════ 조립 ═══════════ */
module pressed_key(a=key_ang) {
    translate([0,bal_y,bal_z]) rotate([a,0,0]) translate([0,-bal_y,-bal_z]) children();
}
module pressed_ham(a=-1) {
    ang = (a<0) ? ham_ang : a;
    translate([0,ham_piv_y,ham_piv_z]) rotate([ang,0,0]) translate([0,-ham_piv_y,-ham_piv_z]) children();
}
module octave(width=164.5, press=-1) {
    frame(width); pcb(width);
    for (j=[0:11]) sensor(stem_cx(j));
    for (i=[0:6]) {
        j = white_semis[i];
        if (j==press) { pressed_key() color([1,0.62,0.30]) key(i,j);  pressed_ham() hammer(stem_cx(j)); }
        else          { color("ivory") key(i,j);                      hammer(stem_cx(j)); }
    }
    for (k=[0:4]) {
        j = black_semis[k];
        if (j==press) { pressed_key() color([1,0.62,0.30]) key(0,j,true); pressed_ham() hammer(stem_cx(j)); }
        else          { color([0.13,0.13,0.13]) key(0,j,true);            hammer(stem_cx(j)); }
    }
}
module section_side() {
    cx = stem_cx(0);
    intersection() { octave(); translate([cx-3, -2, -2]) cube([6, key_len+40, 90]); }
}
module section_pressed() {
    cx = stem_cx(0);
    intersection() { octave(press=0); translate([cx-3, -2, -2]) cube([6, key_len+40, 90]); }
}
module exploded() {
    frame(164.5);
    translate([0,0,40]) { pcb(164.5); for (j=[0:11]) sensor(stem_cx(j)); }
    translate([0,0,88]) for (j=[0:11]) hammer(stem_cx(j));
    translate([0,0,150]) { for (i=[0:6]) color("ivory") key(i,white_semis[i]);
                           for (k=[0:4]) color([0.13,0.13,0.13]) key(0,black_semis[k],true); }
}
module ixcheck() {
    intersection() {
        union() { for (i=[0:6]) key(i,white_semis[i]); for (k=[0:4]) key(0,black_semis[k],true); }
        union() { for (j=[0:11]) hammer(stem_cx(j)); pcb(164.5); for (j=[0:11]) sensor(stem_cx(j)); }
    }
}

if (PART=="assembly")  octave();
if (PART=="pressed")   octave(press=0);
if (PART=="section")   section_side();
if (PART=="sectionp")  section_pressed();
if (PART=="exploded")  exploded();
if (PART=="octave")    octave();
if (PART=="key_white") key(0,0);
if (PART=="key_black") key(0,1,true);
if (PART=="hammer")    hammer(stem_cx(0));
if (PART=="vane")      translate([0,0,0]) vane();
if (PART=="frame")     frame(164.5);
if (PART=="ixcheck")   ixcheck();
