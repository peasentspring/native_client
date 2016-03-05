// Copyright 2016 The Native Client Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef NATIVE_CLIENT_SRC_UNTRUSTED_PLL_LOADER_PLL_ROOT_H_
#define NATIVE_CLIENT_SRC_UNTRUSTED_PLL_LOADER_PLL_ROOT_H_ 1

#include <stddef.h>

// This is the root data structure exported by a PLL (PNaCl/portable
// loadable library).
struct PLLRoot {
  size_t format_version;
  const char *string_table;

  // Exports.
  void *const *exported_ptrs;
  const size_t *exported_names;
  size_t export_count;

  // Imports.
  void *const *imported_ptrs;
  const size_t *imported_names;
  size_t import_count;

  // Hash Table, for quick exported symbol lookup.
  size_t bucket_count;
  const int32_t *hash_buckets;
  const uint32_t *hash_chains;

  // Bloom Filter, for quick exported symbol lookup rejection.
  size_t bloom_filter_maskwords_bitmask;
  // The number of right shifts to generate the second hash from the first.
  size_t bloom_filter_shift2;
  const uint32_t *bloom_filter_data;
};

#endif
