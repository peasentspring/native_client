#!/usr/bin/python
# Copyright (c) 2012 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# IMPORTANT NOTE: If you make local mods to this file, you must run:
#   %  pnacl/build.sh driver
# in order for them to take effect in the scons build.  This command
# updates the copy in the toolchain/ tree.
#

import driver_tools
from driver_env import env
from driver_log import Log, DriverOpen, DriverClose

EXTRA_ENV = {
  'INPUTS'          : '',
  'OUTPUT'          : '',
  'FLAGS'           : '',
}

DISPatterns = [
  ( ('-o','(.*)'),            "env.set('OUTPUT', pathtools.normalize($0))"),
  ( '(-.*)',                  "env.append('FLAGS', $0)"),
  ( '(.*)',                   "env.append('INPUTS', pathtools.normalize($0))"),
]

def main(argv):
  env.update(EXTRA_ENV)
  driver_tools.ParseArgs(argv, DISPatterns)

  inputs = env.get('INPUTS')
  output = env.getone('OUTPUT')

  if len(inputs) == 0:
    Log.Fatal("No input files given")

  if len(inputs) > 1 and output != '':
    Log.Fatal("Cannot have -o with multiple inputs")

  for infile in inputs:
    env.push()
    env.set('input', infile)
    env.set('output', output)

    # When we output to stdout, set redirect_stdout and set log_stdout
    # to False to bypass the driver's line-by-line handling of stdout
    # which is extremely slow when you have a lot of output

    if driver_tools.IsBitcode(infile):
      if output == '':
        # LLVM by default outputs to a file if -o is missing
        # Let's instead output to stdout
        env.set('output', '-')
        env.append('FLAGS', '-f')
      driver_tools.Run('${LLVM_DIS} ${FLAGS} ${input} -o ${output}')
    elif driver_tools.IsELF(infile):
      flags = env.get('FLAGS')
      if len(flags) == 0:
        env.append('FLAGS', '-d')
      if output == '':
        # objdump to stdout
        driver_tools.Run('${OBJDUMP} ${FLAGS} ${input}')
      else:
        # objdump always outputs to stdout, and doesn't recognize -o
        # Let's add this feature to be consistent.
        fp = driver_tools.DriverOpen(output, 'w')
        driver_tools.Run('${OBJDUMP} ${FLAGS} ${input}', redirect_stdout=fp)
        driver_tools.DriverClose(fp)
    else:
      Log.Fatal('Unknown file type')
    env.pop()
  # only reached in case of no errors
  return 0
