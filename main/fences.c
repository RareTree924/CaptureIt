#include "fences.h"

// One entry per assets/fences/<id>.c, via fences_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see fences.h).
#define FENCE_ENTRY(id) extern const fence_def_t k_fence_##id;
#include "fences_manifest.inc"
#undef FENCE_ENTRY

const fence_def_t *const s_fences[] = {
#define FENCE_ENTRY(id) &k_fence_##id,
#include "fences_manifest.inc"
#undef FENCE_ENTRY
    NULL,   // keeps the array non-empty when there are no fences yet
};
const uint8_t fence_count = sizeof(s_fences) / sizeof(s_fences[0]) - 1;
