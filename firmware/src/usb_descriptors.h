#pragma once

// Product name, e.g. "Toccata O4" (D3: every module has its own USB name), and serial number.
// Call before tusb_init(); the strings are copied.
void usb_set_names(const char *product, const char *serial);
