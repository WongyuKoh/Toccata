// Host test for src/keys.c: synthesizes Hall readings of keys moving at known speeds
// (with ADC noise and a wrapping microsecond clock) and checks the events that come out.
// Run: make -C firmware/test
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "keys.h"

#define DT_US 110          // one scan of 12 keys is about 100-110 us on the board
#define T0 0xFFFE0000u     // the clock wraps during the run

static int failures, checks;
#define CHECK(cond, ...)                                                   \
    do {                                                                   \
        checks++;                                                          \
        if (!(cond)) {                                                     \
            failures++;                                                    \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);                   \
            printf(__VA_ARGS__);                                           \
            printf("\n");                                                  \
        }                                                                  \
    } while (0)

// Independent copy of the magnet model (on-axis field of a Ø5 x 2 disc magnet).
static double field(double z) {
    double zl = z + 2.0;
    return zl / sqrt(6.25 + zl * zl) - z / sqrt(6.25 + z * z);
}
static double gap_rest(bool black) { return black ? 13.35 : 10.82; }
static double gap_bottom(bool black) { return black ? 5.32 : 5.60; }
static double travel_mm(bool black) { return gap_rest(black) - gap_bottom(black); }
static double front_ratio(bool black) { return black ? 1.18 : 1.91; }
static double finger_ratio(bool black) { return black ? 1.05 : 1.74; }

typedef struct {
    tkey_t key;
    bool black;
    double rest, span; // the sensor's true rest reading and swing to the rigid bottom
    int sign;
    double noise;      // +- codes, uniform
    unsigned seed;
    double p;          // true magnet travel
    uint32_t t;
    key_event_t ev[256];
    int n;
} sim_t;

static double uniform(unsigned *s) {
    *s = *s * 1103515245u + 12345u;
    return ((*s >> 8) & 0xFFFF) / 65535.0;
}

static int reading(sim_t *m) {
    bool b = m->black;
    double z = gap_rest(b) - m->p * travel_mm(b);
    double n = (field(z) - field(gap_rest(b))) / (field(gap_bottom(b)) - field(gap_rest(b)));
    double adc = m->rest + m->sign * m->span * n + (2.0 * uniform(&m->seed) - 1.0) * m->noise;
    int v = (int)lround(adc);
    return v < 0 ? 0 : v > 4095 ? 4095 : v;
}

static void feed(sim_t *m) {
    key_event_t e;
    if (key_step(&m->key, reading(m), m->t, &e) && m->n < 256) m->ev[m->n++] = e;
    m->t += DT_US;
}

static void sim_init(sim_t *m, uint8_t note, double span_factor, int sign, double noise) {
    *m = (sim_t){0};
    m->black = note_is_black(note);
    m->rest = m->black ? 2138 : 2207;
    m->span = span_factor * (m->black ? 824 : 655);
    m->sign = sign;
    m->noise = noise;
    m->seed = 12345u + note;
    m->t = T0;
    key_init(&m->key, note);
    long sum = 0;
    for (int i = 0; i < 64; i++) sum += reading(m);
    key_calibrate(&m->key, (int)lround(sum / 64.0), false);
}

// Moves the magnet to travel `target` at `v_mag` m/s (= mm/ms).
static void move(sim_t *m, double target, double v_mag) {
    double step = v_mag * DT_US / 1000.0 / travel_mm(m->black);
    while (fabs(target - m->p) > 1e-12) {
        if (target > m->p) m->p = fmin(target, m->p + step);
        else m->p = fmax(target, m->p - step);
        feed(m);
    }
}

static void hold(sim_t *m, double ms) {
    for (int i = 0; i < (int)(ms * 1000 / DT_US); i++) feed(m);
}

// A full stroke at key-front speed v_front, then a release at 0.3 m/s magnet speed.
static void stroke(sim_t *m, double v_front) {
    move(m, 1.0, v_front / front_ratio(m->black));
    hold(m, 30);
    move(m, 0.0, 0.3);
    hold(m, 40);
}

static int count(const sim_t *m, key_ev_type_t type) {
    int c = 0;
    for (int i = 0; i < m->n; i++) c += m->ev[i].type == type;
    return c;
}

static const key_event_t *last(const sim_t *m, key_ev_type_t type) {
    for (int i = m->n - 1; i >= 0; i--)
        if (m->ev[i].type == type) return &m->ev[i];
    return NULL;
}

static void test_design_table(void) {
    // hardware/pcb/README.md: re-arm (magnet back 50 %) white ADC ~2373, black ~2282;
    // 1 N settled bottom (gap 5.52 / 5.47 mm) white ~2890, black ~2907.
    double w50 = 2207 + 655 * key_norm_depth(false, 0.5);
    double b50 = 2138 + 824 * key_norm_depth(true, 0.5);
    double w1n = 2207 + 655 * key_norm_depth(false, (10.82f - 5.52f) / 5.22f);
    double b1n = 2138 + 824 * key_norm_depth(true, (13.35f - 5.47f) / 8.03f);
    CHECK(fabs(w50 - 2373) <= 2, "white re-arm %.1f, design 2373", w50);
    CHECK(fabs(b50 - 2282) <= 2, "black re-arm %.1f, design 2282", b50);
    CHECK(fabs(w1n - 2890) <= 3, "white 1 N bottom %.1f, design 2890", w1n);
    CHECK(fabs(b1n - 2907) <= 3, "black 1 N bottom %.1f, design 2907", b1n);
}

static void test_velocity_curve(void) {
    CHECK(key_velocity(0.05f, 1) == 1, "below the range");
    CHECK(key_velocity(0.10f, 1) == 1, "0.10 m/s");
    CHECK(key_velocity(0.50f, 1) == 64, "0.5 m/s -> %u", key_velocity(0.50f, 1));
    CHECK(key_velocity(2.50f, 1) == 127, "2.5 m/s");
    CHECK(key_velocity(9.0f, 1) == 127, "above the range");
    CHECK(key_velocity(0.0f, KEY_RELEASE_VEL_MIN) == KEY_RELEASE_VEL_MIN, "release floor");
    for (float v = 0.1f; v < 2.5f; v *= 1.05f)
        CHECK(key_velocity(v * 1.05f, 1) >= key_velocity(v, 1), "monotonic at %.3f", v);
}

static void test_speed_accuracy(void) {
    static const double speeds[] = {0.15, 0.3, 0.6, 1.0, 1.5, 2.5};
    for (int black = 0; black < 2; black++) {
        sim_t m;
        sim_init(&m, black ? 61 : 60, 1.0, 1, 3.0);
        stroke(&m, 0.5);  // first press teaches the bottom
        int prev_vel = 0;
        for (unsigned i = 0; i < sizeof speeds / sizeof speeds[0]; i++) {
            int ons = count(&m, KEY_EV_NOTE_ON), offs = count(&m, KEY_EV_NOTE_OFF);
            stroke(&m, speeds[i]);
            CHECK(count(&m, KEY_EV_NOTE_ON) == ons + 1, "%s %.2f m/s: one note-on", black ? "black" : "white", speeds[i]);
            CHECK(count(&m, KEY_EV_NOTE_OFF) == offs + 1, "%s %.2f m/s: one note-off", black ? "black" : "white", speeds[i]);
            const key_event_t *on = last(&m, KEY_EV_NOTE_ON), *off = last(&m, KEY_EV_NOTE_OFF);
            if (!on || !off) continue;
            double err = on->v_front / speeds[i] - 1.0;
            CHECK(fabs(err) < 0.05, "%s %.2f m/s measured %.3f (%.1f %%)", black ? "black" : "white", speeds[i],
                  on->v_front, 100 * err);
            CHECK(on->velocity > prev_vel, "velocity rises with speed (%u after %d)", on->velocity, prev_vel);
            prev_vel = on->velocity;
            // Release at 0.3 m/s magnet speed.
            double rel = 0.3 * front_ratio(black);
            CHECK(fabs(off->v_front / rel - 1.0) < 0.08, "release speed %.3f, true %.3f", off->v_front, rel);
            CHECK(off->velocity >= KEY_RELEASE_VEL_MIN, "release velocity floor");
        }
    }
}

// A fortissimo stroke crosses the timer window in about 10 scans, so the crossing times must be
// interpolated between scans: the error must stay small whatever the scan phase.
static void test_fast_strike_phase(void) {
    for (int black = 0; black < 2; black++) {
        sim_t m;
        sim_init(&m, black ? 63 : 64, 1.0, 1, 1.0);
        stroke(&m, 0.5);
        double v_front = 2.5, worst = 0;
        double step = v_front / front_ratio(black) * DT_US / 1000.0 / travel_mm(black);
        for (int phase = 0; phase < 10; phase++) {
            m.p = -step * phase / 10.0;  // shifts where the scans fall along the stroke
            stroke(&m, v_front);
            const key_event_t *on = last(&m, KEY_EV_NOTE_ON);
            if (on) worst = fmax(worst, fabs(on->v_front / v_front - 1.0));
        }
        CHECK(count(&m, KEY_EV_NOTE_ON) == 11, "%s: all fast strikes sound", black ? "black" : "white");
        CHECK(worst < 0.03, "%s 2.5 m/s over 10 scan phases: worst error %.1f %%", black ? "black" : "white",
              100 * worst);
    }
}

static void test_first_press_spans(void) {
    static const double factors[] = {0.55, 0.7, 1.0, 1.3, 1.6};
    for (int black = 0; black < 2; black++) {
        for (unsigned i = 0; i < sizeof factors / sizeof factors[0]; i++) {
            sim_t m;
            sim_init(&m, black ? 66 : 65, factors[i], 1, 3.0);
            stroke(&m, 0.8);
            CHECK(count(&m, KEY_EV_NOTE_ON) == 1, "%s swing x%.2f: first press sounds", black ? "black" : "white",
                  factors[i]);
            stroke(&m, 0.8);
            const key_event_t *on = last(&m, KEY_EV_NOTE_ON);
            CHECK(count(&m, KEY_EV_NOTE_ON) == 2 && on && fabs(on->v_front / 0.8 - 1.0) < 0.05,
                  "%s swing x%.2f: second press %.3f m/s, true 0.8", black ? "black" : "white", factors[i],
                  on ? on->v_front : 0.0);
        }
    }
}

static void test_idle_noise_and_drift(void) {
    sim_t m;
    sim_init(&m, 64, 1.0, 1, 5.0);
    hold(&m, 10000);
    CHECK(m.n == 0, "10 s at rest with +-5 codes noise: %d events", m.n);
    // Rest drifts +24 codes over 60 s (temperature); no notes, and the key still plays right after.
    for (int i = 0; i < 24; i++) {
        m.rest += 1.0;
        hold(&m, 2500);
    }
    CHECK(m.n == 0, "drift: %d events", m.n);
    int rest = (int)((m.key.rest_q16 + 0x8000) >> 16);
    CHECK(abs(rest - (int)lround(m.rest + 655 * key_norm_depth(false, 0))) <= 4, "rest followed to %d", rest);
    stroke(&m, 0.8);
    stroke(&m, 0.8);
    const key_event_t *on = last(&m, KEY_EV_NOTE_ON);
    CHECK(count(&m, KEY_EV_NOTE_ON) == 2 && on && fabs(on->v_front / 0.8 - 1.0) < 0.05, "plays after drift");
}

// Strike, bounce back past the re-arm line, then come down again at finger speed v_repress.
static void ghost_case(double v_strike, double wait_ms, double v_repress_finger, bool expect_note,
                       const char *what) {
    sim_t m;
    sim_init(&m, 62, 1.0, 1, 2.0);
    stroke(&m, 0.6);  // teach the bottom
    int ons = count(&m, KEY_EV_NOTE_ON);
    move(&m, 1.0, v_strike / front_ratio(false));
    hold(&m, 8);
    move(&m, 0.3, 0.3);  // bounce: past the 50 % line within a few ms
    hold(&m, wait_ms);
    move(&m, 1.0, v_repress_finger / finger_ratio(false));
    hold(&m, 30);
    move(&m, 0.0, 0.3);
    int notes = count(&m, KEY_EV_NOTE_ON) - ons;
    CHECK(notes == (expect_note ? 2 : 1), "%s: %d note-ons after the strike", what, notes);
    CHECK(count(&m, KEY_EV_GHOST) == (expect_note ? 0 : 1), "%s: ghost events %d", what, count(&m, KEY_EV_GHOST));
    if (!expect_note && last(&m, KEY_EV_GHOST))
        CHECK(last(&m, KEY_EV_GHOST)->since_on_us < GHOST_WINDOW_US, "%s: ghost time inside the window", what);
}

static void test_ghost_filter(void) {
    ghost_case(1.0, 0, 0.10, false, "1.0 m/s strike, slow re-press");
    ghost_case(1.0, 0, 0.40, true, "1.0 m/s strike, re-press above 25 %");
    ghost_case(2.0, 0, 0.40, false, "2.0 m/s strike, re-press under the 0.45 cap");
    ghost_case(1.0, 600, 0.10, true, "slow re-press after the 500 ms window");
    ghost_case(0.2, 0, 0.03, true, "strike under 0.3 m/s never arms the filter");
    // Held down 400 ms: re-armed after 250 ms, so the next slow press is a real note.
    sim_t m;
    sim_init(&m, 62, 1.0, 1, 2.0);
    stroke(&m, 0.6);
    move(&m, 1.0, 1.0 / front_ratio(false));
    hold(&m, 400);
    move(&m, 0.3, 0.3);
    move(&m, 1.0, 0.10 / finger_ratio(false));
    CHECK(count(&m, KEY_EV_NOTE_ON) == 3 && count(&m, KEY_EV_GHOST) == 0, "late re-arm: slow re-press sounds");
}

static void test_polarity(void) {
    sim_t m;
    sim_init(&m, 67, 1.0, -1, 3.0);
    stroke(&m, 0.8);
    CHECK(count(&m, KEY_EV_POLARITY) == 1, "flip reported once");
    CHECK(count(&m, KEY_EV_NOTE_ON) == 0, "no note on the flipping press");
    stroke(&m, 0.8);
    stroke(&m, 0.8);
    const key_event_t *on = last(&m, KEY_EV_NOTE_ON);
    CHECK(count(&m, KEY_EV_NOTE_ON) == 2 && on && fabs(on->v_front / 0.8 - 1.0) < 0.05,
          "reversed magnet plays after the flip (%d notes)", count(&m, KEY_EV_NOTE_ON));
    CHECK(count(&m, KEY_EV_POLARITY) == 1, "no second flip");
}

static void test_e11_and_order(void) {
    static const int dnl[] = {1536, 2560, 3584};
    int bad = 0, order = 0;
    for (int black = 0; black < 2; black++)
        for (int sign = -1; sign <= 1; sign += 2)
            for (int rest = KEY_REST_MIN; rest <= KEY_REST_MAX; rest++) {
                tkey_t k;
                key_init(&k, black ? 61 : 60);
                key_calibrate(&k, rest, false);
                if (sign < 0) {
                    // Readings far below rest flip the key, which recomputes its lines.
                    key_event_t e;
                    int low = rest - (black ? 824 : 655);
                    for (int i = 0; i < 4; i++) key_step(&k, low, (uint32_t)i * DT_US, &e);
                    if (k.sign != -1) order++;
                }
                int d[4] = {k.d_rearm, k.d_lo, k.d_rel_hi, k.d_on};
                for (int i = 0; i < 4; i++)
                    for (int j = 0; j < 3; j++)
                        bad += abs(rest + k.sign * d[i] - dnl[j]) <= KEY_E11_GUARD;
                order += !(d[0] < d[1] && d[1] < d[2] && d[2] < d[3] && k.win_on_mm > 0 && k.win_rel_mm > 0);
            }
    CHECK(bad == 0, "%d thresholds within %d codes of an E11 code", bad, KEY_E11_GUARD);
    CHECK(order == 0, "%d calibrations with lines out of order", order);
}

static void test_silent_and_disabled(void) {
    sim_t m;
    sim_init(&m, 69, 1.0, 1, 2.0);
    stroke(&m, 0.6);
    int ons = count(&m, KEY_EV_NOTE_ON);
    move(&m, 1.0, 0.005);
    CHECK(count(&m, KEY_EV_SILENT) == 1 && count(&m, KEY_EV_NOTE_ON) == ons, "0.005 m/s magnet: no note");
    tkey_t k;
    key_init(&k, 21);
    CHECK(!key_calibrate(&k, 40, true) && k.fault == KEY_ABSENT, "unplugged end part");
    key_event_t e;
    CHECK(!key_step(&k, 3000, 0, &e), "absent key stays quiet");
    key_init(&k, 60);
    CHECK(!key_calibrate(&k, 1200, false) && k.fault == KEY_FAULT, "rest out of band");
}

int main(void) {
    test_design_table();
    test_velocity_curve();
    test_speed_accuracy();
    test_fast_strike_phase();
    test_first_press_spans();
    test_idle_noise_and_drift();
    test_ghost_filter();
    test_polarity();
    test_e11_and_order();
    test_silent_and_disabled();
    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
