#!/bin/bash
# Copyright (c) 2012 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Run toolchain torture tests and llvm testsuite tests.
# For now, run on linux64, build and run unsandboxed newlib tests
# for all 3 architectures.
# Note: This script builds the toolchain from scratch but does
#       not build the translators and hence the translators
#       are from an older revision, see comment below.

set -o xtrace
set -o nounset
set -o errexit

# This hopefully needs to be updated rarely
ARCHIVED_PEXE_TRANSLATOR_REV=8834


readonly PNACL_BUILD="pnacl/build.sh"
readonly UP_DOWN_LOAD="buildbot/file_up_down_load.sh"
readonly TORTURE_TEST="tools/toolchain_tester/torture_test.sh"
readonly LLVM_TESTSUITE="pnacl/scripts/llvm-test-suite.sh"
# build.sh, llvm test suite and torture tests all use this value
export PNACL_CONCURRENCY=${PNACL_CONCURRENCY:-4}

# Change the  toolchain build script (PNACL_BUILD) behavior slightly
# wrt to error logging and mecurial retry delays.
# TODO(robertm): if this special casing is still needed,
#                make this into separate vars
export PNACL_BUILDBOT=true
# Make the toolchain build script (PNACL_BUILD) more verbose.
# This will also prevent bot timeouts which otherwise gets triggered
# by long periods without console output.
export PNACL_VERBOSE=true

clobber() {
  echo @@@BUILD_STEP clobber@@@
  rm -rf scons-out
  # Don't clobber toolchain/pnacl_translator; these bots currently don't build
  # it, but they use the DEPSed-in version
  rm -rf toolchain/pnacl_linux* toolchain/pnacl_mac* toolchain/pnacl_win*
  # Try to clobber /tmp/ contents to clear temporary chrome files.
  rm -rf /tmp/.org.chromium.Chromium.*
}

handle-error() {
  echo "@@@STEP_FAILURE@@@"
}

#### Support for running arm sbtc tests on this bot, since we have
# less coverage on the main waterfall now:
# http://code.google.com/p/nativeclient/issues/detail?id=2581
readonly SCONS_COMMON="./scons --verbose bitcode=1"
build-sbtc-prerequisites() {
  local platform=$1
  ${SCONS_COMMON} platform=${platform} sel_ldr sel_universal irt_core \
    -j ${PNACL_CONCURRENCY}
}


scons-tests-pic() {
  local platform=$1

  echo "@@@BUILD_STEP scons-tests-pic [${platform}]@@@"
  local extra="--mode=opt-host,nacl \
               -j${PNACL_CONCURRENCY} -k \
               nacl_pic=1  pnacl_generate_pexe=0"
  ${SCONS_COMMON} ${extra} platform=${platform} smoke_tests || handle-error
}


scons-tests-translator() {
  local platform=$1

  echo "@@@BUILD_STEP scons-sb-translator [${platform}] [prereq]@@@"
  build-sbtc-prerequisites ${platform}

  local use_sbtc="use_sandboxed_translator=1"
  local extra="--mode=opt-host,nacl -j${PNACL_CONCURRENCY} ${use_sbtc} -k"
  for group in smoke_tests large_tests ; do
      echo "@@@BUILD_STEP scons-sb-translator [${platform}] [${group}]@@@"
      ${SCONS_COMMON} ${extra} platform=${platform} ${group} || handle-error
  done
}


archived-pexe-translator-test() {
  local arch=$1
  echo "@@@BUILD_STEP archived_pexe_translator \
        $arch rev ${ARCHIVED_PEXE_TRANSLATOR_REV} @@@"
  local dir="$(pwd)/pexe_archive"
  local tarball="${dir}/pexes.tar.bz2"
  local measure_cmd="/usr/bin/time -v"
  local strip="toolchain/pnacl_linux_x86_64/newlib/bin/pnacl-strip"
  local sb_translator="${measure_cmd} \
                       toolchain/pnacl_translator/bin/pnacl-translate"
  rm -rf ${dir}
  mkdir -p ${dir}

  ${UP_DOWN_LOAD} DownloadArchivedPexesTranslator \
      ${ARCHIVED_PEXE_TRANSLATOR_REV} ${tarball}
  tar jxf ${tarball} --directory ${dir}

  # do different kinds of stripping - so we can compare sizes
  # we will use the smallest, i.e.  "ext=.strip-all" for translation
  # Note: other tests using archived pexes do not use stripped versions
  #       so we get some coverage for the debug info handling inside of the
  #       translator.
  ${strip} --strip-all   ${dir}/ld-new -o ${dir}/ld-new.strip-all
  ${strip} --strip-debug ${dir}/ld-new -o ${dir}/ld-new.strip-debug
  ${strip} --strip-all   ${dir}/llc    -o ${dir}/llc.strip-all
  ${strip} --strip-debug ${dir}/llc    -o ${dir}/llc.strip-debug
  # http://code.google.com/p/nativeclient/issues/detail?id=2840
  # x86-64 will crash when ext=""
  # pexe archive rev: 8834
  # pre-built translator rev: 8759
  local ext=".strip-all"

  # Note, that the arch flag has two functions:
  # 1) it selects the target arch for the translator
  # 2) combined with --pnacl-sb it selects the host arch for the
  #    sandboxed translators
  local flags="-arch ${arch} --pnacl-sb --pnacl-driver-verbose"
  if [[ ${arch} = arm ]] ; then
      # We need to enable qemu magic for arm
      flags="${flags} --pnacl-use-emulator"
  fi

  ${sb_translator} ${flags} ${dir}/ld-new${ext} -o ${dir}/ld-new-${arch}.nexe
  # This takes about 17min on arm with qemu
  # With an unstripped pexe arm runs out of space (also after 17min):
  # "terminate called after throwing an instance of 'std::bad_alloc'"
  ${sb_translator} ${flags} ${dir}/llc${ext} -o ${dir}/llc-${arch}.nexe

  ls -l ${dir}
  file ${dir}/*

  # now actually run the two new translator nexes on the ld-new pexe
  flags="${flags} \
         --pnacl-driver-set-LLC_SB=${dir}/llc-${arch}.nexe \
         --pnacl-driver-set-LD_SB=${dir}/ld-new-${arch}.nexe"
  ${sb_translator} ${flags} ${dir}/ld-new${ext} -o ${dir}/ld-new-${arch}.2.nexe
}


tc-test-bot() {
  local archset="$1"
  clobber

  echo "@@@BUILD_STEP show-config@@@"
  ${PNACL_BUILD} show-config

  # Build the un-sandboxed toolchain
  echo "@@@BUILD_STEP compile_toolchain@@@"
  ${PNACL_BUILD} clean
  ${PNACL_BUILD} all

  # run the torture tests. the "trybot" phases take care of prerequisites
  # for both test sets
  for arch in ${archset}; do
    echo "@@@BUILD_STEP torture_tests $arch @@@"
    ${TORTURE_TEST} trybot-pnacl-${arch}-torture \
      --concurrency=${PNACL_CONCURRENCY} || handle-error
  done

  for arch in ${archset}; do
    echo "@@@BUILD_STEP llvm-test-suite $arch @@@"
    ${LLVM_TESTSUITE} testsuite-prereq ${arch}
    ${LLVM_TESTSUITE} testsuite-clean

    { ${LLVM_TESTSUITE} testsuite-configure ${arch} &&
        ${LLVM_TESTSUITE} testsuite-run ${arch} &&
        ${LLVM_TESTSUITE} testsuite-report ${arch} -v -c
    } || handle-error

    scons-tests-pic ${arch}
    # Note: we do not build the sandboxed translator on this bot
    # because this would add another 20min to the build time.
    # The upshot of this is that we are using the sandboxed
    # toolchain which is currently deps'ed in.
    # There is a small upside here: we will notice that bitcode has
    # changed in a way that is incompatible with older translators.
    # Todo(pnacl-team): rethink this.
    scons-tests-translator ${arch}

    archived-pexe-translator-test ${arch}
  done

}


if [ $# = 0 ]; then
    tc-test-bot "x86-64 x86-32 arm"
else
    "$@"
fi
