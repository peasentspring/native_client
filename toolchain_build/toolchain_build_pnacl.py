#!/usr/bin/python
# Copyright (c) 2013 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipes for PNaCl toolchain packages.

   Recipes consist of specially-structured dictionaries, with keys for package
   name, type, commands to execute, etc. The structure is documented in the
   PackageBuilder docstring in toolchain_main.py.

   The real entry plumbing and CLI flags are also in toolchain_main.py.
"""

import fnmatch
import logging
import os
import shutil
import sys
import zipfile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import pynacl.gsd_storage
import pynacl.platform
import pynacl.repo_tools

import command
import pnacl_commands
import pnacl_targetlibs
import toolchain_main

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NACL_DIR = os.path.dirname(SCRIPT_DIR)
# Use the argparse from third_party to ensure it's the same on all platorms
python_lib_dir = os.path.join(os.path.dirname(NACL_DIR), 'third_party',
                              'python_libs', 'argparse')
sys.path.insert(0, python_lib_dir)
import argparse

PNACL_DRIVER_DIR = os.path.join(NACL_DIR, 'pnacl', 'driver')

# Scons tests can check this version number to decide whether to enable tests
# for toolchain bug fixes or new features.  This allows tests to be enabled on
# the toolchain buildbots/trybots before the new toolchain version is pinned
# (i.e. before the tests would pass on the main NaCl buildbots/trybots).
# If you are adding a test that depends on a toolchain change, you can
# increment this version number manually.
FEATURE_VERSION = 8

# For backward compatibility, these key names match the directory names
# previously used with gclient
GIT_REPOS = {
    'binutils': 'nacl-binutils.git',
    'clang': 'pnacl-clang.git',
    'llvm': 'pnacl-llvm.git',
    'gcc': 'pnacl-gcc.git',
    'libcxx': 'pnacl-libcxx.git',
    'libcxxabi': 'pnacl-libcxxabi.git',
    'nacl-newlib': 'nacl-newlib.git',
    'llvm-test-suite': 'pnacl-llvm-testsuite.git',
    'compiler-rt': 'pnacl-compiler-rt.git',
    'subzero': 'pnacl-subzero.git',
    }

GIT_BASE_URL = 'https://chromium.googlesource.com/native_client/'
GIT_PUSH_URL = 'ssh://gerrit.chromium.org/native_client/'
GIT_DEPS_FILE = os.path.join(NACL_DIR, 'pnacl', 'COMPONENT_REVISIONS')

ALT_GIT_BASE_URL = 'https://chromium.googlesource.com/a/native_client/'

KNOWN_MIRRORS = [('http://git.chromium.org/native_client/', GIT_BASE_URL)]
PUSH_MIRRORS = [('http://git.chromium.org/native_client/', GIT_PUSH_URL),
                (ALT_GIT_BASE_URL, GIT_PUSH_URL),
                (GIT_BASE_URL, GIT_PUSH_URL)]

# TODO(dschuff): Some of this mingw logic duplicates stuff in command.py
BUILD_CROSS_MINGW = False
# Path to the mingw cross-compiler libs on Ubuntu
CROSS_MINGW_LIBPATH = '/usr/lib/gcc/i686-w64-mingw32/4.6'
# Path and version of the native mingw compiler to be installed on Windows hosts
MINGW_PATH = os.path.join(NACL_DIR, 'mingw32')
MINGW_VERSION = 'i686-w64-mingw32-4.8.1'

CHROME_CLANG = os.path.join(os.path.dirname(NACL_DIR), 'third_party',
                            'llvm-build', 'Release+Asserts', 'bin', 'clang')
CHROME_CLANGXX = CHROME_CLANG + '++'

ALL_ARCHES = ('x86-32', 'x86-64', 'arm', 'mips32',
              'x86-32-nonsfi', 'arm-nonsfi')
# MIPS32 doesn't use biased bitcode, and nonsfi targets don't need it.
BITCODE_BIASES = tuple(bias for bias in ('le32', 'x86-32', 'x86-64', 'arm'))

MAKE_DESTDIR_CMD = ['make', 'DESTDIR=%(abs_output)s']

def TripleIsWindows(t):
  return fnmatch.fnmatch(t, '*-mingw32*')

def TripleIsCygWin(t):
  return fnmatch.fnmatch(t, '*-cygwin*')

def TripleIsLinux(t):
  return fnmatch.fnmatch(t, '*-linux*')

def TripleIsMac(t):
  return fnmatch.fnmatch(t, '*-darwin*')

def TripleIsX8664(t):
  return fnmatch.fnmatch(t, 'x86_64*')


# Return a tuple (C compiler, C++ compiler) of the compilers to compile the host
# toolchains
def CompilersForHost(host):
  compiler = {
      # For now we only do native builds for linux and mac
      # treat 32-bit linux like a native build
      'i686-linux': (CHROME_CLANG, CHROME_CLANGXX),
      'x86_64-linux': (CHROME_CLANG, CHROME_CLANGXX),
      'x86_64-apple-darwin': (CHROME_CLANG, CHROME_CLANGXX),
      # Windows build should work for native and cross
      'i686-w64-mingw32': ('i686-w64-mingw32-gcc', 'i686-w64-mingw32-g++'),
      # TODO: add arm-hosted support
      'i686-pc-cygwin': ('gcc', 'g++'),
  }
  return compiler[host]


def GSDJoin(*args):
  return '_'.join([pynacl.gsd_storage.LegalizeName(arg) for arg in args])


def ConfigureHostArchFlags(host, extra_cflags=[]):
  """ Return flags passed to LLVM and binutils configure for compilers and
  compile flags. """
  configure_args = []
  extra_cc_args = []

  native = pynacl.platform.PlatformTriple()
  is_cross = host != native
  if is_cross:
    if (pynacl.platform.IsLinux64() and
        fnmatch.fnmatch(host, '*-linux*')):
      # 64 bit linux can build 32 bit linux binaries while still being a native
      # build for our purposes. But it's not what config.guess will yield, so
      # use --build to force it and make sure things build correctly.
      configure_args.append('--build=' + host)
    else:
      configure_args.append('--host=' + host)
  if TripleIsLinux(host) and not TripleIsX8664(host):
    # Chrome clang defaults to 64-bit builds, even when run on 32-bit Linux.
    extra_cc_args = ['-m32']

  extra_cxx_args = list(extra_cc_args)

  cc, cxx = CompilersForHost(host)

  configure_args.append('CC=' + ' '.join([cc] + extra_cc_args))
  configure_args.append('CXX=' + ' '.join([cxx] + extra_cxx_args))

  if TripleIsWindows(host):
    # The i18n support brings in runtime dependencies on MinGW DLLs
    # that we don't want to have to distribute alongside our binaries.
    # So just disable it, and compiler messages will always be in US English.
    configure_args.append('--disable-nls')
    configure_args.extend(['LDFLAGS=-L%(abs_libdl)s -ldl',
                           'CFLAGS=-isystem %(abs_libdl)s',
                           'CXXFLAGS=-isystem %(abs_libdl)s'])
    if is_cross:
      # LLVM's linux->mingw cross build needs this
      configure_args.append('CC_FOR_BUILD=gcc')
  else:
    configure_args.extend(
      ['CFLAGS=' + ' '.join(extra_cflags),
       'LDFLAGS=-L%(' + GSDJoin('abs_libcxx', host) + ')s/lib',
       'CXXFLAGS=-stdlib=libc++ -I%(' + GSDJoin('abs_libcxx', host) +
         ')s/include/c++/v1 ' + ' '.join(extra_cflags)])

  return configure_args


def LibCxxHostArchFlags(host):
  cc, cxx = CompilersForHost(host)
  cmake_flags = []
  cmake_flags.extend(['-DCMAKE_C_COMPILER='+cc, '-DCMAKE_CXX_COMPILER='+cxx])
  if TripleIsLinux(host) and not TripleIsX8664(host):
    # Chrome clang defaults to 64-bit builds, even when run on 32-bit Linux
    cmake_flags.extend(['-DCMAKE_C_FLAGS=-m32',
                        '-DCMAKE_CXX_FLAGS=-m32'])
  return cmake_flags

def CmakeHostArchFlags(host, options):
  """ Set flags passed to LLVM cmake for compilers and compile flags. """
  cmake_flags = []
  cc, cxx = CompilersForHost(host)

  cmake_flags.extend(['-DCMAKE_C_COMPILER='+cc, '-DCMAKE_CXX_COMPILER='+cxx])

  # There seems to be a bug in chrome clang where it exposes the msan interface
  # (even when compiling without msan) but then does not link with an
  # msan-enabled compiler_rt, leaving references to __msan_allocated_memory
  # undefined.
  cmake_flags.append('-DHAVE_SANITIZER_MSAN_INTERFACE_H=FALSE')

  if pynacl.platform.IsLinux64() and pynacl.platform.PlatformTriple() != host:
    # Currently the only supported "cross" build is 64-bit Linux to 32-bit
    # Linux. Enable it.  Also disable libxml and libtinfo because our Ubuntu
    # doesn't have 32-bit libxml or libtinfo build, and users may not have them
    # either.
    cmake_flags.extend(['-DLLVM_BUILD_32_BITS=ON',
                        '-DLLVM_ENABLE_LIBXML=OFF',
                        '-DLLVM_ENABLE_TERMINFO=OFF'])

  if options.sanitize:
    cmake_flags.extend(['-DCMAKE_%s_FLAGS=-fsanitize=%s' % (c, options.sanitize)
                        for c in ('C', 'CXX')])
    cmake_flags.append('-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=%s' %
                       options.sanitize)

  return cmake_flags


def LLVMConfigureAssertionsFlags(options):
  if options.enable_llvm_assertions:
    return []
  else:
    return ['--disable-debug', '--disable-assertions']


def MakeCommand(host):
  make_command = ['make']
  if not pynacl.platform.IsWindows() or pynacl.platform.IsCygWin():
    # The make that ships with msys sometimes hangs when run with -j.
    # The ming32-make that comes with the compiler itself reportedly doesn't
    # have this problem, but it has issues with pathnames with LLVM's build.
    make_command.append('-j%(cores)s')

  if TripleIsWindows(host):
    # There appears to be nothing we can pass at top-level configure time
    # that will prevent the configure scripts from finding MinGW's libiconv
    # and using it.  We have to force this variable into the environment
    # of the sub-configure runs, which are run via make.
    make_command.append('HAVE_LIBICONV=no')
  return make_command


def CopyWindowsHostLibs(host):
  if not TripleIsWindows(host) and not TripleIsCygWin(host):
    return []

  if TripleIsCygWin(host):
    lib_path = '/bin'
    libs = ('cyggcc_s-1.dll', 'cygiconv-2.dll', 'cygwin1.dll',
            'cygintl-8.dll', 'cygstdc++-6.dll', 'cygz.dll')
  elif pynacl.platform.IsWindows():
    lib_path = os.path.join(MINGW_PATH, 'bin')
    # The native minGW compiler uses winpthread, but the Ubuntu cross compiler
    # does not.
    libs = ('libgcc_s_sjlj-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll')
  else:
    lib_path = os.path.join(CROSS_MINGW_LIBPATH)
    libs = ('libgcc_s_sjlj-1.dll', 'libstdc++-6.dll')
  return [command.Copy(
                  os.path.join(lib_path, lib),
                  os.path.join('%(output)s', 'bin', lib))
               for lib in libs]

def GetGitSyncCmdsCallback(revisions):
  """Return a callback which returns the git sync commands for a component.

     This allows all the revision information to be processed here while giving
     other modules like pnacl_targetlibs.py the ability to define their own
     source targets with minimal boilerplate.
  """
  def GetGitSyncCmds(component):
    git_url = GIT_BASE_URL + GIT_REPOS[component]
    git_push_url = GIT_PUSH_URL + GIT_REPOS[component]

    # This replaces build.sh's newlib-nacl-headers-clean step by cleaning the
    # the newlib repo on checkout (while silently blowing away any local
    # changes). TODO(dschuff): find a better way to handle nacl newlib headers.
    is_newlib = component == 'nacl-newlib'
    return (command.SyncGitRepoCmds(git_url, '%(output)s', revisions[component],
                                    clean=is_newlib,
                                    git_cache='%(git_cache_dir)s',
                                    push_url=git_push_url,
                                    known_mirrors=KNOWN_MIRRORS,
                                    push_mirrors=PUSH_MIRRORS) +
            [command.Runnable(None,
                              pnacl_commands.CmdCheckoutGitBundleForTrybot,
                              component, '%(output)s')])

  return GetGitSyncCmds


def HostToolsSources(GetGitSyncCmds):
  sources = {
      'libcxx_src': {
          'type': 'source',
          'output_dirname': 'libcxx',
          'commands': GetGitSyncCmds('libcxx'),
      },
      'libcxxabi_src': {
          'type': 'source',
          'output_dirname': 'libcxxabi',
          'commands': GetGitSyncCmds('libcxxabi'),
      },
      'binutils_pnacl_src': {
          'type': 'source',
          'output_dirname': 'binutils',
          'commands': GetGitSyncCmds('binutils'),
      },
      # For some reason, the llvm build using --with-clang-srcdir chokes if the
      # clang source directory is named something other than 'clang', so don't
      # change output_dirname for clang.
      'clang_src': {
          'type': 'source',
          'output_dirname': 'clang',
          'commands': GetGitSyncCmds('clang'),
      },
      'llvm_src': {
          'type': 'source',
          'output_dirname': 'llvm',
          'commands': GetGitSyncCmds('llvm'),
      },
      'subzero_src': {
          'type': 'source',
          'output_dirname': 'subzero',
          'commands': GetGitSyncCmds('subzero'),
      },
  }
  return sources

def TestsuiteSources(GetGitSyncCmds):
  sources = {
      'llvm_testsuite_src': {
          'type': 'source',
          'output_dirname': 'llvm-test-suite',
          'commands': GetGitSyncCmds('llvm-test-suite'),
      },
  }
  return sources


def CopyHostLibcxxForLLVMBuild(host, dest):
  """Copy libc++ to the working directory for build tools."""
  if TripleIsLinux(host):
    libname = 'libc++.so.1'
  elif TripleIsMac(host):
    libname = 'libc++.1.dylib'
  else:
    return []
  return [command.Mkdir(dest, parents=True),
          command.Copy('%(' + GSDJoin('abs_libcxx', host) +')s/lib/' + libname,
                       os.path.join(dest, libname))]

def HostLibs(host):
  def H(component_name):
    # Return a package name for a component name with a host triple.
    return GSDJoin(component_name, host)
  libs = {}
  if TripleIsWindows(host):
    if pynacl.platform.IsWindows():
      ar = 'ar'
    else:
      ar = 'i686-w64-mingw32-ar'

    libs.update({
      'libdl': {
          'type': 'build',
          'inputs' : { 'src' : os.path.join(NACL_DIR, '..', 'third_party',
                                            'dlfcn-win32') },
          'commands': [
              command.CopyTree('%(src)s', 'src'),
              command.Command(['i686-w64-mingw32-gcc',
                               '-o', 'dlfcn.o', '-c',
                               os.path.join('src', 'dlfcn.c'),
                               '-Wall', '-O3', '-fomit-frame-pointer']),
              command.Command([ar, 'cru',
                               'libdl.a', 'dlfcn.o']),
              command.Copy('libdl.a',
                           os.path.join('%(output)s', 'libdl.a')),
              command.Copy(os.path.join('src', 'dlfcn.h'),
                           os.path.join('%(output)s', 'dlfcn.h')),
          ],
      },
    })
  else:
    libs.update({
        H('libcxx'): {
            'dependencies': ['libcxx_src', 'libcxxabi_src'],
            'type': 'build',
            'commands': [
                command.SkipForIncrementalCommand([
                    'cmake', '-G', 'Unix Makefiles'] +
                     LibCxxHostArchFlags(host) +
                     ['-DLIBCXX_CXX_ABI=libcxxabi',
                      '-DLIBCXX_LIBCXXABI_INCLUDE_PATHS=' + command.path.join(
                          '%(abs_libcxxabi_src)s', 'include'),
                      '-DLIBCXX_ENABLE_SHARED=ON',
                      '-DCMAKE_INSTALL_PREFIX=',
                      '-DCMAKE_INSTALL_NAME_DIR=@executable_path/../lib',
                      '%(libcxx_src)s']),
                command.Command(MakeCommand(host) + ['VERBOSE=1']),
                command.Command(MAKE_DESTDIR_CMD + ['VERBOSE=1', 'install']),
            ],
        },
    })
  return libs


def HostTools(host, options):
  def H(component_name):
    # Return a package name for a component name with a host triple.
    return GSDJoin(component_name, host)
  # Return the file name with the appropriate suffix for an executable file.
  def Exe(file):
    if TripleIsWindows(host):
      return file + '.exe'
    else:
      return file
  # Binutils still has some warnings when building with clang
  warning_flags = ['-Wno-extended-offsetof', '-Wno-absolute-value',
                   '-Wno-unused-function', '-Wno-unused-const-variable',
                   '-Wno-unneeded-internal-declaration',
                   '-Wno-unused-private-field', '-Wno-format-security']
  tools = {
      H('binutils_pnacl'): {
          'dependencies': ['binutils_pnacl_src'],
          'type': 'build',
          'commands': [
              command.SkipForIncrementalCommand([
                  'sh',
                  '%(binutils_pnacl_src)s/configure'] +
                  ConfigureHostArchFlags(host, warning_flags) +
                  ['--prefix=',
                  '--disable-silent-rules',
                  '--target=arm-pc-nacl',
                  '--program-prefix=le32-nacl-',
                  '--enable-targets=arm-pc-nacl,i686-pc-nacl,x86_64-pc-nacl,' +
                  'mipsel-pc-nacl',
                  '--enable-deterministic-archives',
                  '--enable-shared=no',
                  '--enable-gold=default',
                  '--enable-ld=no',
                  '--enable-plugins',
                  '--without-gas',
                  '--without-zlib',
                  '--with-sysroot=/arm-pc-nacl']),
              command.Command(MakeCommand(host)),
              command.Command(MAKE_DESTDIR_CMD + ['install-strip'])] +
              [command.RemoveDirectory(os.path.join('%(output)s', dir))
               for dir in ('arm-pc-nacl', 'lib', 'lib32')]
      },
      H('driver'): {
        'type': 'build',
        'output_subdir': 'bin',
        'inputs': { 'src': PNACL_DRIVER_DIR },
        'commands': [
            command.Runnable(
                None,
                pnacl_commands.InstallDriverScripts,
                '%(src)s', '%(output)s',
                host_windows=TripleIsWindows(host) or TripleIsCygWin(host),
                host_64bit=TripleIsX8664(host))
        ],
      },
  }

  llvm_cmake = {
      H('llvm'): {
          'dependencies': ['clang_src', 'llvm_src', 'binutils_pnacl_src'],
          'type': 'build',
          'commands': [
              command.SkipForIncrementalCommand([
                  'cmake', '-G', 'Ninja'] +
                  CmakeHostArchFlags(host, options) +
                  ['-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                  '-DCMAKE_INSTALL_PREFIX=%(output)s',
                  '-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib',
                  '-DLLVM_ENABLE_LIBCXX=ON',
                  '-DBUILD_SHARED_LIBS=ON',
                  '-DLLVM_TARGETS_TO_BUILD=X86;ARM;Mips',
                  '-DLLVM_ENABLE_ASSERTIONS=ON',
                  '-DLLVM_ENABLE_ZLIB=OFF',
                  '-DLLVM_BUILD_TESTS=ON',
                  '-DLLVM_APPEND_VC_REV=ON',
                  '-DLLVM_BINUTILS_INCDIR=%(abs_binutils_pnacl_src)s/include',
                  '-DLLVM_EXTERNAL_CLANG_SOURCE_DIR=%(clang_src)s',
                  '%(llvm_src)s']),
              command.Command(['ninja', '-v']),
              command.Command(['ninja', 'install']),
        ],
      },
  }
  llvm_autoconf = {
      H('llvm'): {
          'dependencies': ['clang_src', 'llvm_src', 'binutils_pnacl_src',
                           'subzero_src'],
          'type': 'build',
          'commands': [
              command.SkipForIncrementalCommand([
                  'sh',
                  '%(llvm_src)s/configure'] +
                  ConfigureHostArchFlags(host) +
                  LLVMConfigureAssertionsFlags(options) +
                  ['--prefix=/',
                   '--enable-shared',
                   '--disable-zlib',
                   '--disable-terminfo',
                   '--disable-jit',
                   '--disable-bindings', # ocaml is currently the only binding.
                   '--with-binutils-include=%(abs_binutils_pnacl_src)s/include',
                   '--enable-targets=x86,arm,mips',
                   '--program-prefix=',
                   '--enable-optimized',
                   '--with-clang-srcdir=%(abs_clang_src)s'])] +
              CopyHostLibcxxForLLVMBuild(
                  host,
                  os.path.join('Release+Asserts', 'lib')) +
              [command.Command(MakeCommand(host) + [
                  'VERBOSE=1',
                  'NACL_SANDBOX=0',
                  'SUBZERO_SRC_ROOT=%(abs_subzero_src)s',
                  'all']),
              command.Command(MAKE_DESTDIR_CMD + ['install']),
              command.Remove(*[os.path.join('%(output)s', 'lib', f) for f in
                              '*.a', '*Hello.*', 'BugpointPasses.*']),
              command.Remove(*[os.path.join('%(output)s', 'bin', f) for f in
                               Exe('clang-format'), Exe('clang-check'),
                               Exe('c-index-test'), Exe('clang-tblgen'),
                               Exe('llvm-tblgen')])] +
              CopyWindowsHostLibs(host),
      },
  }
  if options.cmake:
    tools.update(llvm_cmake)
  else:
    tools.update(llvm_autoconf)
  if TripleIsWindows(host):
    tools[H('binutils_pnacl')]['dependencies'].append('libdl')
    tools[H('llvm')]['dependencies'].append('libdl')
  else:
    tools[H('binutils_pnacl')]['dependencies'].append(H('libcxx'))
    tools[H('llvm')]['dependencies'].append(H('libcxx'))
  return tools


def TargetLibCompiler(host):
  def H(component_name):
    return GSDJoin(component_name, host)
  host_lib = 'libdl' if TripleIsWindows(host) else H('libcxx')
  compiler = {
      # Because target_lib_compiler is not a memoized target, its name doesn't
      # need to have the host appended to it (it can be different on different
      # hosts), which means that target library build rules don't have to care
      # what host they run on; they can just depend on 'target_lib_compiler'
      'target_lib_compiler': {
          'type': 'work',
          'output_subdir': 'target_lib_compiler',
          'dependencies': [ H('binutils_pnacl'), H('llvm'), host_lib ],
          'inputs': { 'driver': PNACL_DRIVER_DIR },
          'commands': [
              command.CopyRecursive('%(' + t + ')s', '%(output)s')
              for t in [H('llvm'), H('binutils_pnacl'), host_lib]] + [
              command.Runnable(
                  None, pnacl_commands.InstallDriverScripts,
                  '%(driver)s', os.path.join('%(output)s', 'bin'),
                  host_windows=TripleIsWindows(host) or TripleIsCygWin(host),
                  host_64bit=TripleIsX8664(host))
          ]
      },
  }
  return compiler


def Metadata(revisions):
  data = {
      'metadata': {
          'type': 'build',
          'inputs': { 'readme': os.path.join(NACL_DIR, 'pnacl', 'README'),
                      'COMPONENT_REVISIONS': GIT_DEPS_FILE,
                      'driver': PNACL_DRIVER_DIR },
          'commands': [
              command.Copy('%(readme)s', os.path.join('%(output)s', 'README')),
              command.WriteData(str(FEATURE_VERSION),
                                os.path.join('%(output)s', 'FEATURE_VERSION')),
              command.Runnable(None, pnacl_commands.WriteREVFile,
                               os.path.join('%(output)s', 'REV'),
                               GIT_BASE_URL,
                               GIT_REPOS,
                               revisions),
          ],
      }
  }
  return data

def ParseComponentRevisionsFile(filename):
  ''' Parse a simple-format deps file, with fields of the form:
key=value
Keys should match the keys in GIT_REPOS above, which match the previous
directory names used by gclient (with the exception that '_' in the file is
replaced by '-' in the returned key name).
Values are the git hashes for each repo.
Empty lines or lines beginning with '#' are ignored.
This function returns a dictionary mapping the keys found in the file to their
values.
'''
  with open(filename) as f:
    deps = {}
    for line in f:
      stripped = line.strip()
      if stripped.startswith('#') or len(stripped) == 0:
        continue
      tokens = stripped.split('=')
      if len(tokens) != 2:
        raise Exception('Malformed component revisions file: ' + filename)
      deps[tokens[0].replace('_', '-')] = tokens[1]
  return deps


def GetSyncPNaClReposSource(revisions, GetGitSyncCmds):
  sources = {}
  for repo, revision in revisions.iteritems():
    sources['legacy_pnacl_%s_src' % repo] = {
        'type': 'source',
        'output_dirname': os.path.join(NACL_DIR, 'pnacl', 'git', repo),
        'commands': GetGitSyncCmds(repo),
    }
  return sources


def InstallMinGWHostCompiler():
  """Install the MinGW host compiler used to build the host tools on Windows.

  We could use an ordinary source rule for this, but that would require hashing
  hundreds of MB of toolchain files on every build. Instead, check for the
  presence of the specially-named file <version>.installed in the install
  directory. If it is absent, check for the presence of the zip file
  <version>.zip. If it is absent, attempt to download it from Google Storage.
  Then extract the zip file and create the install file.
  """
  if not os.path.isfile(os.path.join(MINGW_PATH, MINGW_VERSION + '.installed')):
    downloader = pynacl.gsd_storage.GSDStorage([], ['nativeclient-mingw'])
    zipfilename = MINGW_VERSION + '.zip'
    zipfilepath = os.path.join(NACL_DIR, zipfilename)
    # If the zip file is not present, try to download it from Google Storage.
    # If that fails, bail out.
    if (not os.path.isfile(zipfilepath) and
        not downloader.GetSecureFile(zipfilename, zipfilepath)):
        print >>sys.stderr, 'Failed to install MinGW tools:'
        print >>sys.stderr, 'could not find or download', zipfilename
        sys.exit(1)
    logging.info('Extracting %s' % zipfilename)
    zf = zipfile.ZipFile(zipfilepath)
    if os.path.exists(MINGW_PATH):
      shutil.rmtree(MINGW_PATH)
    zf.extractall(NACL_DIR)
    with open(os.path.join(MINGW_PATH, MINGW_VERSION + '.installed'), 'w') as _:
      pass
  os.environ['MINGW'] = MINGW_PATH


def GetUploadPackageTargets():
  """Package Targets describes all the archived package targets.

  This build can be built among many build bots, but eventually all things
  will be combined together. This package target dictionary describes the final
  output of the entire build.
  """
  package_targets = {}

  common_packages = ['metadata']

  # Target native libraries
  for arch in ALL_ARCHES:
    legal_arch = pynacl.gsd_storage.LegalizeName(arch)
    common_packages.append('libs_support_native_%s' % legal_arch)
    common_packages.append('compiler_rt_%s' % legal_arch)
    if not 'nonsfi' in arch:
      common_packages.append('libgcc_eh_%s' % legal_arch)

  # Target bitcode libraries
  for bias in BITCODE_BIASES:
    legal_bias = pynacl.gsd_storage.LegalizeName(bias)
    common_packages.append('newlib_%s' % legal_bias)
    common_packages.append('libcxx_%s' % legal_bias)
    common_packages.append('libstdcxx_%s' % legal_bias)
    common_packages.append('libs_support_bitcode_%s' % legal_bias)

  # Host components
  host_packages = {}
  for os_name, arch in (('win', 'x86-32'),
                        ('mac', 'x86-64'),
                        ('linux', 'x86-64')):
    triple = pynacl.platform.PlatformTriple(os_name, arch)
    legal_triple = pynacl.gsd_storage.LegalizeName(triple)
    host_packages.setdefault(os_name, []).extend(
        ['binutils_pnacl_%s' % legal_triple,
         'llvm_%s' % legal_triple,
         'driver_%s' % legal_triple])
    if os_name != 'win':
      host_packages[os_name].append('libcxx_%s' % legal_triple)

  # Unsandboxed target IRT libraries
  for os_name in ('linux', 'mac'):
    legal_triple = pynacl.gsd_storage.LegalizeName('x86-32-' + os_name)
    host_packages[os_name].append('unsandboxed_irt_%s' % legal_triple)

  for os_name, os_packages in host_packages.iteritems():
    package_target = '%s_x86' % pynacl.platform.GetOS(os_name)
    package_targets[package_target] = {}
    package_name = 'pnacl_newlib'
    combined_packages = os_packages + common_packages
    package_targets[package_target][package_name] = combined_packages

  return package_targets

if __name__ == '__main__':
  # This sets the logging for gclient-alike repo sync. It will be overridden
  # by the package builder based on the command-line flags.
  logging.getLogger().setLevel(logging.DEBUG)
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('--legacy-repo-sync', action='store_true',
                      dest='legacy_repo_sync', default=False,
                      help='Sync the git repo directories used by build.sh')
  parser.add_argument('--disable-llvm-assertions', action='store_false',
                      dest='enable_llvm_assertions', default=True)
  parser.add_argument('--cmake', action='store_true', default=False,
                      help="Use LLVM's cmake ninja build instead of autoconf")
  parser.add_argument('--sanitize', choices=['address', 'thread', 'memory',
                                             'undefined'],
                      help="Use a sanitizer with LLVM's clang cmake build")
  parser.add_argument('--testsuite-sync', action='store_true', default=False,
                      help=('Sync the sources for the LLVM testsuite. '
                      'Only useful if --sync/ is also enabled'))
  args, leftover_args = parser.parse_known_args()
  if '-h' in leftover_args or '--help' in leftover_args:
    print 'The following arguments are specific to toolchain_build_pnacl.py:'
    parser.print_help()
    print 'The rest of the arguments are generic, in toolchain_main.py'

  if args.sanitize and not args.cmake:
    print 'Use of sanitizers requires a cmake build'
    sys.exit(1)


  packages = {}
  upload_packages = {}

  rev = ParseComponentRevisionsFile(GIT_DEPS_FILE)
  if args.legacy_repo_sync:
    packages = GetSyncPNaClReposSource(rev, GetGitSyncCmdsCallback(rev))

    # Make sure sync is inside of the args to toolchain_main.
    if not set(['-y', '--sync', '--sync-only']).intersection(leftover_args):
      leftover_args.append('--sync-only')
  else:
    upload_packages = GetUploadPackageTargets()
    if pynacl.platform.IsWindows():
      InstallMinGWHostCompiler()

    packages.update(HostToolsSources(GetGitSyncCmdsCallback(rev)))
    if args.testsuite_sync:
      packages.update(TestsuiteSources(GetGitSyncCmdsCallback(rev)))

    hosts = [pynacl.platform.PlatformTriple()]
    if pynacl.platform.IsLinux() and BUILD_CROSS_MINGW:
      hosts.append(pynacl.platform.PlatformTriple('win', 'x86-32'))
    for host in hosts:
      packages.update(HostLibs(host))
      packages.update(HostTools(host, args))
    packages.update(TargetLibCompiler(pynacl.platform.PlatformTriple()))
    # Don't build the target libs on Windows because of pathname issues.
    # Only the linux64 bot is canonical (i.e. it will upload its packages).
    # The other bots will use a 'work' target instead of a 'build' target for
    # the target libs, so they will not be memoized, but can be used for tests.
    # TODO(dschuff): Even better would be if we could memoize non-canonical
    # build targets without doing things like mangling their names (and for e.g.
    # scons tests, skip running them if their dependencies haven't changed, like
    # build targets)
    is_canonical = pynacl.platform.IsLinux64()
    if pynacl.platform.IsLinux() or pynacl.platform.IsMac():
      packages.update(pnacl_targetlibs.TargetLibsSrc(
        GetGitSyncCmdsCallback(rev)))
      for bias in BITCODE_BIASES:
        packages.update(pnacl_targetlibs.BitcodeLibs(bias, is_canonical))
      for arch in ALL_ARCHES:
        packages.update(pnacl_targetlibs.NativeLibs(arch, is_canonical))
      packages.update(Metadata(rev))
    if pynacl.platform.IsLinux() or pynacl.platform.IsMac():
      packages.update(pnacl_targetlibs.UnsandboxedIRT(
          'x86-32-%s' % pynacl.platform.GetOS()))


  tb = toolchain_main.PackageBuilder(packages,
                                     upload_packages,
                                     leftover_args)
  tb.Main()
