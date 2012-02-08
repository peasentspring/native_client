#!/usr/bin/python
# Copyright (c) 2011 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# IMPORTANT NOTE: If you make local mods to this file, you must run:
#   %  tools/llvm/utman.sh driver
# in order for them to take effect in the scons build.  This command
# updates the copy in the toolchain/ tree.
#

import shutil
from driver_tools import *
from driver_env import env
from driver_log import Log

def main(argv):
  env.set('ARGV', *argv)
  return RunWithLog('${AR} ${ARGV}', errexit = False)

if __name__ == "__main__":
  DriverMain(main)
