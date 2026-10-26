#include "keys.h"

#include <math.h>
#include <stdlib.h>

// On-axis field of the Ø5 x 2 disc magnet at gap z (mm), in units of Br/2. Only ratios are used,
// so the grade (N35) drops out. hardware/pcb/README.md uses the same model for its ADC table.
static float field(float z) {
    const float r = 2.5f, len = 2.0f;
    float zl = z + len;
    return zl / sqrtf(r * r + zl * zl) - z / sqrtf(r * r + z * z);
}

static float gap_rest(bool black) { return black ? KEY_BLACK_GAP_REST : KEY_WHITE_GAP_REST; }
static float gap_bottom(bool black) { return black ? KEY_BLACK_GAP_BOTTOM : KEY_WHITE_GAP_BOTTOM; }
static float travel_mm(bool black) { return gap_rest(black) - gap_bottom(black); }
static int span_design(bool black) { return black ? KEY_BLACK_SPAN_DESIGN : KEY_WHITE_SPAN_DESIGN; }
static float front_ratio(bool black) { return black ? KEY_BLACK_FRONT_RATIO : KEY_WHITE_FRONT_RATIO; }
static float finger_ratio(bool black) { return black ? KEY_BLACK_FINGER_RATIO : KEY_WHITE_FINGER_RATIO; }

// Field at rest and rest-to-bottom field change, per key colour; cached because the board has
// no FPU and threshold updates run inside the scan loop.
static float field_rest[2], field_swing[2];
static bool field_ready;

float key_norm_depth(bool black, float p) {
    if (!field_ready) {
        for (int b = 0; b < 2; b++) {
            field_rest[b] = field(gap_rest(b));
            field_swing[b] = field(gap_bottom(b)) - field_rest[b];
        }
        field_ready = true;
    }
    float z = gap_rest(black) - p * travel_mm(black);
    return (field(z) - field_rest[black]) / field_swing[black];
}

// Inverse of key_norm_depth by bisection (it rises with p); 16 halvings resolve 0.1 µm.
static float travel_from_norm(bool black, float n) {
    float lo = -0.2f, hi = 1.5f;
    if (n <= key_norm_depth(black, lo)) return lo;
    if (n >= key_norm_depth(black, hi)) return hi;
    for (int i = 0; i < 16; i++) {
        float mid = 0.5f * (lo + hi);
        if (key_norm_depth(black, mid) < n) lo = mid; else hi = mid;
    }
    return 0.5f * (lo + hi);
}

bool note_is_black(uint8_t note) {
    switch (note % 12) {
    case 1: case 3: case 6: case 8: case 10: return true;
    default: return false;
    }
}

static int rest_of(const tkey_t *k) { return (int)((k->rest_q16 + 0x8000) >> 16); }

// Moves a threshold off the codes where the RP2040 ADC has its DNL spikes (erratum E11),
// towards the bottom when deeper is true, else towards rest, so the line order is kept.
static int16_t e11_clear(const tkey_t *k, int16_t d, bool deeper) {
    static const int dnl[] = {512, 1536, 2560, 3584};
    int rest = rest_of(k);
    int adc = rest + k->sign * d;
    for (unsigned i = 0; i < sizeof dnl / sizeof dnl[0]; i++) {
        if (abs(adc - dnl[i]) > KEY_E11_GUARD) continue;
        int up = dnl[i] + KEY_E11_GUARD + 1, down = dnl[i] - KEY_E11_GUARD - 1;
        // Going deeper means the reading moves in the sign direction.
        adc = ((k->sign > 0) == deeper) ? up : down;
    }
    return (int16_t)(k->sign * (adc - rest));
}

static void compute_thresholds(tkey_t *k) {
    float span = (float)k->span;
    k->d_rearm = e11_clear(k, (int16_t)lroundf(span * key_norm_depth(k->black, KEY_P_REARM)), false);
    k->d_lo = e11_clear(k, (int16_t)lroundf(span * key_norm_depth(k->black, KEY_P_VEL_LO)), true);
    k->d_rel_hi = e11_clear(k, (int16_t)lroundf(span * key_norm_depth(k->black, KEY_P_REL_HI)), false);
    k->d_on = e11_clear(k, (int16_t)lroundf(span * key_norm_depth(k->black, KEY_P_ON)), true);
    float mm = travel_mm(k->black);
    float p_rearm = travel_from_norm(k->black, k->d_rearm / span);
    float p_lo = travel_from_norm(k->black, k->d_lo / span);
    float p_rel_hi = travel_from_norm(k->black, k->d_rel_hi / span);
    float p_on = travel_from_norm(k->black, k->d_on / span);
    k->win_on_mm = (p_on - p_lo) * mm;
    k->win_rel_mm = (p_rel_hi - p_rearm) * mm;
    k->rest_at_calc = (int16_t)rest_of(k);
}

void key_init(tkey_t *k, uint8_t note) {
    *k = (tkey_t){0};
    k->note = note;
    k->black = note_is_black(note);
    k->sign = 1;
    k->state = KEY_OFF;
    key_norm_depth(false, 0.0f);  // fill the field cache on core 0, before the scan core starts
}

bool key_calibrate(tkey_t *k, int adc, bool ext) {
    uint8_t note = k->note;
    key_init(k, note);
    k->last_adc = (int16_t)adc;
    if (ext && adc < KEY_EXT_ABSENT) {
        k->fault = KEY_ABSENT;
        return false;
    }
    if (adc < KEY_REST_MIN || adc > KEY_REST_MAX) {
        k->fault = KEY_FAULT;
        return false;
    }
    k->rest_q16 = (int32_t)adc << 16;
    k->span = (int16_t)lroundf(span_design(k->black) * KEY_BOTTOM_INIT);
    compute_thresholds(k);
    k->state = KEY_UP;
    return true;
}

float key_travel(const tkey_t *k, int adc) {
    if (k->state == KEY_OFF || k->span <= 0) return 0.0f;
    float n = (float)(k->sign * (adc - rest_of(k))) / (float)k->span;
    return travel_from_norm(k->black, n);
}

uint8_t key_velocity(float v_front, uint8_t lowest) {
    if (v_front <= KEY_VEL_V_MIN) return lowest;
    float x = logf(v_front / KEY_VEL_V_MIN) / logf(KEY_VEL_V_MAX / KEY_VEL_V_MIN);
    long v = 1 + lroundf(126.0f * x);
    if (v < lowest) v = lowest;
    if (v > 127) v = 127;
    return (uint8_t)v;
}

// Time at which the depth passed thr between two readings (linear between them).
static uint32_t crossing(uint32_t t0, int d0, uint32_t t1, int d1, int thr) {
    if (d1 == d0) return t1;
    int64_t num = (int64_t)(thr - d0) * (int64_t)(uint32_t)(t1 - t0);
    return t0 + (uint32_t)(num / (d1 - d0));
}

static float speed(float mm, uint32_t dt_us) {
    return dt_us ? mm * 1000.0f / (float)dt_us : 1000.0f; // mm/ms = m/s
}

static bool strike(tkey_t *k, uint32_t t_on, key_event_t *ev) {
    if (!k->lo_ok) return false; // started below the timer line unseen (boot); stay quiet
    float v_mag = speed(k->win_on_mm, t_on - k->t_lo);
    *ev = (key_event_t){.note = k->note, .t_us = t_on,
                        .v_front = v_mag * front_ratio(k->black),
                        .v_finger = v_mag * finger_ratio(k->black)};
    if (v_mag < KEY_SILENT_V_MAG) {
        ev->type = KEY_EV_SILENT;
        return true;
    }
    if (k->ghost_suspect) {
        k->ghost_suspect = false;
        uint32_t since = t_on - k->t_note_on;
        float limit = fminf(GHOST_CAP_V_FINGER, GHOST_RATIO * k->v_front_prev);
        if (since <= GHOST_WINDOW_US && ev->v_finger < limit) {
            ev->type = KEY_EV_GHOST;
            ev->since_on_us = since;
            return true;
        }
    }
    ev->type = KEY_EV_NOTE_ON;
    ev->velocity = key_velocity(ev->v_front, 1);
    k->sounding = true;
    k->t_note_on = t_on;
    k->v_front_prev = ev->v_front;
    k->ghost_watch = ev->v_front >= GHOST_ARM_V_FRONT;
    return true;
}

static bool release(tkey_t *k, uint32_t t_off, key_event_t *ev) {
    if (k->ghost_watch) {
        k->ghost_suspect = (uint32_t)(t_off - k->t_note_on) <= GHOST_REARM_US;
        k->ghost_watch = false;
    }
    if (!k->sounding) return false;
    k->sounding = false;
    float v_front = k->rel_ok ? speed(k->win_rel_mm, t_off - k->t_rel) * front_ratio(k->black) : 0.0f;
    *ev = (key_event_t){.type = KEY_EV_NOTE_OFF, .note = k->note, .t_us = t_off, .v_front = v_front,
                        .velocity = k->rel_ok ? key_velocity(v_front, KEY_RELEASE_VEL_MIN) : 64};
    return true;
}

bool key_step(tkey_t *k, int adc, uint32_t t, key_event_t *ev) {
    k->last_adc = (int16_t)adc;
    if (k->state == KEY_OFF) return false;
    int d = k->sign * (adc - rest_of(k));
    if (!k->have_prev) {
        k->have_prev = true;
        k->d_prev = (int16_t)d;
        k->t_prev = t;
        return false;
    }
    int dp = k->d_prev;
    uint32_t tp = k->t_prev;
    bool out = false;

    if (k->state == KEY_UP) {
        if (d < -span_design(k->black) / 2) {
            // Three readings far on the wrong side: the magnet sits N pole down.
            if (++k->neg_count >= 3) {
                k->sign = (int8_t)-k->sign;
                k->neg_count = 0;
                k->lo_ok = false;
                k->have_prev = false;
                compute_thresholds(k);
                *ev = (key_event_t){.type = KEY_EV_POLARITY, .note = k->note, .t_us = t};
                return true;
            }
        } else {
            k->neg_count = 0;
        }
        if (dp < k->d_lo && d >= k->d_lo) {
            k->t_lo = crossing(tp, dp, t, d, k->d_lo);
            k->lo_ok = true;
        } else if (d < k->d_lo - KEY_HYST) {
            k->lo_ok = false;
        }
        if (dp < k->d_on && d >= k->d_on) {
            out = strike(k, crossing(tp, dp, t, d, k->d_on), ev);
            k->state = KEY_DOWN;
            k->lo_ok = false;
            k->rel_ok = false;
            k->peak = (int16_t)d;
        } else if (!k->lo_ok && abs(d) <= KEY_REST_BAND) {
            k->rest_q16 += (((int32_t)adc << 16) - k->rest_q16) >> KEY_REST_SHIFT;
            if (abs(rest_of(k) - k->rest_at_calc) >= 3) compute_thresholds(k);
        }
    } else {
        int held = d < dp ? d : dp; // two readings in a row, so one noisy sample cannot set it
        if (held > k->peak) k->peak = (int16_t)held;
        if (dp > k->d_rel_hi && d <= k->d_rel_hi) {
            k->t_rel = crossing(tp, dp, t, d, k->d_rel_hi);
            k->rel_ok = true;
        } else if (d > k->d_rel_hi + KEY_HYST) {
            k->rel_ok = false;
        }
        if (d < k->d_rearm) {
            out = release(k, crossing(tp, dp, t, d, k->d_rearm), ev);
            k->state = KEY_UP;
            k->lo_ok = false;
            // Learn the bottom: the swing only grows, and a reading far beyond the design is ignored.
            if (k->peak > k->span && k->peak < 2 * span_design(k->black)) {
                k->span = k->peak;
                compute_thresholds(k);
            }
        }
    }
    k->d_prev = (int16_t)(k->sign * (adc - rest_of(k)));
    k->t_prev = t;
    return out;
}
