cmake_minimum_required(VERSION 3.13)

set(PICO_BOARD waveshare_rp2040_zero)
include(pico_sdk_import.cmake)

project(toccata_octave C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

add_executable(toccata_octave
    src/main.c
    src/scan.c
    src/keys.c
    src/usb_descriptors.c
)
target_include_directories(toccata_octave PRIVATE src)
target_compile_options(toccata_octave PRIVATE -Wall -Wextra)
target_compile_definitions(toccata_octave PRIVATE
    # RP2040-Zero clones may not boot without a longer crystal start-up (SCH-03 note 8).
    PICO_XOSC_STARTUP_DELAY_MULTIPLIER=64
)
target_link_libraries(toccata_octave
    pico_stdlib
    pico_multicore
    pico_unique_id
    hardware_adc
    tinyusb_device
)
# USB is our own MIDI + console device, not the SDK's stdio.
pico_enable_stdio_usb(toccata_octave 0)
pico_enable_stdio_uart(toccata_octave 0)
pico_add_extra_outputs(toccata_octave)
