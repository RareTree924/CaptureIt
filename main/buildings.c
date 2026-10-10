#include "buildings.h"

// One entry per assets/buildings/<id>.c, via buildings_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see buildings.h).
#define BUILDING_ENTRY(id) extern const building_def_t k_building_##id;
#include "buildings_manifest.inc"
#undef BUILDING_ENTRY

const building_def_t *const s_buildings[] = {
#define BUILDING_ENTRY(id) &k_building_##id,
#include "buildings_manifest.inc"
#undef BUILDING_ENTRY
    NULL,   // keeps the array non-empty when there are no buildings yet
};
const uint8_t building_count = sizeof(s_buildings) / sizeof(s_buildings[0]) - 1;
