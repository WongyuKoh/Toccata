// Toccata octave board (MB, SCH-03): RP2040-Zero + CD74HC4067 mux + 12 DRV5055 Hall sensors.
// Core 1 scans the keys (scan.c, keys.c). Core 0 runs USB: MIDI to the synth and a text
// console on the CDC serial port for checking sensors on the bench.
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "keys.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "scan.h"
#include "tusb.h"
#include "usb_descriptors.h"

// ID jumpers JP301..JP303 on GP6..GP8, closed = GND: ID = JP301 + 2 x JP302 + 4 x JP303
// (hardware/pcb/netlist/id_jumpers.csv). GP14 is JP304 (open) here and JP504 (closed) on the pedal board.
#define PIN_ID0      6
#define PIN_PED_SEL  14
#define MIDI_CHANNEL 0

// Octave used when no ID jumper is closed yet, e.g. a bare board on the bench.
#ifndef TOCCATA_DEFAULT_OCTAVE
#define TOCCATA_DEFAULT_OCTAVE 4
#endif

static int octave;            // 1..7 -> O1..O7
static bool id_jumpers_open;  // no jumper closed: TOCCATA_DEFAULT_OCTAVE
static bool pedal_board;
static bool scanning;
static bool echo_events = true;
static bool watching;
static uint32_t scans_per_s;
static char product[32];

static void read_board_id(void) {
    for (uint pin = PIN_ID0; pin < PIN_ID0 + 3; pin++) {
        gpio_init(pin);
        gpio_pull_up(pin);
    }
    gpio_init(PIN_PED_SEL);
    gpio_pull_up(PIN_PED_SEL);
    busy_wait_us_32(10);  // SCH-03 note 8
    int id = 0;
    for (int bit = 0; bit < 3; bit++)
        if (!gpio_get(PIN_ID0 + bit)) id |= 1 << bit;
    pedal_board = !gpio_get(PIN_PED_SEL);
    id_jumpers_open = id == 0;
    octave = id ? id : TOCCATA_DEFAULT_OCTAVE;
}

// O4: mux C0..C11 -> MIDI 60..71. End parts: O1 C12..C14 -> A0, A#0, B0; O7 C12 -> C8 (mux_map.csv).
static void make_plan(scan_plan_t *plan) {
    int base = 12 * (octave + 1);
    plan->count = 0;
    for (int ch = 0; ch < 12; ch++) {
        plan->channel[plan->count] = (uint8_t)ch;
        plan->note[plan->count] = (uint8_t)(base + ch);
        plan->ext[plan->count++] = false;
    }
    int ext_keys = octave == 1 ? 3 : octave == 7 ? 1 : 0;
    int ext_note = octave == 1 ? 21 : 108;
    for (int i = 0; i < ext_keys; i++) {
        plan->channel[plan->count] = (uint8_t)(12 + i);
        plan->note[plan->count] = (uint8_t)(ext_note + i);
        plan->ext[plan->count++] = true;
    }
}

// ---- console (CDC) -----------------------------------------------------------------------

static void con_write(const char *s, uint32_t n) {
    if (!tud_cdc_connected()) return;
    absolute_time_t give_up = make_timeout_time_ms(50);
    while (n) {
        uint32_t done = tud_cdc_write(s, n);
        s += done;
        n -= done;
        if (n) {
            tud_cdc_write_flush();
            tud_task();
            if (time_reached(give_up)) return;  // nobody is reading: drop the rest
        }
    }
}

static void con_printf(const char *fmt, ...) {
    char buf[200];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (n > 0) con_write(buf, n < (int)sizeof buf ? (uint32_t)n : sizeof buf - 1);
}

static const char *note_name(uint8_t note, char *buf) {
    static const char *const names[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    snprintf(buf, 6, "%s%d", names[note % 12], note / 12 - 1);
    return buf;
}

static void show_help(void) {
    con_printf("\r\n%s commands: s = status, w = watch sensors on/off, e = note log on/off,\r\n"
               "  r = re-read rest values (all keys up), h = help\r\n", product);
}

static void show_status(void) {
    char nm[6];
    con_printf("\r\n%s  %s  scans/s %lu  MIDI %s\r\n", product,
               id_jumpers_open ? "(no ID jumper closed: default octave)" : "(ID jumpers)",
               (unsigned long)scans_per_s, tud_midi_mounted() ? "mounted" : "not mounted");
    if (!scanning) {
        con_printf("pedal board (JP504 closed): not handled by this firmware\r\n");
        return;
    }
    con_printf("note  now   rest  swing pol  rearm  lo   relhi   on   state\r\n");
    for (int i = 0; i < SCAN_MAX_KEYS; i++) {
        const tkey_t *k = &scan_keys[i];
        if (!k->note) break;
        const char *state = k->fault == KEY_ABSENT ? "absent" : k->fault == KEY_FAULT ? "FAULT" :
                            k->state == KEY_DOWN ? "down" : "up";
        con_printf("%-4s %5d %5d %5d   %c  %5d %5d %5d %5d   %s\r\n", note_name(k->note, nm),
                   k->last_adc, (int)((k->rest_q16 + 0x8000) >> 16), k->span, k->sign > 0 ? '+' : '-',
                   k->d_rearm, k->d_lo, k->d_rel_hi, k->d_on, state);
    }
    con_printf("FAULT = rest reading outside %d..%d (wiring, sensor, or a key held down at power-up)\r\n",
               KEY_REST_MIN, KEY_REST_MAX);
}

static void show_watch_line(void) {
    char line[200], nm[6];
    int n = 0;
    for (int i = 0; i < SCAN_MAX_KEYS && scan_keys[i].note; i++) {
        const tkey_t *k = &scan_keys[i];
        int pct = (int)(100.0f * key_travel(k, k->last_adc) + 0.5f);
        n += snprintf(line + n, sizeof line - n, "%s %d/%d%% ", note_name(k->note, nm), k->last_adc, pct);
        if (n >= (int)sizeof line - 2) break;
    }
    con_printf("%s\r\n", line);
}

static void console_poll(void) {
    while (tud_cdc_available()) {
        int c = tud_cdc_read_char();
        switch (c) {
        case 's': show_status(); break;
        case 'w': watching = !watching; break;
        case 'e':
            echo_events = !echo_events;
            con_printf("note log %s\r\n", echo_events ? "on" : "off");
            break;
        case 'r':
            if (scanning) {
                uint8_t all_off[3] = {0xB0 | MIDI_CHANNEL, 123, 0};  // the key states restart
                if (tud_midi_mounted()) tud_midi_stream_write(0, all_off, 3);
                scan_recalibrate();
                con_printf("rest values re-read\r\n");
            }
            break;
        case 'h': case '?': show_help(); break;
        default: break;
        }
    }
}

// ---- events -------------------------------------------------------------------------------

static void handle_event(const key_event_t *ev) {
    char nm[6];
    uint8_t msg[3] = {0, ev->note, ev->velocity};
    if (ev->type == KEY_EV_NOTE_ON) msg[0] = 0x90 | MIDI_CHANNEL;
    if (ev->type == KEY_EV_NOTE_OFF) msg[0] = 0x80 | MIDI_CHANNEL;  // D2: real note-off
    if (msg[0] && tud_midi_mounted()) tud_midi_stream_write(0, msg, 3);
    if (!echo_events) return;
    uint32_t ms = ev->t_us / 1000;
    switch (ev->type) {
    case KEY_EV_NOTE_ON:
        con_printf("%8lu on    %-4s vel %3u  front %.2f m/s\r\n", (unsigned long)ms,
                   note_name(ev->note, nm), ev->velocity, (double)ev->v_front);
        break;
    case KEY_EV_NOTE_OFF:
        con_printf("%8lu off   %-4s vel %3u  front %.2f m/s\r\n", (unsigned long)ms,
                   note_name(ev->note, nm), ev->velocity, (double)ev->v_front);
        break;
    case KEY_EV_GHOST:  // stage-0 test 11 records these re-press times
        con_printf("%8lu ghost %-4s dropped %lu ms after note-on, finger %.3f m/s\r\n", (unsigned long)ms,
                   note_name(ev->note, nm), (unsigned long)(ev->since_on_us / 1000), (double)ev->v_finger);
        break;
    case KEY_EV_SILENT:
        con_printf("%8lu quiet %-4s pressed too slowly to sound\r\n", (unsigned long)ms, note_name(ev->note, nm));
        break;
    case KEY_EV_POLARITY:
        con_printf("%8lu %-4s reading falls when pressed: magnet N pole down? now counted the other way\r\n",
                   (unsigned long)ms, note_name(ev->note, nm));
        break;
    }
}

int main(void) {
    read_board_id();
    char serial[48], uid[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    pico_get_unique_board_id_string(uid, sizeof uid);
    if (pedal_board) {
        snprintf(product, sizeof product, "Toccata PED");
    } else {
        snprintf(product, sizeof product, "Toccata O%d", octave);
        scan_plan_t plan;
        make_plan(&plan);
        scan_start(&plan);
        scanning = true;
    }
    snprintf(serial, sizeof serial, "%s-%s", product + 8, uid);
    usb_set_names(product, serial);
    tusb_init();

    uint32_t last_count = 0;
    absolute_time_t next_second = make_timeout_time_ms(1000), next_watch = make_timeout_time_ms(100);
    for (;;) {
        tud_task();
        uint8_t discard[16];
        while (tud_midi_available()) tud_midi_stream_read(discard, sizeof discard);
        if (scanning) {
            key_event_t ev;
            while (queue_try_remove(&scan_events, &ev)) handle_event(&ev);
        }
        console_poll();
        if (time_reached(next_second)) {
            uint32_t count = scan_count;
            scans_per_s = count - last_count;
            last_count = count;
            next_second = delayed_by_ms(next_second, 1000);
        }
        if (watching && scanning && time_reached(next_watch)) {
            show_watch_line();
            next_watch = make_timeout_time_ms(100);
        }
        tud_cdc_write_flush();
    }
}
