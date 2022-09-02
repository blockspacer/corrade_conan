#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
from conans import ConanFile, CMake, tools
from conans.model.version import Version
from conans.errors import ConanInvalidConfiguration

from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment, RunEnvironment, python_requires
from conans.errors import ConanInvalidConfiguration, ConanException
from conans.tools import os_info
import os, re, stat, fnmatch, platform, glob, traceback, shutil
from functools import total_ordering

# if you using python less than 3 use from distutils import strtobool
from distutils.util import strtobool

# conan runs the methods in this order:
# config_options(),
# configure(),
# requirements(),
# package_id(),
# build_requirements(),
# build_id(),
# system_requirements(),
# source(),
# imports(),
# build(),
# package(),
# package_info()

conan_build_helper = python_requires("conan_build_helper/[~=0.0]@conan/stable")

def sort_libs(correct_order, libs, lib_suffix='', reverse_result=False):
    # Add suffix for correct string matching
    correct_order[:] = [s.__add__(lib_suffix) for s in correct_order]

    result = []
    for expectedLib in correct_order:
        for lib in libs:
            if expectedLib == lib:
                result.append(lib)

    if reverse_result:
        # Linking happens in reversed order
        result.reverse()

    return result

class CorradeConan(conan_build_helper.CMakePackage):
    name = "corrade"
    version = "v2020.06"
    repo_url = "https://github.com/mosra/corrade.git"
    description = "Corrade is a multiplatform utility library written \
                    in C++11/C++14. It's used as a base for the Magnum \
                    graphics engine, among other things."
    # topics can get used for searches, GitHub topics, Bintray tags etc. Add here keywords about the library
    topics = ("conan", "corrad", "magnum", "filesystem", "console", "environment", "os")
    url = "https://github.com/mosra/corrade"
    homepage = "https://magnum.graphics/corrade"
    author = "helmesjo <helmesjo@gmail.com>"
    license = "MIT"  # Indicates license type of the packaged library; please use SPDX Identifiers https://spdx.org/licenses/
    exports = ["COPYING"]
    exports_sources = ["CMakeLists.txt", "src/*", "package/**", "modules/*"]
    generators = "cmake"
    short_paths = True  # Some folders go out of the 260 chars path length scope (windows)

    # Options may need to change depending on the packaged library.
    settings = "os", "arch", "compiler", "build_type"
    options = {
      "enable_ubsan": [True, False],
      "enable_asan": [True, False],
      "enable_msan": [True, False],
      "enable_tsan": [True, False],
      "shared": [True, False],
      "fPIC": [True, False],
      "build_deprecated": [True, False],
      "with_interconnect": [True, False],
      "with_pluginmanager": [True, False],
      "with_rc": [True, False],
      "with_testsuite": [True, False],
      "with_utility": [True, False],
    }

    default_options = {
      "enable_ubsan": False,
      "enable_asan": False,
      "enable_msan": False,
      "enable_tsan": False,
      "shared": False,
      "fPIC": True,
      "build_deprecated": True,
      "with_interconnect": True,
      "with_pluginmanager": True,
      "with_rc": True,
      "with_testsuite": False,
      "with_utility": True,
    }

    # sets cmake variables required to use clang 10 from conan
    def _is_compile_with_llvm_tools_enabled(self):
      return self._environ_option("COMPILE_WITH_LLVM_TOOLS", default = 'false')

    # installs clang 10 from conan
    def _is_llvm_tools_enabled(self):
      return self._environ_option("ENABLE_LLVM_TOOLS", default = 'false')

    _build_subfolder = "build_subfolder"

    @property
    def _download_subfolder(self):
        return "downloads"

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        if self.settings.compiler == 'Visual Studio' and int(self.settings.compiler.version.value) < 14:
            raise ConanException("{} requires Visual Studio version 14 or greater".format(self.name))

        lower_build_type = str(self.settings.build_type).lower()

        if lower_build_type != "release" and not self._is_llvm_tools_enabled():
            self.output.warn('enable llvm_tools for Debug builds')

        if self._is_compile_with_llvm_tools_enabled() and not self._is_llvm_tools_enabled():
            raise ConanInvalidConfiguration("llvm_tools must be enabled")

        if self.options.enable_ubsan \
           or self.options.enable_asan \
           or self.options.enable_msan \
           or self.options.enable_tsan:
            if self.options.with_testsuite:
                raise ConanInvalidConfiguration("some sanitizers require disabled corrade-testsuite AND exceptions disabled (testsuite requires exceptions)")
            if not self._is_llvm_tools_enabled():
                raise ConanInvalidConfiguration("sanitizers require llvm_tools")

    def build_requirements(self):
        self.build_requires("cmake_platform_detection/master@conan/stable")
        self.build_requires("cmake_build_options/master@conan/stable")
        self.build_requires("cmake_helper_utils/master@conan/stable")

        if self.options.enable_tsan \
            or self.options.enable_msan \
            or self.options.enable_asan \
            or self.options.enable_ubsan:
          self.build_requires("cmake_sanitizers/master@conan/stable")

        # provides clang-tidy, clang-format, IWYU, scan-build, etc.
        if self._is_llvm_tools_enabled():
          self.build_requires("llvm_tools/master@conan/stable")

    # https://stackoverflow.com/a/13814557
    def copytree(self, src, dst, symlinks=False, ignore=None):
        if not os.path.exists(dst):
            os.makedirs(dst)
        ignore_list = ['.travis.yml', '.git', '.make', '.o', '.obj', '.marks', '.internal', 'CMakeFiles', 'CMakeCache']
        for item in os.listdir(src):
            if item not in ignore_list:
              s = os.path.join(src, item)
              d = os.path.join(dst, item)
              if os.path.isdir(s):
                  self.copytree(s, d, symlinks, ignore)
              else:
                  if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                      shutil.copy2(s, d)

    def source(self):
        if os.path.isdir(self._download_subfolder):
          shutil.rmtree(self._download_subfolder)
        self.run('git clone -b {} --progress --depth 100 --recursive --recurse-submodules {} {}'.format(self.version, self.repo_url, self._download_subfolder))
        self.output.info('downloaded source folder: %s' % str(os.listdir(self._download_subfolder)))
        shutil.rmtree(os.path.join(self._download_subfolder, "package"))
        os.remove(os.path.join(self._download_subfolder, "conanfile.py"))
        self.copytree( \
          os.path.join(self.source_folder, self._download_subfolder), \
          str(self.source_folder))
        # Wrap the original CMake file to call conan_basic_setup
        shutil.move("CMakeLists.txt", "CMakeListsOriginal.txt")
        shutil.move(os.path.join("package", "conan", "CMakeLists.txt"), "CMakeLists.txt")
        # Replace GrowableArray.h
        shutil.move(os.path.join("src", "Corrade", "Containers","GrowableArray.h"), os.path.join("src", "Corrade", "Containers","GrowableArrayOriginal.h"))
        shutil.move(os.path.join("package", "src", "Corrade", "Containers","GrowableArray.h"), os.path.join("src", "Corrade", "Containers","GrowableArray.h"))

    def _configure_cmake(self):
        cmake = CMake(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            cmake.definitions[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        # Corrade uses suffix on the resulting 'lib'-folder when running cmake.install()
        # Set it explicitly to empty, else Corrade might set it implicitly (eg. to "64")
        add_cmake_option("LIB_SUFFIX", "")

        add_cmake_option("BUILD_STATIC", not self.options.shared)

        if self.settings.compiler == 'Visual Studio':
            add_cmake_option("MSVC2015_COMPATIBILITY", int(self.settings.compiler.version.value) == 14)
            add_cmake_option("MSVC2017_COMPATIBILITY", int(self.settings.compiler.version.value) == 17)

        cmake.definitions["ENABLE_UBSAN"] = 'ON'
        if not self.options.enable_ubsan:
            cmake.definitions["ENABLE_UBSAN"] = 'OFF'

        cmake.definitions["ENABLE_ASAN"] = 'ON'
        if not self.options.enable_asan:
            cmake.definitions["ENABLE_ASAN"] = 'OFF'

        cmake.definitions["ENABLE_MSAN"] = 'ON'
        if not self.options.enable_msan:
            cmake.definitions["ENABLE_MSAN"] = 'OFF'

        cmake.definitions["ENABLE_TSAN"] = 'ON'
        if not self.options.enable_tsan:
            cmake.definitions["ENABLE_TSAN"] = 'OFF'

        self.add_cmake_option(cmake, "COMPILE_WITH_LLVM_TOOLS", self._is_compile_with_llvm_tools_enabled())

        cmake.configure(build_folder=self._build_subfolder)

        return cmake

    def build(self):
        with tools.vcvars(self.settings, only_diff=False): # https://github.com/conan-io/conan/issues/6577
            cmake = self._configure_cmake()
            cmake.build()

    def package(self):
        with tools.vcvars(self.settings, only_diff=False): # https://github.com/conan-io/conan/issues/6577
            self.copy("COPYING", dst="licenses", src=".")
            cmake = self._configure_cmake()
            cmake.install()

    def package_info(self):
        # See dependency order here: https://doc.magnum.graphics/magnum/custom-buildsystems.html
        allLibs = [
            #1
            "CorradeUtility",
            "CorradeContainers",
            #2
            "CorradeInterconnect",
            "CorradePluginManager",
            "CorradeTestSuite",
        ]

        # Sort all built libs according to above, and reverse result for correct link order
        suffix = '-d' if self.settings.build_type == "Debug" else ''
        builtLibs = tools.collect_libs(self)
        self.cpp_info.libs = sort_libs(correct_order=allLibs, libs=builtLibs, lib_suffix=suffix, reverse_result=True)
