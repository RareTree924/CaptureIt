#pragma once

// ============================================================
//  CaptureIt build settings ??? flip a switch here and rebuild.
//  A feature that's switched off is left out of the firmware entirely
//  (not just hidden), so it costs no RAM, CPU time or radio.
// ============================================================


// ---- ESP32-CAM photo link (over ESP-NOW) ----------------------------------
// 1 = the camera button in the inventory header, with the live camera view:
//     the photo button asks what is in the photo. The ESP32-CAM goes online so
//     an AI names the objects, SAM 3 outlines them and eBay prices them (Wi-Fi
//     networks and keys: the CAM's secrets.h).
//     Wi-Fi + ESP-NOW is started for it; its ~1.6 MB of PSRAM is only
//     taken while the camera screens are open.
// 0 = that menu item and all camera code are left out, and the radio never
//     starts at all: no Wi-Fi task, no Wi-Fi buffers in RAM, less power draw.
#define ESPNOW_CAMERA_ENABLED   1


// ---- Dev link (over the USB cable) ------------------------------------------
// 1 = while audio is off (the USB pins are free — Settings), the board takes
//     commands over its USB serial port from tools/devlink.py on the PC:
//     screenshots, taps, files to/from the SD card, items, travel. For
//     building and testing the game without touching the board.
// 0 = left out (a shipped game).
#define DEV_LINK_ENABLED        1
