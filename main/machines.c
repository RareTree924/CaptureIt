#include "machines.h"

// One entry per assets/machines/<id>.c, via machines_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see machines.h).
#define MACHINE_ENTRY(id) extern const machine_def_t k_machine_##id;
#include "machines_manifest.inc"
#undef MACHINE_ENTRY

const machine_def_t *const s_machines[] = {
#define MACHINE_ENTRY(id) &k_machine_##id,
#include "machines_manifest.inc"
#undef MACHINE_ENTRY
    NULL,   // keeps the array non-empty when there are no machines yet
};
const uint8_t machine_count = sizeof(s_machines) / sizeof(s_machines[0]) - 1;
