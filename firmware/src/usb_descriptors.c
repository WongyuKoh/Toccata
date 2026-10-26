#include "usb_descriptors.h"

#include <string.h>

#include "tusb.h"

// pid.codes test VID/PID. Hosts tell the boards apart by product name and serial number.
#ifndef TOCCATA_USB_VID
#define TOCCATA_USB_VID 0x1209
#endif
#ifndef TOCCATA_USB_PID
#define TOCCATA_USB_PID 0x0001
#endif

static char product_name[32] = "Toccata";
static char serial_number[48] = "0";
static char console_name[48] = "Toccata console";

void usb_set_names(const char *product, const char *serial) {
    strncpy(product_name, product, sizeof product_name - 1);
    strncpy(serial_number, serial, sizeof serial_number - 1);
    strncpy(console_name, product, sizeof console_name - 9);
    strcat(console_name, " console");
}

static tusb_desc_device_t const desc_device = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    // CDC uses an interface association, so the device is "miscellaneous / IAD".
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = TOCCATA_USB_VID,
    .idProduct = TOCCATA_USB_PID,
    .bcdDevice = 0x0100,
    .iManufacturer = 1,
    .iProduct = 2,
    .iSerialNumber = 3,
    .bNumConfigurations = 1,
};

uint8_t const *tud_descriptor_device_cb(void) { return (uint8_t const *)&desc_device; }

enum { ITF_NUM_CDC = 0, ITF_NUM_CDC_DATA, ITF_NUM_MIDI, ITF_NUM_MIDI_STREAMING, ITF_NUM_TOTAL };

#define EPNUM_CDC_NOTIF  0x81
#define EPNUM_CDC_OUT    0x02
#define EPNUM_CDC_IN     0x82
#define EPNUM_MIDI_OUT   0x03
#define EPNUM_MIDI_IN    0x83

#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN + TUD_MIDI_DESC_LEN)

static uint8_t const desc_configuration[] = {
    // 12 sensors + MCU draw about 60-100 mA (research/mcu.md 1.6).
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 200),
    TUD_CDC_DESCRIPTOR(ITF_NUM_CDC, 4, EPNUM_CDC_NOTIF, 8, EPNUM_CDC_OUT, EPNUM_CDC_IN, 64),
    TUD_MIDI_DESCRIPTOR(ITF_NUM_MIDI, 0, EPNUM_MIDI_OUT, EPNUM_MIDI_IN, 64),
};

uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_configuration;
}

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t desc[48];
    size_t len;
    if (index == 0) {
        desc[1] = 0x0409;  // English
        len = 1;
    } else {
        const char *s;
        switch (index) {
        case 1: s = "Toccata"; break;
        case 2: s = product_name; break;
        case 3: s = serial_number; break;
        case 4: s = console_name; break;
        default: return NULL;
        }
        len = strlen(s);
        if (len > 47) len = 47;
        for (size_t i = 0; i < len; i++) desc[1 + i] = (uint8_t)s[i];
    }
    desc[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * len + 2));
    return desc;
}
