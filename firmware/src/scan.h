// Core 1: mux + ADC scan of one octave board, feeding keys.c.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "keys.h"
#include "pico/util/queue.h"

#define SCAN_MAX_KEYS 15  // 12 keys + 3 end-part keys on O1 (mux C12..C14)

typedef struct {
    uint8_t count;
    uint8_t channel[SCAN_MAX_KEYS];  // mux channel C0..C15
    uint8_t note[SCAN_MAX_KEYS];
    bool ext[SCAN_MAX_KEYS];         // end part on the EXT cable (may be unplugged)
} scan_plan_t;

extern tkey_t scan_keys[SCAN_MAX_KEYS];  // written by core 1, read by core 0 for the console
extern volatile uint32_t scan_count;     // full passes over all keys
extern queue_t scan_events;              // key_event_t, core 1 -> core 0

void scan_start(const scan_plan_t *plan);
void scan_recalibrate(void);  // re-read every rest value on the next pass (keys must be up)
