#!/usr/bin/python
# Copyright (c) 2012 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import subprocess
import sys

python = sys.executable
bash = '/bin/bash'
echo = 'echo'


BOT_ASSIGNMENT = {
    ######################################################################
    # Buildbots.
    ######################################################################
    'xp-newlib-opt':
        python + ' buildbot\\buildbot_standard.py opt 32 newlib --no-gyp',
    'xp-glibc-opt':
        python + ' buildbot\\buildbot_standard.py opt 32 glibc --no-gyp',

    'xp-bare-newlib-opt':
        python + ' buildbot\\buildbot_standard.py opt 32 newlib --no-gyp',
    'xp-bare-glibc-opt':
        python + ' buildbot\\buildbot_standard.py opt 32 glibc --no-gyp',

    'precise-64-validator-opt':
        python + ' buildbot/buildbot_standard.py opt 64 glibc --validator',

    # Clang.
    'precise_64-newlib-dbg-clang':
        python + ' buildbot/buildbot_standard.py dbg 64 newlib --clang',
    'mac10.7-newlib-dbg-clang':
        python + ' buildbot/buildbot_standard.py dbg 32 newlib --clang',

    # ASan.
    'precise_64-newlib-dbg-asan':
        python + ' buildbot/buildbot_standard.py opt 64 newlib --asan',
    'mac10.7-newlib-dbg-asan':
        python + ' buildbot/buildbot_standard.py opt 32 newlib --asan',

    # PNaCl.
    'oneiric_32-newlib-arm_hw-pnacl-panda-dbg':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-hw-dbg',
    'oneiric_32-newlib-arm_hw-pnacl-panda-opt':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-hw-opt',
    'precise_64-newlib-arm_qemu-pnacl-dbg':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-dbg',
    'precise_64-newlib-arm_qemu-pnacl-opt':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-opt',
    'precise_64-newlib-x86_32-pnacl':
        python + ' buildbot/buildbot_pnacl.py opt 32 pnacl',
    'precise_64-newlib-x86_64-pnacl':
        python + ' buildbot/buildbot_pnacl.py opt 64 pnacl',
    'precise_64-newlib-mips-pnacl':
        echo + ' "TODO(mseaborn): add mips"',
    # PNaCl Spec
    'lucid_64-newlib-arm_qemu-pnacl-buildonly-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-arm-buildonly',
    'oneiric_32-newlib-arm_hw-pnacl-panda-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-arm-hw',
    'lucid_64-newlib-x86_32-pnacl-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-x8632',
    'lucid_64-newlib-x86_64-pnacl-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-x8664',
    'precise_64-newlib-arm_qemu-pnacl-buildonly-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-arm-buildonly',
    # NaCl Spec
    'lucid_64-newlib-x86_32-spec':
        bash + ' buildbot/buildbot_spec2k.sh nacl-x8632',
    'lucid_64-newlib-x86_64-spec':
        bash + ' buildbot/buildbot_spec2k.sh nacl-x8664',

    # Valgrind bots.
    'precise-64-newlib-dbg-valgrind':
        echo + ' "Valgrind bots are disabled: see '
            'https://code.google.com/p/nativeclient/issues/detail?id=3158"',
    'precise-64-glibc-dbg-valgrind':
        echo + ' "Valgrind bots are disabled: see '
            'https://code.google.com/p/nativeclient/issues/detail?id=3158"',
    # Coverage.
    'mac10.6-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 64 newlib --coverage --clang'),
    'precise-64-32-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 32 newlib --coverage'),
    'precise-64-64-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 64 newlib --coverage'),
    'xp-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 32 newlib --coverage'),

    ######################################################################
    # Trybots.
    ######################################################################
    'nacl-precise64_validator_opt':
        python + ' buildbot/buildbot_standard.py opt 64 glibc --validator',
    'nacl-precise64_newlib_dbg_valgrind':
        bash + ' buildbot/buildbot_valgrind.sh newlib',
    'nacl-precise64_glibc_dbg_valgrind':
        bash + ' buildbot/buildbot_valgrind.sh glibc',
    # Coverage trybots.
    'nacl-mac10.6-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 64 newlib --coverage --clang'),
    'nacl-precise-64-32-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 32 newlib --coverage'),
    'nacl-precise-64-64-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 64 newlib --coverage'),
    'nacl-win32-newlib-coverage':
         python + (' buildbot/buildbot_standard.py '
                   'coverage 32 newlib --coverage'),
    # Clang trybots.
    'nacl-precise_64-newlib-dbg-clang':
        python + ' buildbot/buildbot_standard.py dbg 64 newlib --clang',
    'nacl-mac10.6-newlib-dbg-clang':
        python + ' buildbot/buildbot_standard.py dbg 32 newlib --clang',
    # Pnacl main trybots
    'nacl-precise_64-newlib-arm_qemu-pnacl':
        bash + ' buildbot/buildbot_pnacl.sh mode-trybot-qemu',
    'nacl-precise_64-newlib-x86_32-pnacl':
         python + ' buildbot/buildbot_pnacl.py opt 32 pnacl',
    'nacl-precise_64-newlib-x86_64-pnacl':
         python + ' buildbot/buildbot_pnacl.py opt 64 pnacl',
    'nacl-precise_64-newlib-mips-pnacl':
        echo + ' "TODO(mseaborn): add mips"',
    'nacl-arm_opt_panda':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-try',
    'nacl-arm_hw_opt_panda':
        bash + ' buildbot/buildbot_pnacl.sh mode-buildbot-arm-hw-try',
    # Pnacl spec2k trybots
    'nacl-precise_64-newlib-x86_32-pnacl-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-trybot-x8632',
    'nacl-precise_64-newlib-x86_64-pnacl-spec':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-trybot-x8664',
    'nacl-arm_perf_panda':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-trybot-arm-buildonly',
    'nacl-arm_hw_perf_panda':
        bash + ' buildbot/buildbot_spec2k.sh pnacl-trybot-arm-hw',
    # Toolchain glibc.
    'precise64-glibc': bash + ' buildbot/buildbot_linux-glibc-makefile.sh',
    'mac-glibc': bash + ' buildbot/buildbot_mac-glibc-makefile.sh',
    'win7-glibc': 'buildbot\\buildbot_windows-glibc-makefile.bat',
    # Toolchain newlib x86.
    'win7-toolchain_x86': 'buildbot\\buildbot_toolchain_win.bat',
    'mac-toolchain_x86': bash + ' buildbot/buildbot_toolchain.sh mac',
    'precise64-toolchain_x86': bash + ' buildbot/buildbot_toolchain.sh linux',
    # Toolchain newlib arm.
    'win7-toolchain_arm':
        python + ' buildbot/buildbot_toolchain_build.py --buildbot',
    'mac-toolchain_arm':
        python + ' buildbot/buildbot_toolchain_build.py --buildbot',
    'precise64-toolchain_arm':
        python + ' buildbot/buildbot_toolchain_build.py --buildbot',

    # BIONIC toolchain builders.
    'precise64-toolchain_bionic':
        python + ' buildbot/buildbot_toolchain_build_bionic.py --buildbot',

    # Pnacl toolchain builders.
    'linux-armtools-x86_32':
        bash + ' buildbot/buildbot_toolchain_arm_trusted.sh',
    'linux-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    'linux-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    'precise-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    'precise-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    'mac-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    # TODO(robertm): Delete this once we are using win-pnacl-x86_64
    'win-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',
    # TODO(robertm): use this in favor or the misnamed win-pnacl-x86_32
    'win-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --buildbot',

    # Pnacl toolchain testers
    'linux-pnacl-x86_64-tests-x86_64':
        bash + ' buildbot/buildbot_pnacl_toolchain_tests.sh tc-test-bot x86-64',
    'linux-pnacl-x86_64-tests-x86_32':
        bash + ' buildbot/buildbot_pnacl_toolchain_tests.sh tc-test-bot x86-32',
    'linux-pnacl-x86_64-tests-arm':
        bash + ' buildbot/buildbot_pnacl_toolchain_tests.sh tc-test-bot arm',

    # MIPS toolchain buildbot.
    'linux-pnacl-x86_32-tests-mips':
        bash + ' buildbot/buildbot_toolchain_mips_trusted.sh',

    # Toolchain trybots.
    'nacl-toolchain-precise64-newlib':
        bash + ' buildbot/buildbot_toolchain.sh linux',
    'nacl-toolchain-mac-newlib': bash + ' buildbot/buildbot_toolchain.sh mac',
    'nacl-toolchain-win7-newlib': 'buildbot\\buildbot_toolchain_win.bat',
    'nacl-toolchain-precise64-newlib-arm':
        python + ' buildbot/buildbot_toolchain_build.py --trybot',
    'nacl-toolchain-mac-newlib-arm':
        python + ' buildbot/buildbot_toolchain_build.py --trybot',
    'nacl-toolchain-win7-newlib-arm':
        python + ' buildbot/buildbot_toolchain_build.py --trybot',
    'nacl-toolchain-precise64-glibc':
        bash + ' buildbot/buildbot_linux-glibc-makefile.sh',
    'nacl-toolchain-mac-glibc':
        bash + ' buildbot/buildbot_mac-glibc-makefile.sh',
    'nacl-toolchain-win7-glibc':
        'buildbot\\buildbot_windows-glibc-makefile.bat',

    # Pnacl toolchain trybots.
    'nacl-toolchain-linux-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',
    'nacl-toolchain-linux-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',
    'nacl-toolchain-linux-pnacl-mips': echo + ' "TODO(mseaborn)"',
    'nacl-toolchain-precise-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',
    'nacl-toolchain-precise-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',
    'nacl-toolchain-precise-pnacl-mips': echo + ' "TODO(mseaborn)"',
    'nacl-toolchain-mac-pnacl-x86_32':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',
    'nacl-toolchain-win7-pnacl-x86_64':
        python + ' buildbot/buildbot_pnacl_toolchain.py --trybot',

}

special_for_arm = [
    'win7_64',
    'win7-64',
    'lucid-64',
    'lucid64',
    'precise-64',
    'precise64'
]
for platform in [
    'vista', 'win7', 'win8', 'win',
    'mac10.6', 'mac10.7', 'mac10.8',
    'lucid', 'precise'] + special_for_arm:
  if platform in special_for_arm:
    arch_variants = ['arm']
  else:
    arch_variants = ['', '32', '64', 'arm']
  for arch in arch_variants:
    arch_flags = ''
    real_arch = arch
    arch_part = '-' + arch
    # Disable GYP build for win32 bots and arm cross-builders. In this case
    # "win" means Windows XP, not Vista, Windows 7, etc.
    #
    # Building via GYP always builds all toolchains by default, but the win32
    # XP pnacl builds are pathologically slow (e.g. ~38 seconds per compile on
    # the nacl-win32_glibc_opt trybot). There are other builders that test
    # Windows builds via gyp, so the reduced test coverage should be slight.
    if arch == 'arm' or (platform == 'win' and arch == '32'):
      arch_flags += ' --no-gyp'
    if arch == '':
      arch_part = ''
      real_arch = '32'
    if platform.startswith('mac'):
      arch_flags += ' --clang'
    # Test with Breakpad tools only on basic Linux builds.
    if sys.platform.startswith('linux'):
      arch_flags += ' --use-breakpad-tools'
    for mode in ['dbg', 'opt']:
      for libc in ['newlib', 'glibc']:
        # Buildbots.
        for bare in ['', '-bare']:
          name = platform + arch_part + bare + '-' + libc + '-' + mode
          assert name not in BOT_ASSIGNMENT, name
          BOT_ASSIGNMENT[name] = (
              python + ' buildbot/buildbot_standard.py ' +
              mode + ' ' + real_arch + ' ' + libc + arch_flags)
        # Trybots
        for arch_sep in ['', '-', '_']:
          name = 'nacl-' + platform + arch_sep + arch + '_' + libc + '_' + mode
          assert name not in BOT_ASSIGNMENT, name
          BOT_ASSIGNMENT[name] = (
              python + ' buildbot/buildbot_standard.py ' +
              mode + ' ' + real_arch + ' ' + libc + arch_flags)


def EscapeJson(data):
  return '"' + json.dumps(data).replace('"', r'\"') + '"'


def Main():
  builder = os.environ.get('BUILDBOT_BUILDERNAME')
  build_number = os.environ.get('BUILDBOT_BUILDNUMBER')
  slave_type = os.environ.get('BUILDBOT_SLAVE_TYPE')
  cmd = BOT_ASSIGNMENT.get(builder)
  if not cmd:
    sys.stderr.write('ERROR - unset/invalid builder name\n')
    sys.exit(1)

  env = os.environ.copy()

  # Use .boto file from home-dir instead of buildbot supplied one.
  if 'AWS_CREDENTIAL_FILE' in env:
    del env['AWS_CREDENTIAL_FILE']
  if 'BOTO_CONFIG' in env:
    del env['BOTO_CONFIG']

  env['GSUTIL'] = '/b/build/third_party/gsutil/gsutil'

  if sys.platform == 'win32':
    # If the temp directory is not on the same drive as the working directory,
    # there can be random failures when cleaning up temp directories, so use
    # a directory on the current drive. Use __file__ here instead of os.getcwd()
    # because toolchain_main picks its working directories relative to __file__
    filedrive, _ = os.path.splitdrive(__file__)
    tempdrive, _ = os.path.splitdrive(env['TEMP'])
    if tempdrive != filedrive:
      env['TEMP'] = filedrive + '\\temp'
      env['TMP'] = env['TEMP']

  # Run through runtest.py to get upload of perf data.
  build_properties = {
      'buildername': builder,
      'mastername': 'client.nacl',
      'buildnumber': str(build_number),
  }
  factory_properties = {
      'perf_id': builder,
      'show_perf_results': True,
      'step_name': 'naclperf',  # Seems unused, but is required.
      'test_name': 'naclperf',  # Really "Test Suite"
      'expectations': True,
      'perf_filename': ('native_client/tools/'
                        'nacl_perf_expectations/nacl_perf_expectations.json'),
  }
  # Locate the buildbot build directory by relative path, as it's absolute
  # location varies by platform and configuration.
  buildbot_build_dir = os.path.join(* [os.pardir] * 4)
  runtest = os.path.join(buildbot_build_dir, 'scripts', 'slave', 'runtest.py')
  # For builds with an actual build number, require that the script is present
  # (i.e. that we're run from an actual buildbot).
  if build_number is not None and not os.path.exists(runtest):
    raise Exception('runtest.py script not found at: %s\n' % runtest)
  cmd_exe = cmd.split(' ')[0]
  cmd_exe_ext = os.path.splitext(cmd_exe)[1]
  # Do not wrap these types of builds with runtest.py:
  # - tryjobs
  # - commands beginning with 'echo '
  # - batch files
  if not (slave_type == 'Trybot' or
          cmd_exe == echo or
          cmd_exe_ext == '.bat'):
    # Perf dashboards are now generated by output scraping that occurs in the
    # script runtest.py, which lives in the buildbot repository.
    # Non-trybot builds should be run through runtest, allowing it to upload
    # perf data if relevant.
    cmd = ' '.join([
        python, runtest,
        '--build-dir=src/out',
        '--results-url=https://chromeperf.appspot.com',
        '--annotate=graphing',
        '--no-xvfb',  # We provide our own xvfb invocation.
        '--factory-properties', EscapeJson(factory_properties),
        '--build-properties', EscapeJson(build_properties),
        cmd,
    ])

  print "%s runs: %s\n" % (builder, cmd)
  retcode = subprocess.call(cmd, env=env, shell=True)
  sys.exit(retcode)


if __name__ == '__main__':
  Main()
