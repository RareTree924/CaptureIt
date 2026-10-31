#include "monsters.h"

// One entry per assets/monsters/<id>.c, via monsters_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see monsters.h).
#define MONSTER_ENTRY(id) extern const monster_def_t k_monster_##id;
#include "monsters_manifest.inc"
#undef MONSTER_ENTRY

const monster_def_t *const s_monsters[] = {
#define MONSTER_ENTRY(id) &k_monster_##id,
#include "monsters_manifest.inc"
#undef MONSTER_ENTRY
    NULL,   // keeps the array non-empty when there are no monsters yet
};
const uint8_t monster_count = sizeof(s_monsters) / sizeof(s_monsters[0]) - 1;
