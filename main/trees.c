#include "trees.h"

// One entry per assets/trees/<id>.c, via trees_manifest.inc — which
// main/CMakeLists.txt regenerates from whatever files are there (see trees.h).
#define TREE_ENTRY(id) extern const tree_def_t k_tree_##id;
#include "trees_manifest.inc"
#undef TREE_ENTRY

const tree_def_t *const s_trees[] = {
#define TREE_ENTRY(id) &k_tree_##id,
#include "trees_manifest.inc"
#undef TREE_ENTRY
    NULL,   // keeps the array non-empty when there are no trees yet
};
const uint8_t tree_count = sizeof(s_trees) / sizeof(s_trees[0]) - 1;
