#!/bin/bash
# Copyright (c) 2012 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -o xtrace
set -o nounset
set -o errexit

# Tell build.sh and test.sh that we're a bot.
export PNACL_BUILDBOT=true

# If true, terminate script when first scons error is encountered.
FAIL_FAST=${FAIL_FAST:-true}
# This remembers when any build steps failed, but we ended up continuing.
RETCODE=0

readonly SCONS_COMMON="./scons --verbose bitcode=1"
readonly UP_DOWN_LOAD="buildbot/file_up_down_load.sh"
# This script is used by toolchain bots (i.e. tc-xxx functions)
readonly PNACL_BUILD="pnacl/build.sh"

tc-clobber() {
  local label=$1
  local clobber_translators=$2

  echo @@@BUILD_STEP tc_clobber@@@
  rm -rf toolchain/${label}
  rm -rf toolchain/test-log
  rm -rf pnacl*.tgz pnacl/pnacl*.tgz
  if ${clobber_translators} ; then
      rm -rf toolchain/pnacl_translator
  fi
}

tc-show-config() {
  echo @@@BUILD_STEP show_config@@@
  ${PNACL_BUILD} show-config
}

tc-compile-toolchain() {
  echo @@@BUILD_STEP compile_toolchain@@@
  ${PNACL_BUILD} clean
  ${PNACL_BUILD} everything
  ${PNACL_BUILD} tarball pnacl-toolchain.tgz
  chmod a+r pnacl-toolchain.tgz
}

tc-untar-toolchain() {
  local label=$1
  echo @@@BUILD_STEP untar_toolchain@@@
  # Untar to ensure we can and to place the toolchain where the main build
  # expects it to be.
  rm -rf toolchain/${label}
  mkdir -p toolchain/${label}
  pushd toolchain/${label}
  tar xfz ../../pnacl-toolchain.tgz
  popd
}

tc-build-translator() {
  echo @@@BUILD_STEP compile_translator@@@
  ${PNACL_BUILD} translator-clean-all
  ${PNACL_BUILD} translator-all
}

tc-archive() {
  local label=$1
  echo @@@BUILD_STEP archive_toolchain@@@
  ${UP_DOWN_LOAD} UploadArmUntrustedToolchains ${BUILDBOT_GOT_REVISION} \
    ${label} pnacl-toolchain.tgz
}

tc-archive-translator() {
  echo @@@BUILD_STEP archive_translator@@@
  ${PNACL_BUILD} translator-tarball pnacl-translator.tgz
  ${UP_DOWN_LOAD} UploadArmUntrustedToolchains ${BUILDBOT_GOT_REVISION} \
      pnacl_translator pnacl-translator.tgz
}

tc-build-all() {
  local label=$1
  local is_try=$2
  local build_translator=$3

  # Tell build.sh and test.sh that we're a bot.
  export PNACL_BUILDBOT=true
  # Tells build.sh to prune the install directory (for release).
  export PNACL_PRUNE=true

  clobber
  tc-clobber ${label} ${build_translator}
  tc-show-config
  tc-compile-toolchain
  tc-untar-toolchain ${label}
  if ! ${is_try} ; then
    tc-archive ${label}
  fi

  # NOTE: only one bot needs to do this
  if ${build_translator} ; then
    tc-build-translator
    if ! ${is_try} ; then
      tc-archive-translator
    fi
  fi
}


# extract the relevant scons flags for reporting
relevant() {
  for i in "$@" ; do
    case $i in
      nacl_pic=1)
        echo -n "pic "
        ;;
      use_sandboxed_translator=1)
        echo -n "sbtc "
        ;;
      do_not_run_tests=1)
        echo -n "no_tests "
        ;;
      pnacl_generate_pexe=0)
        echo -n "no_pexe "
        ;;
      --nacl_glibc)
        echo -n "glibc "
        ;;
    esac
  done
}

# called when a scons invocation fails
handle-error() {
  RETCODE=1
  echo "@@@STEP_FAILURE@@@"
  if ${FAIL_FAST} ; then
    echo "FAIL_FAST enabled"
    exit 1
  fi
}

clobber-chrome-tmp() {
  # Try to clobber /tmp/ contents to clear temporary chrome files.
  rm -rf /tmp/.org.chromium.Chromium.*
}

# Clear out object, and temporary directories.
clobber() {
  echo "@@@BUILD_STEP clobber@@@"
  rm -rf scons-out ../xcodebuild ../sconsbuild ../out
}

# Generate filenames for arm bot uploads and downloads
NAME_ARM_UPLOAD() {
  echo -n "${BUILDBOT_BUILDERNAME}/${BUILDBOT_GOT_REVISION}"
}

NAME_ARM_DOWNLOAD() {
  echo -n "${BUILDBOT_TRIGGERED_BY_BUILDERNAME}/${BUILDBOT_GOT_REVISION}"
}

NAME_ARM_TRY_UPLOAD() {
  echo -n "${BUILDBOT_BUILDERNAME}/"
  echo -n "${BUILDBOT_SLAVENAME}/"
  echo -n "${BUILDBOT_BUILDNUMBER}"
}
NAME_ARM_TRY_DOWNLOAD() {
  echo -n "${BUILDBOT_TRIGGERED_BY_BUILDERNAME}/"
  echo -n "${BUILDBOT_TRIGGERED_BY_SLAVENAME}/"
  echo -n "${BUILDBOT_TRIGGERED_BY_BUILDNUMBER}"
}

# Tar up the executables which are shipped to the arm HW bots
archive-for-hw-bots() {
  local name=$1
  local try=$2

  echo "@@@BUILD_STEP tar_generated_binaries@@@"
  # clean out a bunch of files that are not needed
  find scons-out/ \
    \( -name '*.o' -o -name '*.bc' -o -name 'test_results' \) \
    -print0 | xargs -0 rm -rf

  # delete nexes from pexe mode directories to force translation
  # TODO(dschuff) enable this once we can translate on the hw bots
  #find scons-out/*pexe*/ -name '*.nexe' -print0 | xargs -0 rm -f
  tar cvfz arm-scons.tgz scons-out/*arm*

  echo "@@@BUILD_STEP archive_binaries@@@"
  if [[ ${try} == "try" ]] ; then
    ${UP_DOWN_LOAD} UploadArmBinariesForHWBotsTry ${name} arm-scons.tgz
  else
    ${UP_DOWN_LOAD} UploadArmBinariesForHWBots ${name} arm-scons.tgz
  fi
}

# Untar archived executables for HW bots
unarchive-for-hw-bots() {
  local name=$1
  local try=$2

  echo "@@@BUILD_STEP fetch_binaries@@@"
  if [[ ${try} == "try" ]] ; then
    ${UP_DOWN_LOAD} DownloadArmBinariesForHWBotsTry ${name} arm-scons.tgz
  else
    ${UP_DOWN_LOAD} DownloadArmBinariesForHWBots ${name} arm-scons.tgz
  fi

  echo "@@@BUILD_STEP untar_binaries@@@"
  rm -rf scons-out/
  tar xvfz arm-scons.tgz --no-same-owner
}

# Build with gyp - this only exercises the trusted TC and hence this only
# makes sense to run for ARM.
gyp-arm-build() {
  gypmode=$1
  TOOLCHAIN_DIR=native_client/toolchain/linux_arm-trusted
  EXTRA="-isystem ${TOOLCHAIN_DIR}/usr/include \
         -Wl,-rpath-link=${TOOLCHAIN_DIR}/lib/arm-linux-gnueabi \
         -L${TOOLCHAIN_DIR}/lib \
         -L${TOOLCHAIN_DIR}/lib/arm-linux-gnueabi \
         -L${TOOLCHAIN_DIR}/usr/lib \
         -L${TOOLCHAIN_DIR}/usr/lib/arm-linux-gnueabi"
  # Setup environment for arm.

  export AR=arm-linux-gnueabi-ar
  export AS=arm-linux-gnueabi-as
  export CC="arm-linux-gnueabi-gcc-4.5 ${EXTRA} "
  export CXX="arm-linux-gnueabi-g++-4.5 ${EXTRA} "
  export LD=arm-linux-gnueabi-ld
  export RANLIB=arm-linux-gnueabi-ranlib
  export SYSROOT
  export GYP_DEFINES="target_arch=arm \
    sysroot=${TOOLCHAIN_DIR} \
    linux_use_tcmalloc=0 armv7=1 arm_thumb=1"
  export GYP_GENERATOR=make

  # NOTE: this step is also run implicitly as part of
  #        gclient runhooks --force
  #       it uses the exported env vars so we have to run it again
  #
  echo "@@@BUILD_STEP gyp_configure [${gypmode}]@@@"
  cd ..
  native_client/build/gyp_nacl native_client/build/all.gyp
  cd native_client

  echo "@@@BUILD_STEP gyp_compile [${gypmode}]@@@"
  make -C .. -k -j8 V=1 BUILDTYPE=${gypmode}
}

build-sbtc-prerequisites() {
  local platform=$1
  # Sandboxed translators currently only require irt_core since they do not
  # use PPAPI.
  ${SCONS_COMMON} platform=${platform} sel_ldr sel_universal irt_core
}

# Run a single invocation of scons as its own buildbot stage and handle errors
scons-stage() {
  local platform=$1
  local extra=$2
  local test=$3
  echo "@@@BUILD_STEP scons [${platform}] [${test}] \
[$(relevant ${extra})]@@@"
  ${SCONS_COMMON} ${extra} platform=${platform} ${test} || handle-error
}

single-browser-test() {
  local platform=$1
  local extra=$2
  local test=$3

  # if we run mulitple browser test (e.g. on toolchain bots) we
  # may run out of quota without this
  clobber-chrome-tmp

  # Build in parallel (assume -jN specified in extra), but run sequentially.
  # If we do not run tests sequentially, some may fail. E.g.,
  # http://code.google.com/p/nativeclient/issues/detail?id=2019
  scons-stage ${platform} \
    "${extra} browser_headless=1 SILENT=1 do_not_run_tests=1" ${test}
  scons-stage ${platform} "${extra} browser_headless=1 SILENT=1 -j1" \
      ${test}
}

browser-tests() {
  local platform=$1
  local extra=$2
  if [[ "${extra}" =~ --nacl_glibc ]]; then
    # For glibc, only non-pexe mode works for now.
    # We need to ensure psos are translated before running.
    # E.g., run_pm_manifest_file_chrome_browser_test relies on
    # libimc, libweak_ref, etc.
    single-browser-test ${platform} "${extra} pnacl_generate_pexe=0" \
        "chrome_browser_tests"
  else
    # Otherwise, try pexe mode.
    single-browser-test ${platform} "${extra}" "chrome_browser_tests"
  fi
}

# This function is shared between x86-32 and x86-64. All building and testing
# is done on the same bot. Try runs are identical to buildbot runs
mode-buildbot-x86() {
  local bits=$1
  FAIL_FAST=false
  clobber

  # Normal pexe tests. Build all targets, then run (-j4 is a compromise to try
  # to reduce cycle times without making output too difficult to follow)
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j8 -k" ""
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j4 -k" \
    "small_tests medium_tests large_tests"

  # non-pexe tests (Do the build-everything step just to make sure it all still
  # builds as non-pexe)
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j8 -k pnacl_generate_pexe=0"\
    ""
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j4 -k pnacl_generate_pexe=0"\
    "nonpexe_tests"

  # PIC
  scons-stage "x86-${bits}" \
    "--mode=opt-host,nacl -j8 -k nacl_pic=1 pnacl_generate_pexe=0" ""
  scons-stage "x86-${bits}" \
    "--mode=opt-host,nacl -j4 -k nacl_pic=1 pnacl_generate_pexe=0" \
    "small_tests medium_tests large_tests"

  # sandboxed translation
  build-sbtc-prerequisites x86-${bits}
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j8 -k \
    use_sandboxed_translator=1" ""
  scons-stage "x86-${bits}" "--mode=opt-host,nacl -j4 -k \
    use_sandboxed_translator=1" "small_tests medium_tests large_tests"

  browser-tests "x86-${bits}" "--mode=opt-host,nacl,nacl_irt_test -j8 -k"
}

# QEMU upload bot runs this function, and the hardware download bot runs
# mode-buildbot-arm-hw
mode-buildbot-arm() {
  FAIL_FAST=false
  local scons_mode=$1
  local gyp_mode=$2
  local qemuflags="${scons_mode} -j8 -k do_not_run_tests=1"

  clobber

  gyp-arm-build ${gyp_mode}

  # Sanity check
  scons-stage "arm" "${scons_mode}" "run_hello_world_test"

  # Don't run the rest of the tests on qemu, only build them.
  # QEMU is too flaky for the main waterfall

  # Normal pexe mode tests
  scons-stage "arm" "${qemuflags}" ""
  # This extra step is required to translate the pexes (because translation
  # happens as part of CommandSelLdrTestNacl and not part of the
  # build-everything step)
  scons-stage "arm" "${qemuflags}" "small_tests medium_tests large_tests"

  # PIC
  # Don't bother to build everything here, just the tests we want to run
  scons-stage "arm" "${qemuflags} nacl_pic=1 pnacl_generate_pexe=0" \
    "small_tests medium_tests large_tests"

  # non-pexe-mode tests
  scons-stage "arm" "${qemuflags} pnacl_generate_pexe=0" "nonpexe_tests"

  build-sbtc-prerequisites "arm"

  scons-stage "arm" \
    "${qemuflags} use_sandboxed_translator=1 translate_in_build_step=0" \
    "toolchain_tests"

  browser-tests "arm" "${scons_mode},nacl_irt_test"
}

mode-buildbot-arm-hw() {
  FAIL_FAST=false
  local mode=$1
  local hwflags="-j2 -k naclsdk_validate=0 built_elsewhere=1"

  scons-stage "arm" "${mode} ${hwflags}" "small_tests medium_tests large_tests"
  scons-stage "arm" "${mode} ${hwflags} nacl_pic=1 pnacl_generate_pexe=0" \
    "small_tests medium_tests large_tests"
  scons-stage "arm" "${mode} ${hwflags} pnacl_generate_pexe=0" "nonpexe_tests"
  scons-stage "arm" \
    "${mode} ${hwflags} use_sandboxed_translator=1 translate_in_build_step=0" \
    "toolchain_tests"
  browser-tests "arm" "${mode},nacl_irt_test ${hwflags}"
}

mode-trybot-qemu() {
  # Build and actually run the arm tests under qemu, except
  # sandboxed translation. Hopefully that's a good tradeoff between
  # flakiness and cycle time.
  FAIL_FAST=false
  local qemuflags="--mode=opt-host,nacl -j4 -k"
  clobber
  gyp-arm-build Release

  scons-stage "arm" "${qemuflags}" ""
  scons-stage "arm" "${qemuflags} -j1" "small_tests medium_tests large_tests"

  scons-stage "arm" "${qemuflags} nacl_pic=1 pnacl_generate_pexe=0" ""
  scons-stage "arm" "${qemuflags} -j1 nacl_pic=1 pnacl_generate_pexe=0" \
    "small_tests medium_tests large_tests"

  # non-pexe tests
  scons-stage "arm" "${qemuflags} pnacl_generate_pexe=0" "nonpexe_tests"
}

mode-buildbot-arm-dbg() {
  mode-buildbot-arm "--mode=dbg-host,nacl" "Debug"
  archive-for-hw-bots $(NAME_ARM_UPLOAD) regular
}

mode-buildbot-arm-opt() {
  mode-buildbot-arm "--mode=opt-host,nacl" "Release"
  archive-for-hw-bots $(NAME_ARM_UPLOAD) regular
}

mode-buildbot-arm-try() {
  mode-buildbot-arm "--mode=opt-host,nacl" "Release"
  archive-for-hw-bots $(NAME_ARM_TRY_UPLOAD) try
}

# NOTE: the hw bots are too slow to build stuff on so we just
#       use pre-built executables
mode-buildbot-arm-hw-dbg() {
  unarchive-for-hw-bots $(NAME_ARM_DOWNLOAD)  regular
  mode-buildbot-arm-hw "--mode=dbg-host,nacl"
}

mode-buildbot-arm-hw-opt() {
  unarchive-for-hw-bots $(NAME_ARM_DOWNLOAD)  regular
  mode-buildbot-arm-hw "--mode=opt-host,nacl"
}

mode-buildbot-arm-hw-try() {
  unarchive-for-hw-bots $(NAME_ARM_TRY_DOWNLOAD)  try
  mode-buildbot-arm-hw "--mode=opt-host,nacl"
}

readonly TC_TESTS="smoke_tests"

# These are also suitable for local TC sanity testing
tc-tests-large() {
  # newlib
  scons-stage "x86-32" "--mode=opt-host,nacl -j8 -k" "${TC_TESTS}"
  scons-stage "x86-64" "--mode=opt-host,nacl -j8 -k" "${TC_TESTS}"
  scons-stage "arm"    "--mode=opt-host,nacl -j8 -k" "${TC_TESTS}"

  # glibc
  scons-stage "x86-32" \
              "--mode=opt-host,nacl -j8 -k --nacl_glibc pnacl_generate_pexe=0" \
              "${TC_TESTS}"
  scons-stage "x86-64" \
              "--mode=opt-host,nacl -j8 -k --nacl_glibc pnacl_generate_pexe=0" \
              "${TC_TESTS}"

  # we run the browser tests last since they tend to be flaky
  # and will terminate the testing unless  FAIL_FAST=false

  # newlib browser
  browser-tests "x86-32" "--mode=opt-host,nacl,nacl_irt_test -j8 -k"
  browser-tests "x86-64" "--mode=opt-host,nacl,nacl_irt_test -j8 -k"
  browser-tests "arm"    "--mode=opt-host,nacl,nacl_irt_test -j8 -k"

  # glibc browser
  browser-tests "x86-32" \
                "--mode=opt-host,nacl,nacl_irt_test -j8 -k --nacl_glibc"
  browser-tests "x86-64" \
                "--mode=opt-host,nacl,nacl_irt_test -j8 -k --nacl_glibc"
}

tc-tests-small() {
  scons-stage "$1" "--mode=opt-host,nacl -j8 -k" "${TC_TESTS}"
  browser-tests "$1" "--mode=opt-host,nacl,nacl_irt_test -j8 -k"
}

mode-buildbot-tc-x8664-linux() {
  local is_try=$1
  FAIL_FAST=false
  TOOLCHAIN_LABEL=pnacl_linux_x86_64
  tc-build-all ${TOOLCHAIN_LABEL} ${is_try} true
  tc-tests-large
}

mode-buildbot-tc-x8632-linux() {
  local is_try=$1
  FAIL_FAST=false
  TOOLCHAIN_LABEL=pnacl_linux_x86_32
  tc-build-all ${TOOLCHAIN_LABEL} ${is_try} false
  tc-tests-small "x86-32"
}

mode-buildbot-tc-x8632-mac() {
  local is_try=$1
  FAIL_FAST=false
  TOOLCHAIN_LABEL=pnacl_mac_x86_32
  # To avoid timing out, since this bot is slow.
  export PNACL_VERBOSE=true
  # We can't test ARM because we do not have QEMU for Mac.
  # We can't test X86-64 because NaCl X86-64 Mac support is not in good shape.
  tc-build-all ${TOOLCHAIN_LABEL} ${is_try} false
  tc-tests-small "x86-32"
}

mode-buildbot-tc-x8664-win() {
  local is_try=$1
  FAIL_FAST=false
  TOOLCHAIN_LABEL=pnacl_win_x86_64
  tc-build-all ${TOOLCHAIN_LABEL} ${is_try} false

  # On windows-chrome the plugin is always 32bit even though the nexe
  # might be 64bit
  echo @@@BUILD_STEP plugin compile 32@@@
  ./scons --verbose -k -j8 --mode=opt-host,nacl platform=x86-32 plugin

  # We can't test ARM because we do not have QEMU for Win.
  tc-tests-small "x86-64"
}



mode-test-all() {
  test-all-newlib "$@"
  test-all-glibc "$@"
}

# NOTE: clobber and toolchain setup to be done manually, since this is for
# testing a locally built toolchain.
# This runs tests concurrently, so may be more difficult to parse logs.
test-all-newlib() {
  local concur=$1

  # turn verbose mode off
  set +o xtrace

  # At least clobber scons-out before building and running the tests though.
  echo "@@@BUILD_STEP clobber@@@"
  rm -rf scons-out

  # First build everything.
  echo "@@@BUILD_STEP scons build @@@"
  scons-stage "arm" "--mode=opt-host,nacl -j${concur}" ""
  scons-stage "x86-32" "--mode=opt-host,nacl -j${concur}" ""
  scons-stage "x86-64" "--mode=opt-host,nacl -j${concur}" ""
  # Then test everything.
  echo "@@@BUILD_STEP scons smoke_tests @@@"
  scons-stage "arm" "--mode=opt-host,nacl -j${concur}" "smoke_tests"
  scons-stage "x86-32" "--mode=opt-host,nacl -j${concur}" "smoke_tests"
  scons-stage "x86-64" "--mode=opt-host,nacl -j${concur}" "smoke_tests"
  # browser tests.
  browser-tests "arm" "--verbose --mode=opt-host,nacl,nacl_irt_test -j${concur}"
  browser-tests "x86-32" \
    "--verbose --mode=opt-host,nacl,nacl_irt_test -j${concur}"
  browser-tests "x86-64" \
    "--verbose --mode=opt-host,nacl,nacl_irt_test -j${concur}"
}

test-all-glibc() {
  echo "TODO(pdox): Add GlibC tests"
}

######################################################################
# On Windows, this script is invoked from a batch file.
# The inherited PWD environmental variable is a Windows-style path.
# This can cause problems with pwd and bash. This line fixes it.
cd -P .

# Script assumed to be run in native_client/
if [[ $(pwd) != */native_client ]]; then
  echo "ERROR: must be run in native_client!"
  exit 1
fi


if [[ $# -eq 0 ]] ; then
  echo "you must specify a mode on the commandline:"
  exit 1
fi

if [ "$(type -t $1)" != "function" ]; then
  Usage
  echo "ERROR: unknown mode '$1'." >&2
  exit 1
fi

"$@"

if [[ ${RETCODE} != 0 ]]; then
  echo "@@@BUILD_STEP summary@@@"
  echo There were failed stages.
  exit ${RETCODE}
fi
