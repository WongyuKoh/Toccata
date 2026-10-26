// Toccata key logic: one Hall reading per scan -> magnet position -> note events.
// Plain C with no pico-sdk calls, so firmware/test/test_keys.c runs it on a computer.
#pragma once

#include <stdbool.h>
#include <stdint.h>

// Magnet-to-element gap in mm, at rest and on the rigid bottom (W1 r4.5, hardware/pcb/README.md, SCH-02).
#define KEY_WHITE_GAP_REST    10.82f
#define KEY_WHITE_GAP_BOTTOM   5.60f
#define KEY_BLACK_GAP_REST    13.35f
#define KEY_BLACK_GAP_BOTTOM   5.32f

// Design ADC swing from rest to bottom (DRV5055A2 at 3.3 V): white 2207 -> 2862, black 2138 -> 2962.
#define KEY_WHITE_SPAN_DESIGN 655
#define KEY_BLACK_SPAN_DESIGN 824

// W1 lever ratios (SCH-03 note 9): key front = magnet x 1.91 / 1.18, finger point = magnet x 1.74 / 1.05.
#define KEY_WHITE_FRONT_RATIO  1.91f
#define KEY_BLACK_FRONT_RATIO  1.18f
#define KEY_WHITE_FINGER_RATIO 1.74f
#define KEY_BLACK_FINGER_RATIO 1.05f

// Lines on the magnet travel p (0 = rest, 1 = bottom).
#define KEY_P_REARM   0.50f  // note-off and re-arm: magnet back 50 % (SCH-03 note 9)
#define KEY_P_VEL_LO  0.55f  // strike timer starts
#define KEY_P_ON      0.85f  // note-on; strike timer stops
#define KEY_P_REL_HI  0.80f  // release timer starts (it stops at KEY_P_REARM)

// Until a key has been pressed once, its bottom is guessed at this share of the design swing.
// Low on purpose: a weak sensor or a slightly far magnet still reaches KEY_P_ON, and the first
// press then teaches the real bottom (D4: per-key calibration lives in the firmware).
#define KEY_BOTTOM_INIT  0.75f
#define KEY_HYST         6     // ADC codes
#define KEY_REST_BAND    8     // rest follows slow drift only while the key reads within this
#define KEY_REST_SHIFT   16    // drift filter, about 7 s at 9 k scans/s
#define KEY_E11_GUARD    10    // thresholds stay > 10 codes off the RP2040-E11 DNL codes (SCH-03 note 7)
#define KEY_REST_MIN     1800  // a rest reading outside this band marks the sensor faulty
#define KEY_REST_MAX     2600
#define KEY_EXT_ABSENT   186   // 0.15 V: end part unplugged, EXT pulled to 0 V (SCH-04 note 5)

// Velocity: key-front speed on a log scale. The taste curve belongs to the synth (D4).
#define KEY_VEL_V_MIN        0.10f  // m/s -> velocity 1
#define KEY_VEL_V_MAX        2.50f  // m/s -> velocity 127
#define KEY_RELEASE_VEL_MIN  5      // D2: some engines keep the damper up at release velocity 1
#define KEY_SILENT_V_MAG     0.01f  // magnet slower than this: no note (SCH-03 note 9, optional)

// Ghost filter U6 (W1 r4.5 DESIGN 0.1 = SCH-03 note 9).
#define GHOST_ARM_V_FRONT   0.30f    // only notes at least this fast can leave a ghost
#define GHOST_REARM_US      250000   // re-armed this soon after note-on -> suspect
#define GHOST_WINDOW_US     500000   // the first re-press this soon after note-on is judged
#define GHOST_CAP_V_FINGER  0.45f    // dropped if finger speed < min(cap, ratio x previous front speed)
#define GHOST_RATIO         0.25f

typedef enum { KEY_OFF, KEY_UP, KEY_DOWN } key_state_t;
typedef enum { KEY_OK, KEY_ABSENT, KEY_FAULT } key_fault_t;

typedef enum {
    KEY_EV_NOTE_ON,
    KEY_EV_NOTE_OFF,
    KEY_EV_GHOST,     // re-press dropped by the ghost filter
    KEY_EV_SILENT,    // pressed too slowly to sound
    KEY_EV_POLARITY,  // reading fell instead of rising; the key now counts the other way
} key_ev_type_t;

typedef struct {
    key_ev_type_t type;
    uint8_t note;
    uint8_t velocity;
    float v_front;       // key-front speed in m/s (strike or release)
    float v_finger;      // finger-point speed in m/s (strikes only)
    uint32_t t_us;
    uint32_t since_on_us; // KEY_EV_GHOST: time since the note-on it follows
} key_event_t;

typedef struct {
    uint8_t note;
    bool black;
    key_state_t state;
    key_fault_t fault;
    int8_t sign;          // +1: the reading rises as the key goes down (S pole down)
    int32_t rest_q16;     // rest reading x 65536
    int16_t rest_at_calc; // rest when the thresholds were last computed
    int16_t span;         // depth at the bottom, learned from presses
    // Thresholds as depth = sign x (reading - rest), already moved off the E11 codes.
    int16_t d_rearm, d_lo, d_on, d_rel_hi;
    float win_on_mm, win_rel_mm; // magnet travel between the timer lines
    // Running state
    bool have_prev;
    int16_t d_prev;
    uint32_t t_prev;
    bool lo_ok, rel_ok;
    uint32_t t_lo, t_rel;
    int16_t peak;
    uint8_t neg_count;
    bool sounding;
    bool ghost_watch, ghost_suspect;
    uint32_t t_note_on;
    float v_front_prev;
    int16_t last_adc;
} tkey_t;

bool note_is_black(uint8_t note);
void key_init(tkey_t *k, uint8_t note);
// Sets rest from an averaged reading taken with the key up. Returns false if the key is disabled.
bool key_calibrate(tkey_t *k, int adc, bool ext);
// Feeds one reading. Returns true and fills *ev when something happened.
bool key_step(tkey_t *k, int adc, uint32_t t_us, key_event_t *ev);
float key_travel(const tkey_t *k, int adc);  // p for a reading (for display)
uint8_t key_velocity(float v_front, uint8_t lowest);
// Share of the rest-to-bottom swing reached at travel p (exposed for tests).
float key_norm_depth(bool black, float p);
