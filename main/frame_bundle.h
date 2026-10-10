#pragma once
#include <stdint.h>
#include <stdbool.h>

// ============================================================
//  FRAME BUNDLE — the one reusable animation building block shared by
//  item passive/use art, map ambient animations, and breakable hit
//  effects.
//
//  A bundle is just: a strip of frames, how long each stays up, and how
//  many times to loop. Frame index and "is it done" are computed from
//  elapsed time (see the helpers below) instead of being stepped one
//  frame at a time or unrolled into a bigger stored sequence — so a
//  breakable that takes 20 hits reuses the SAME 3-frame hit bundle for
//  every hit, rather than needing 20x3 unique baked frames.
//
//  loop_count means different things depending on who's playing the
//  bundle (see bundle_frame_by_loop_count / bundle_frame_passes below):
//   - Ambient use (map animations, an item's passive hold): loop_count
//     is authoritative. -1 = loop forever (the old always-looping
//     behavior). 0 or N = play that many passes, then hold the last
//     frame — e.g. a one-shot splash effect placed on the map.
//   - Item "use": same rule — loop_count is how many times the swing
//     plays before holding.
//   - A breakable's hit flash: always exactly ONE pass, regardless of
//     the bundle's own loop_count — repetition there comes from the
//     hit count, not the bundle, so the same bundle can be shared with
//     an ambient placement elsewhere on the map without the two
//     stepping on each other's meaning.
// ============================================================
#define BUNDLE_MAX_FRAMES 64   // frames per bundle (the editor enforces the same cap)

typedef struct {
    uint16_t        w, h;          // size of ONE frame, in pixels
    uint16_t        frame_count;   // 0 = no animation (a static image / "none")
    uint16_t        interval_ms;   // how long each frame stays on screen
    int16_t         loop_count;    // -1 = forever; else passes to play before holding
    const uint16_t *pixels;        // frame_count * w * h pixels, frame after frame
                                    // (opaque for map ambient art and a
                                    // breakable's idle/gone state art;
                                    // colorkeyed 0x0000-transparent for item
                                    // art and a breakable's hit-flash bundle)
} frame_bundle_t;

// Whole frames elapsed, ignoring loop count.
static inline uint32_t bundle_raw_frame(const frame_bundle_t *b, uint32_t elapsed_ms)
{
    if (!b || b->frame_count == 0 || b->interval_ms == 0) return 0;
    return elapsed_ms / b->interval_ms;
}

// Always loops, regardless of the bundle's own loop_count. Use for
// ambient playback you never expect to finish mid-conversation (e.g. an
// item's passive/held look).
static inline uint16_t bundle_frame_looping(const frame_bundle_t *b, uint32_t elapsed_ms)
{
    if (!b || b->frame_count == 0) return 0;
    return (uint16_t)(bundle_raw_frame(b, elapsed_ms) % b->frame_count);
}

// Plays exactly `passes` full cycles of the bundle, then holds the last
// frame and reports finished=true. `passes` is supplied by the caller
// (not read from the bundle) so the same bundle asset can mean "loop
// forever" in one context and "play once" in another.
static inline uint16_t bundle_frame_passes(const frame_bundle_t *b, uint32_t elapsed_ms,
                                            uint32_t passes, bool *finished)
{
    if (!b || b->frame_count == 0 || passes == 0) { if (finished) *finished = true; return 0; }
    uint32_t total = passes * b->frame_count;
    uint32_t raw   = bundle_raw_frame(b, elapsed_ms);
    if (raw >= total) { if (finished) *finished = true; return (uint16_t)(b->frame_count - 1); }
    if (finished) *finished = false;
    return (uint16_t)(raw % b->frame_count);
}

// Ambient/item-use playback: honors the bundle's own loop_count
// (-1 = forever, else that many passes then hold).
static inline uint16_t bundle_frame_by_loop_count(const frame_bundle_t *b, uint32_t elapsed_ms, bool *finished)
{
    if (b && b->loop_count < 0) { if (finished) *finished = false; return bundle_frame_looping(b, elapsed_ms); }
    return bundle_frame_passes(b, elapsed_ms, b ? (uint32_t)(b->loop_count + 1) : 0, finished);
}

// ms until bundle_frame_by_loop_count() would next possibly return a
// different frame — an early-out so a per-tick poll can skip bundles
// that aren't due yet instead of re-doing the math every frame.
static inline uint32_t bundle_next_boundary_ms(const frame_bundle_t *b, uint32_t start_ms, uint32_t elapsed_ms)
{
    if (!b || b->frame_count == 0 || b->interval_ms == 0) return start_ms;
    return start_ms + (bundle_raw_frame(b, elapsed_ms) + 1) * (uint32_t)b->interval_ms;
}
