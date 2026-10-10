#pragma once
// pipeline_msgs.h — ESP-NOW message formats shared by the S3 (CaptureIt) and
// the ESP32-CAM firmware. Keep the two copies identical.
//
// Photo geometry: the CAM windows its OV2640 to the center square and sends
// the S3 480x480 JPEGs, the same framing as the center of a 640x480 shot.
// The photo button's photo is the same square at 640x640 (CAM_PHOTO_SIZE), kept
// on the CAM for the AI and SAM 3; the S3 gets it shrunk to 480x480. Other
// sensors still send 640x480; the S3 crops the center square itself. Either way
// every box and outline below is in 480x480 screen pixels.
//
// The camera screen (take_picture on the S3):
//   S3 -> CAM  CAM_MSG_PREVIEW(id)   CAM -> S3  IMG_START + IMG_CHUNKs   (repeat: the live feed)
//   S3 -> CAM  CAM_MSG_SNAP(id)      the photo button: CAM takes the 640x640 photo, keeps it,
//                                    and sends the S3 its 480x480 copy
//   S3 -> CAM  CAM_MSG_APPRAISE(id, known kinds)  "what is in the photo you sent me?"
//   CAM -> S3  CAM_MSG_STATUS(id, AWAY, secs)   sent BEFORE the CAM leaves channel 1 for
//                                    the real Wi-Fi: while it is away nothing reaches the S3
//   ...        the CAM joins a Wi-Fi network, the AI finds and names the objects, SAM 3
//              outlines them, eBay prices them, the CAM comes back to channel 1...
//   CAM -> S3  CAM_MSG_STATUS(id, ERROR, text)  on failure (ends the request), or
//              CAM_MSG_STATUS(id, INFO, summary), [OUTLINE_START + OUTLINE_CHUNKs],
//              CAM_MSG_LABELS(id), CAM_MSG_TRAITS(id), CAM_MSG_KINDS(id), CAM_MSG_PRICES(id),
//              CAM_MSG_BOXES(id)
//                                    the boxes come last: they complete the result
//
// Camera Wi-Fi (the S3's Settings -> Camera Wi-Fi screen). The networks the CAM goes
// online with live on the CAM (its NVS flash, so they survive reflashing); until the
// S3 first changes them they are secrets.h's. Passwords never come back to the S3:
// it only learns whether one is saved.
//   S3 -> CAM  CAM_MSG_NET_GET(id)         CAM -> S3  CAM_MSG_NET_LIST(id)
//   S3 -> CAM  CAM_MSG_NET_SET(id, op ...) CAM -> S3  CAM_MSG_NET_LIST(id) when saved, or
//                                                      CAM_MSG_STATUS(id, ERROR, why)
//   S3 -> CAM  CAM_MSG_NET_TEST(id)        CAM -> S3  STATUS(id, AWAY, secs), then (once back
//                                          on channel 1) STATUS(id, INFO, "Connected to ...")
//                                          or STATUS(id, ERROR, why)

#include <stddef.h>
#include <stdint.h>

// 0x01 and 0x06 were old requests: not reused.
#define CAM_MSG_BOXES         0x02   // CAM -> S3  : bounding boxes for that photo
#define CAM_MSG_IMG_START     0x03   // CAM -> S3  : a JPEG is about to follow
#define CAM_MSG_IMG_CHUNK     0x04   // CAM -> S3  : one slice of that JPEG
#define CAM_MSG_PREVIEW       0x05   // S3  -> CAM : live view: "take a photo and send it to me"
#define CAM_MSG_OUTLINE_START 0x07   // CAM -> S3  : the outline bitmap is about to follow (cam_img_start_msg_t layout)
#define CAM_MSG_OUTLINE_CHUNK 0x08   // CAM -> S3  : one slice of it (cam_img_chunk_msg_t layout)
#define CAM_MSG_SNAP          0x09   // S3  -> CAM : "take the photo": 640x640 kept, 480x480 copy to me
#define CAM_MSG_APPRAISE      0x0A   // S3  -> CAM : what is in the photo of frame_id
#define CAM_MSG_STATUS        0x0B   // CAM -> S3  : one line for the screen (cam_status_msg_t)
#define CAM_MSG_LABELS        0x0C   // CAM -> S3  : the AI's names for the boxes that follow (cam_labels_msg_t)
#define CAM_MSG_PRICES        0x0D   // CAM -> S3  : eBay prices for the boxes that follow (cam_prices_msg_t)
#define CAM_MSG_TRAITS        0x0E   // CAM -> S3  : the AI's traits for the boxes that follow (cam_traits_msg_t)
#define CAM_MSG_KINDS         0x0F   // CAM -> S3  : what kind each box is, for the daily selling limit (cam_kinds_msg_t)
#define CAM_MSG_NET_GET       0x10   // S3  -> CAM : "which Wi-Fi networks do you have?" (cam_request_msg_t)
#define CAM_MSG_NET_LIST      0x11   // CAM -> S3  : the networks, no passwords (cam_net_list_msg_t)
#define CAM_MSG_NET_SET       0x12   // S3  -> CAM : save / delete / move one network (cam_net_set_msg_t)
#define CAM_MSG_NET_TEST      0x13   // S3  -> CAM : "try to go online now" (cam_request_msg_t)

#define CAM_OUT_SIZE       480                // final square image, in pixels
#define CAM_PHOTO_SIZE     640                // the photo button's photo, as the AI and SAM 3 get it
#define CAM_MAX_BOXES      25
#define CAM_CHUNK_BYTES    1460               // JPEG bytes per ESP-NOW packet (needs ESP-NOW v2 on both ends)
#define CAM_JPEG_MAX_BYTES (96 * 1024)        // largest photo either side accepts

// Object outlines as a 1-bit 480x480 picture: row-major, 60 bytes per row,
// the most significant bit is the leftmost pixel. A set bit is a border pixel.
#define CAM_OUTLINE_BYTES  (CAM_OUT_SIZE * CAM_OUT_SIZE / 8)

// Every S3 -> CAM request (CAM_MSG_APPRAISE's is longer: cam_appraise_msg_t).
typedef struct __attribute__((packed)) {
    uint8_t type;        // CAM_MSG_PREVIEW or CAM_MSG_SNAP
    uint8_t frame_id;    // S3 increments this per photo; every reply echoes it
} cam_request_msg_t;

// Things are told apart by kind: the AI's 1-2 plain words ("couch", "sandal").
// The game sells one of each kind a day, so CAM_MSG_APPRAISE carries the kinds
// the player has sold today or holds as photo items, and the AI says which of
// them each thing in the photo is: another photo of the same couch, or a sofa
// just like it, is still a "couch". Only count names are sent.
#define CAM_KIND_LEN       24
#define CAM_KNOWN_MAX      16
typedef struct __attribute__((packed)) {
    uint8_t type;        // CAM_MSG_APPRAISE
    uint8_t frame_id;    // the photo (its CAM_MSG_SNAP)
    uint8_t count;
    char    known[CAM_KNOWN_MAX][CAM_KIND_LEN];
} cam_appraise_msg_t;

// Each box's kind, in box order: the known kind it matched, else the AI's own word.
typedef struct __attribute__((packed)) {
    uint8_t type;        // CAM_MSG_KINDS
    uint8_t frame_id;
    uint8_t count;
    char    kind[CAM_MAX_BOXES][CAM_KIND_LEN];
} cam_kinds_msg_t;

typedef struct __attribute__((packed)) {
    uint16_t x, y, w, h; // top-left corner + size, in 480x480 pixels
} cam_box_t;

// Sent last: the boxes complete the result (outline, labels and prices came before).
typedef struct __attribute__((packed)) {
    uint8_t   type;         // CAM_MSG_BOXES
    uint8_t   frame_id;
    uint16_t  img_w, img_h; // always CAM_OUT_SIZE x CAM_OUT_SIZE now
    uint8_t   count;        // number of valid entries in boxes[]
    cam_box_t boxes[CAM_MAX_BOXES];
} cam_boxes_msg_t;

typedef struct __attribute__((packed)) {
    uint8_t  type;          // CAM_MSG_IMG_START or CAM_MSG_OUTLINE_START
    uint8_t  frame_id;
    uint32_t jpeg_len;      // total size in bytes (JPEG, or CAM_OUTLINE_BYTES)
    uint16_t chunk_count;   // how many chunk packets follow
} cam_img_start_msg_t;

typedef struct __attribute__((packed)) {
    uint8_t  type;          // CAM_MSG_IMG_CHUNK or CAM_MSG_OUTLINE_CHUNK
    uint8_t  frame_id;
    uint16_t index;         // chunk number, 0-based; byte offset = index * CAM_CHUNK_BYTES
    uint8_t  data[CAM_CHUNK_BYTES];  // the last chunk is sent shorter
} cam_img_chunk_msg_t;

// What the CAM tells the player during an appraisal. Printable ASCII, only
// the characters are sent (packet length says how many).
#define CAM_STATUS_MAX     120
#define CAM_STATUS_INFO    0   // progress or the result's summary
#define CAM_STATUS_AWAY    1   // the CAM is going online now: secs = how long it expects to be gone
#define CAM_STATUS_ERROR   2   // it failed: text says why; the request is over
typedef struct __attribute__((packed)) {
    uint8_t type;           // CAM_MSG_STATUS
    uint8_t frame_id;
    uint8_t kind;           // CAM_STATUS_*
    uint8_t secs;
    char    text[CAM_STATUS_MAX];
} cam_status_msg_t;

// One name per box, in box order, each zero-padded to CAM_LABEL_LEN. Only
// count slots are sent; it needs ESP-NOW v2 (more than 250 bytes) like the chunks.
#define CAM_LABEL_LEN      32
typedef struct __attribute__((packed)) {
    uint8_t type;           // CAM_MSG_LABELS
    uint8_t frame_id;
    uint8_t count;
    char    label[CAM_MAX_BOXES][CAM_LABEL_LEN];
} cam_labels_msg_t;

// Market prices per box, in cents of `currency`: halfway between the AI's used
// value and the middle eBay asking price of current fixed-price listings under the
// box's name (only those between half the AI's used value and 1.5x its new price:
// no covers, parts or sets); lo/hi = eBay's typical range (quartiles). When eBay
// has nothing, the AI's value alone (lo = hi = 0). mid == 0: no price at all.
typedef struct __attribute__((packed)) {
    uint32_t mid, lo, hi;
} cam_price_t;
typedef struct __attribute__((packed)) {
    uint8_t     type;       // CAM_MSG_PRICES
    uint8_t     frame_id;
    uint8_t     count;
    char        currency[4];   // "CAD", zero-terminated
    cam_price_t price[CAM_MAX_BOXES];
} cam_prices_msg_t;

// The AI's traits per box: the first says how good the photo of the thing is
// ("Crisp Shot", "Blurry"), the rest what shows of the thing itself ("Worn",
// "Vintage"). pct is what a trait does to the value: 100 = nothing, 130 = x1.3.
// An item's price is the market price times every one of its traits' pct.
// Sent in parts of up to CAM_TRAITS_BOXES boxes (one packet can't hold 25).
#define CAM_TRAITS_PER     5
#define CAM_TRAIT_LEN      15                 // text, zero-terminated ("" = no trait)
#define CAM_TRAITS_BOXES   15                 // boxes per traits message
typedef struct __attribute__((packed)) {
    char    text[CAM_TRAIT_LEN];
    uint8_t pct;                              // 25..250
} cam_trait_t;
typedef struct __attribute__((packed)) {
    uint8_t     type;       // CAM_MSG_TRAITS
    uint8_t     frame_id;
    uint8_t     first;      // box index of trait[0]
    uint8_t     count;      // boxes in this part
    cam_trait_t trait[CAM_TRAITS_BOXES][CAM_TRAITS_PER];
} cam_traits_msg_t;

// The CAM's Wi-Fi networks, tried in list order. user empty = home Wi-Fi (WPA2/WPA3-
// Personal: the password is the Wi-Fi password); user set = school/work Wi-Fi that asks
// for a login (WPA2/WPA3-Enterprise, eduroam): user + password are that login.
#define CAM_NET_MAX        5
#define CAM_NET_SSID_LEN   33                 // 32 + the zero
#define CAM_NET_PASS_LEN   64                 // 63 (WPA2's longest passphrase) + the zero
#define CAM_NET_USER_LEN   64
#define CAM_NET_HAS_PASS   0x01               // NET_LIST: a password is saved for it
#define CAM_NET_PAP        0x02               // school Wi-Fi: TTLS with PAP inner login (else MSCHAPv2)
#define CAM_NET_KEEP_PASS  0x04               // NET_SET save: keep the saved password (pass is ignored)
typedef struct __attribute__((packed)) {
    char    ssid[CAM_NET_SSID_LEN];
    char    user[CAM_NET_USER_LEN];           // "" = home Wi-Fi
    char    anon[CAM_NET_USER_LEN];           // school Wi-Fi's outer ("anonymous") identity, "" = user
    uint8_t flags;                            // CAM_NET_*
} cam_net_info_t;

typedef struct __attribute__((packed)) {
    uint8_t        type;     // CAM_MSG_NET_LIST
    uint8_t        frame_id; // the NET_GET / NET_SET it answers
    uint8_t        count;
    cam_net_info_t net[CAM_NET_MAX];
} cam_net_list_msg_t;

#define CAM_NET_OP_SAVE    0   // slot < count: replace that network; slot == count: add one
#define CAM_NET_OP_DELETE  1   // remove slot
#define CAM_NET_OP_UP      2   // move slot one up (tried sooner)
#define CAM_NET_OP_RESET   3   // forget the S3's changes: back to secrets.h's list
typedef struct __attribute__((packed)) {
    uint8_t        type;     // CAM_MSG_NET_SET
    uint8_t        frame_id;
    uint8_t        op;       // CAM_NET_OP_*
    uint8_t        slot;
    cam_net_info_t net;      // SAVE only (flags: CAM_NET_PAP, CAM_NET_KEEP_PASS)
    char           pass[CAM_NET_PASS_LEN];   // SAVE only: "" = open network (unless KEEP_PASS)
} cam_net_set_msg_t;

// Bytes before the variable part. A boxes packet is BOXES_HEADER + N boxes;
// a chunk packet is CHUNK_HEADER + its data length; and so on.
#define CAM_BOXES_HEADER_SIZE  (offsetof(cam_boxes_msg_t, boxes))
#define CAM_CHUNK_HEADER_SIZE  (offsetof(cam_img_chunk_msg_t, data))
#define CAM_STATUS_HEADER_SIZE (offsetof(cam_status_msg_t, text))
#define CAM_LABELS_HEADER_SIZE (offsetof(cam_labels_msg_t, label))
#define CAM_PRICES_HEADER_SIZE (offsetof(cam_prices_msg_t, price))
#define CAM_TRAITS_HEADER_SIZE (offsetof(cam_traits_msg_t, trait))
#define CAM_TRAITS_ITEM_SIZE   (CAM_TRAITS_PER * sizeof(cam_trait_t))   // one box's traits
#define CAM_APPRAISE_HEADER_SIZE (offsetof(cam_appraise_msg_t, known))
#define CAM_KINDS_HEADER_SIZE  (offsetof(cam_kinds_msg_t, kind))
#define CAM_NET_LIST_HEADER_SIZE (offsetof(cam_net_list_msg_t, net))
#define CAM_OUTLINE_CHUNKS     ((CAM_OUTLINE_BYTES + CAM_CHUNK_BYTES - 1) / CAM_CHUNK_BYTES)

// ESP-NOW v2 payloads are limited to 1470 bytes (ESP_NOW_MAX_DATA_LEN_V2).
// The boxes and status messages stay within the v1 limit of 250 (the CAM
// keeps the boxes in a 250-byte buffer).
_Static_assert(sizeof(cam_boxes_msg_t)     <= 250,  "boxes message too big for ESP-NOW");
_Static_assert(sizeof(cam_status_msg_t)    <= 250,  "status message too big for ESP-NOW");
_Static_assert(sizeof(cam_img_chunk_msg_t) <= 1470, "chunk message too big for ESP-NOW v2");
_Static_assert(sizeof(cam_labels_msg_t)    <= 1470, "labels message too big for ESP-NOW v2");
_Static_assert(sizeof(cam_prices_msg_t)    <= 1470, "prices message too big for ESP-NOW v2");
_Static_assert(sizeof(cam_traits_msg_t)    <= 1470, "traits message too big for ESP-NOW v2");
_Static_assert(sizeof(cam_appraise_msg_t)  <= 1470, "appraise request too big for ESP-NOW v2");
_Static_assert(sizeof(cam_kinds_msg_t)     <= 1470, "kinds message too big for ESP-NOW v2");
_Static_assert(sizeof(cam_net_list_msg_t)  <= 1470, "network list too big for ESP-NOW v2");
_Static_assert(sizeof(cam_net_set_msg_t)   <= 250,  "network message too big for ESP-NOW");
_Static_assert(CAM_OUT_SIZE % 8 == 0, "outline rows must be whole bytes");
