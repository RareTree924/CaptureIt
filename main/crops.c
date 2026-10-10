#include "crops.h"

// One entry per assets/crops/<id>.c, via crops_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see crops.h).
#define CROP_ENTRY(id) extern const crop_def_t k_crop_##id;
#include "crops_manifest.inc"
#undef CROP_ENTRY

const crop_def_t *const s_crops[] = {
#define CROP_ENTRY(id) &k_crop_##id,
#include "crops_manifest.inc"
#undef CROP_ENTRY
    NULL,   // keeps the array non-empty when there are no crops yet
};
const uint8_t crop_count = sizeof(s_crops) / sizeof(s_crops[0]) - 1;
