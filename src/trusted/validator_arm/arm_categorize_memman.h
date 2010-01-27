/*
 * Copyright 2009 The Native Client Authors. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can
 * be found in the LICENSE file.
 */

/*
 * Define a memory manager for handling memory on ARM instruction tries.
 * This API is defined so that we can swap in different memory strategies
 * to deal with the large amount of memory generated by this API.
 */

#ifndef NATIVE_CLIENT_PRIVATE_TOOLS_NCV_ARM_ARM_CATEGORIZE_MEMMAN_H__
#define NATIVE_CLIENT_PRIVATE_TOOLS_NCV_ARM_ARM_CATEGORIZE_MEMMAN_H__

#include "native_client/src/trusted/validator_arm/arm_categorize.h"

EXTERN_C_BEGIN

/*
 * Alcloate an instance of an ArmInstructionList;
 */
ArmInstructionList* MallocArmInstructionListNode();

/*
 * Free an instance of an ArmInstructionList allocated using
 * MallocArmInstructionList.
 */
void FreeArmInstructionListNode(ArmInstructionList* node);

/*
 * Delete all instruction list nodes in the given list.
 */
void FreeArmInstructionList(ArmInstructionList* list);

/*
 * Allocate an instance of an ArmInstructionTrie.
 */
ArmInstructionTrie* MallocArmInstructionTrie();

/*
 * Free an instance of an ArmInstructionTrie allocated using
 * MallocArmInstructionTrie.
 */
void FreeArmInstructionTrie(ArmInstructionTrie* node);

EXTERN_C_END

#endif  /* NATIVE_CLIENT_PRIVATE_TOOLS_NCV_ARM_ARM_CATEGORIZE_MEMMAN_H__ */
