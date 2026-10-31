#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every monster is made in the Game Tools Monsters tab (or cut from a sprite
// sheet by tools/slice_monsters.py, in the same format) and exported as ONE
// file, assets/monsters/<id>.c, holding k_monster_<id>. main/CMakeLists.txt
// adds it to s_monsters[], so nothing is hand-edited per monster. All of it
// is const: the art stays in flash and costs no RAM.
//
// Where they come up (MONSTERS in main.c): on a mining map (the Map Editor's
// "Mining map…": <map>.spawn's "monsters N" and "monster <id> W" lines), a
// fresh lot every time the player comes onto the map. They wander, and chase
// the player once they're within wake_tiles; touching the player hurts them
// (damage, less nothing — the player has no armour yet). A weapon's swing
// (an item with "weapon N") hits them: N - defense, at least 1, and knocks
// them back. At 0 hp they play their death frames, leave a few particles
// that fly out and fade, drop their drops and give combat xp.
//
// Art: frame_count frames of fw x fh RGB565 (0x0000 = see-through), frame
// after frame; a frame's bottom middle stands on the monster's feet. seq[]
// lists which frames each animation plays, seq_len[] how many (up to
// MON_SEQ_MAX):
//   DOWN/RIGHT/UP/LEFT  walking that way. No LEFT: RIGHT mirrored. Only
//                       DOWN: every way (a bat flapping).
//   REST                a hiding one's look while it waits (MON_HIDES: a
//                       rock crab's rock); a looping one's idle otherwise
//   WAKE                played once as it pops out (then it chases)
//   DEATH               played once at 0 hp (none: it just goes)
//   ATTACK_DOWN..LEFT   played while it attacks: dashing (MON_CHARGES), or
//                       a moment each time it hurts the player. Missing ways
//                       as for walking; none at all: its walk.
// particles: particle_count pictures of MON_PARTICLE x MON_PARTICLE (the
// bits it leaves behind: bones, goo, feathers), flung out when it dies.
#define MON_FRAME_MAX  32   // px, either side
#define MON_SEQ_MAX    8
#define MON_PARTICLE   16   // a particle's picture, px square
#define MON_PARTICLES  4    // at most this many

enum {
    MON_SEQ_DOWN = 0,
    MON_SEQ_RIGHT,
    MON_SEQ_UP,
    MON_SEQ_LEFT,
    MON_SEQ_REST,
    MON_SEQ_WAKE,
    MON_SEQ_DEATH,
    MON_SEQ_ATTACK_DOWN,
    MON_SEQ_ATTACK_RIGHT,
    MON_SEQ_ATTACK_UP,
    MON_SEQ_ATTACK_LEFT,
    MON_SEQ_COUNT
};

// What it can do (abilities). The Monsters tab's names are the same, lowercase.
#define MON_FLIES     0x0001   // flies: walls don't stop it (bats, ghosts, flies)
#define MON_HIDES     0x0002   // hides (REST) until the player comes near, pops out (WAKE), chases; hides again if they get away
#define MON_HOPS      0x0004   // moves in hops: a burst, a pause (dust sprites, slimes)
#define MON_ERRATIC   0x0008   // darts about at random on its way (haunted skulls, flies)
#define MON_CHARGES   0x0010   // stops, then dashes at the player at 3x its speed (its ATTACK frames while it does)
#define MON_REVIVES   0x0020   // collapses at 0 hp and gets up again a while later with half its hp — unless hit while down (mummies)
#define MON_HEALS     0x0040   // now and then heals the hurt monsters near it (shadow shamans)
#define MON_STRAIGHT  0x0080   // flies in straight lines, turning at walls, never chases (bugs)
#define MON_KEEPS_OFF 0x0100   // keeps a few tiles away from the player instead of touching them (casters)
#define MON_GHOSTLY   0x0200   // see-through-ish: flickers (ghosts)
#define MON_SHOOTS    0x0400   // shoots at the player (proj below) every shoot_ms while they're within shoot_tiles
                               // (skeletons' bones, mages' fireballs); shot from a flier, it flies over walls too

// A shot's pictures (MON_PROJECTILE x MON_PROJECTILE, the shot in the middle), up to MON_PROJ_FRAMES, played in a loop.
#define MON_PROJECTILE  16
#define MON_PROJ_FRAMES 4

typedef struct {
    const char *item;     // item id
    uint8_t     chance;   // % (each drop on its own)
    uint8_t     min, max;
} mon_drop_t;

typedef struct {
    const char     *id;
    const char     *name;            // shown when it's hit / killed
    uint8_t         fw, fh;          // frame size, px (at most MON_FRAME_MAX)
    uint8_t         frame_count;
    const uint16_t *frames;          // frame_count x fw*fh
    uint8_t         seq_len[MON_SEQ_COUNT];
    uint8_t         seq[MON_SEQ_COUNT][MON_SEQ_MAX];
    uint16_t        frame_ms;        // how long each frame of an animation shows
    uint16_t        hp;
    uint8_t         damage;          // what touching the player costs them
    uint8_t         defense;         // taken off every hit it takes
    uint8_t         speed_q;         // quarter pixels a game tick (the player walks 12)
    uint8_t         xp;              // combat xp for killing it
    uint8_t         wake_tiles;      // how near (tiles) the player must come for it to notice them
    uint16_t        abilities;       // MON_* bits
    uint8_t         particle_count;
    const uint16_t *particles;       // particle_count x MON_PARTICLE*MON_PARTICLE
    uint8_t         drop_count;
    const mon_drop_t *drops;
    // Its own sounds (WAVs in sounds/sound effects, no ".wav"). "" or NULL = "<id>_hit",
    // "<id>_die", "<id>_wake", "<id>_attack" (rock_crab_hit.wav...): silent until that's on the card.
    const char     *sound;           // it takes a hit
    const char     *sound_die;       // it dies (or collapses, a reviver)
    const char     *sound_wake;      // it pops out / notices the player
    const char     *sound_attack;    // it hurts the player / starts a dash / shoots
    // ---- MON_SHOOTS (all 0: it doesn't) ----
    uint8_t         proj_count;      // its shot's pictures...
    const uint16_t *proj;            // ...proj_count x MON_PROJECTILE*MON_PROJECTILE
    uint8_t         proj_damage;     // what a shot costs the player
    uint8_t         proj_speed_q;    // quarter px a game tick it flies (0 = 20)
    uint16_t        shoot_ms;        // at most this often (0 = 2000)
    uint8_t         shoot_tiles;     // from this near (0 = 6)
} monster_def_t;

extern const monster_def_t *const s_monsters[];
extern const uint8_t              monster_count;
