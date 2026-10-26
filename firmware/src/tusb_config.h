// TinyUSB settings: one USB MIDI port (to the synth) + one CDC serial port (text console).
#pragma once

#define CFG_TUSB_RHPORT0_MODE   OPT_MODE_DEVICE
#define CFG_TUD_ENDPOINT0_SIZE  64

#define CFG_TUD_CDC   1
#define CFG_TUD_MIDI  1
#define CFG_TUD_MSC   0
#define CFG_TUD_HID   0
#define CFG_TUD_VENDOR 0

#define CFG_TUD_CDC_RX_BUFSIZE   64
#define CFG_TUD_CDC_TX_BUFSIZE   2048  // a full status table fits without waiting
#define CFG_TUD_CDC_EP_BUFSIZE   64
#define CFG_TUD_MIDI_RX_BUFSIZE  64
#define CFG_TUD_MIDI_TX_BUFSIZE  256
