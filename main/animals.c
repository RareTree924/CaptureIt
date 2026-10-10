#include "animals.h"

// One entry per assets/animals/<id>.c, via animals_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see animals.h).
#define ANIMAL_ENTRY(id) extern const animal_def_t k_animal_##id;
#include "animals_manifest.inc"
#undef ANIMAL_ENTRY

const animal_def_t *const s_animals[] = {
#define ANIMAL_ENTRY(id) &k_animal_##id,
#include "animals_manifest.inc"
#undef ANIMAL_ENTRY
    NULL,   // keeps the array non-empty when there are no animals yet
};
const uint8_t animal_count = sizeof(s_animals) / sizeof(s_animals[0]) - 1;
