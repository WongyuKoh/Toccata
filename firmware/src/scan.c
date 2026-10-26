#include "scan.h"

#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"

// Pins from hardware/pcb/netlist/pins_rp2040.csv: GP2..GP5 = MUX S0..S3, GP26 = MUX SIG (ADC0).
#define PIN_MUX_S0     2
#define PIN_MUX_SIG    26
#define MUX_MASK       (0xFu << PIN_MUX_S0)
#define MUX_SETTLE_US  4   // after changing S0..S3 (SCH-03 note 7)
#define SAMPLES        2   // conversions averaged per reading
#define CAL_PASSES     64

tkey_t scan_keys[SCAN_MAX_KEYS];
volatile uint32_t scan_count;
queue_t scan_events;

static scan_plan_t plan;
static volatile bool recal_wanted;

static int read_channel(uint channel) {
    gpio_put_masked(MUX_MASK, channel << PIN_MUX_S0);
    busy_wait_us_32(MUX_SETTLE_US);
    int sum = 0;
    for (int i = 0; i < SAMPLES; i++) sum += adc_read();
    return (sum + SAMPLES / 2) / SAMPLES;
}

static void calibrate(void) {
    int32_t sum[SCAN_MAX_KEYS] = {0};
    for (int pass = 0; pass < CAL_PASSES; pass++)
        for (uint i = 0; i < plan.count; i++) sum[i] += read_channel(plan.channel[i]);
    for (uint i = 0; i < plan.count; i++)
        key_calibrate(&scan_keys[i], (sum[i] + CAL_PASSES / 2) / CAL_PASSES, plan.ext[i]);
}

static void core1_main(void) {
    gpio_init_mask(MUX_MASK);
    gpio_set_dir_out_masked(MUX_MASK);
    adc_init();
    adc_gpio_init(PIN_MUX_SIG);
    adc_select_input(0);
    sleep_ms(2);  // DRV5055 power-on time: allow at least 1 ms (research/hall.md 1.3)
    calibrate();
    for (;;) {
        if (recal_wanted) {
            calibrate();
            recal_wanted = false;
        }
        for (uint i = 0; i < plan.count; i++) {
            int adc = read_channel(plan.channel[i]);
            key_event_t ev;
            if (key_step(&scan_keys[i], adc, time_us_32(), &ev)) queue_try_add(&scan_events, &ev);
        }
        scan_count++;
    }
}

void scan_start(const scan_plan_t *p) {
    plan = *p;
    for (uint i = 0; i < plan.count; i++) key_init(&scan_keys[i], plan.note[i]);
    queue_init(&scan_events, sizeof(key_event_t), 64);
    multicore_launch_core1(core1_main);
}

void scan_recalibrate(void) { recal_wanted = true; }
