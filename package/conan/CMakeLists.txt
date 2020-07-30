cmake_minimum_required(VERSION 3.4)
project(cmake_wrapper)

option(COMPILE_WITH_LLVM_TOOLS
  "Enable clang from llvm_tools (conan package)" OFF)

# see https://github.com/Ericsson/codechecker/blob/master/tools/report-converter/README.md#undefined-behaviour-sanitizer
# NOTE: Compile with -g and -fno-omit-frame-pointer
# to get proper debug information in your binary.
# NOTE: Run your program with environment variable UBSAN_OPTIONS=print_stacktrace=1.
# see https://github.com/google/sanitizers/wiki/SanitizerCommonFlags
option(ENABLE_UBSAN
  "Enable Undefined Behaviour Sanitizer" OFF)

# see https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
# see https://github.com/Ericsson/codechecker/blob/master/tools/report-converter/README.md#address-sanitizer
# NOTE: Compile with -g and -fno-omit-frame-pointer
# to get proper debug information in your binary.
# NOTE: use ASAN_OPTIONS=detect_leaks=1 LSAN_OPTIONS=suppressions=suppr.txt
# NOTE: You need the ASAN_OPTIONS=symbolize=1
# to turn on resolving addresses in object code
# to source code line numbers and filenames.
# This option is implicit for Clang but it won't do any harm.
# see https://github.com/google/sanitizers/wiki/SanitizerCommonFlags
option(ENABLE_ASAN
  "Enable Address Sanitizer" OFF)

# see https://github.com/Ericsson/codechecker/blob/master/tools/report-converter/README.md#memory-sanitizer
# NOTE: Compile with -g and -fno-omit-frame-pointer
# to get proper debug information in your binary.
option(ENABLE_MSAN
  "Enable Memory Sanitizer" OFF)

# see https://github.com/Ericsson/codechecker/blob/master/tools/report-converter/README.md#thread-sanitizer
# NOTE: Compile with -g
# to get proper debug information in your binary.
option(ENABLE_TSAN
  "Enable Thread Sanitizer" OFF)

if(COMPILE_WITH_LLVM_TOOLS)
  message(STATUS
    "Using COMPILE_WITH_LLVM_TOOLS")
  # do not check compile in conanbuildinfo
  # cause we will switch to other compiler after conan install
  set(CONAN_DISABLE_CHECK_COMPILER ON)
else(COMPILE_WITH_LLVM_TOOLS)
  message(STATUS
    "Disabled COMPILE_WITH_LLVM_TOOLS")
endif(COMPILE_WITH_LLVM_TOOLS)

include(conanbuildinfo.cmake)
conan_basic_setup()

if(ENABLE_MSAN OR ENABLE_TSAN OR ENABLE_ASAN OR ENABLE_UBSAN)
  find_package(cmake_sanitizers REQUIRED)
endif()

find_package(cmake_helper_utils REQUIRED)

# prefer ASCII for folder names
force_latin_paths() # from cmake_helper_utils (conan package)

# out dirs (CMAKE_*_OUTPUT_DIRECTORY) must be not empty
validate_out_dirs() # from cmake_helper_utils (conan package)

# In-source builds not allowed
validate_out_source_build(WARNING) # from cmake_helper_utils (conan package)

if(ENABLE_MSAN)
  add_msan_flags()
endif(ENABLE_MSAN)

if(ENABLE_TSAN)
  add_tsan_flags()
endif(ENABLE_TSAN)

if(ENABLE_ASAN)
  add_asan_flags()
endif(ENABLE_ASAN)

if(ENABLE_UBSAN)
  add_ubsan_flags()
endif(ENABLE_UBSAN)

if(COMPILE_WITH_LLVM_TOOLS)
  message(STATUS
    "Using COMPILE_WITH_LLVM_TOOLS")
  # force change CMAKE_*_COMPILER and CMAKE_LINKER to clang from conan
  compile_with_llvm_tools() # from cmake_helper_utils (conan package)
else(COMPILE_WITH_LLVM_TOOLS)
  message(STATUS
    "Disabled COMPILE_WITH_LLVM_TOOLS")
endif(COMPILE_WITH_LLVM_TOOLS)

include(${CMAKE_SOURCE_DIR}/CMakeListsOriginal.txt)

if(ENABLE_MSAN OR ENABLE_TSAN OR ENABLE_ASAN OR ENABLE_UBSAN)
  message(STATUS
    "Using sanitizers")

  if(cmake_build_type_tolower MATCHES "release" )
    message(WARNING
      "Disable sanitizers in Release builds")
  endif()

  # use llvm_tools from conan
  find_program_helper(llvm-symbolizer
    PATHS
      #${CONAN_BIN_DIRS}
      ${CONAN_BIN_DIRS_LLVM_TOOLS}
    NO_SYSTEM_ENVIRONMENT_PATH
    NO_CMAKE_SYSTEM_PATH
    ${ARGUMENTS_UNPARSED_ARGUMENTS}
    REQUIRED
    OUT_VAR LLVM_SYMBOLIZER_PROGRAM
    VERBOSE TRUE
  )
  check_sanitizer_options(
    ENABLE_TSAN ${ENABLE_TSAN}
    ENABLE_ASAN ${ENABLE_ASAN}
    ENABLE_MSAN ${ENABLE_MSAN}
    ENABLE_UBSAN ${ENABLE_UBSAN}
    LLVM_SYMBOLIZER_PROGRAM ${LLVM_SYMBOLIZER_PROGRAM}
  )
else()
  message(STATUS
    "Disabled sanitizers")
endif()

set(CORRAGE_SAN_TARGETS
  CorradePluginManager
  #CorradeContainers # INTERFACE
  CorradeInterconnect
  CorradeUtility
  #CorradeMain # INTERFACE
)

foreach(target IN LISTS CORRAGE_SAN_TARGETS)
  if(ENABLE_MSAN)
    message(STATUS "enabling MSAN on ${target}")
    add_msan_static_link(${target})
    add_msan_definitions(${target})
    add_msan_flags()
  else(ENABLE_MSAN)
    message(STATUS
      "Disabled ENABLE_MSAN")
  endif(ENABLE_MSAN)

  if(ENABLE_TSAN)
    message(STATUS "enabling TSAN on ${target}")
    add_tsan_static_link(${target})
    add_tsan_flags(${target})
    add_tsan_definitions(${target})
    add_tsan_flags()
  else(ENABLE_TSAN)
    message(STATUS
      "Disabled ENABLE_TSAN")
  endif(ENABLE_TSAN)

  if(ENABLE_ASAN)
    message(STATUS "enabling ASAN on ${target}")
    add_asan_static_link(${target})
    add_asan_definitions(${target})
    add_asan_flags()
  else(ENABLE_ASAN)
    message(STATUS
      "Disabled ENABLE_ASAN")
  endif(ENABLE_ASAN)

  if(ENABLE_UBSAN)
    message(STATUS "enabling UBSAN on ${target}")
    add_ubsan_static_link(${target})
    add_ubsan_definitions(${target})
    add_ubsan_flags()
  else(ENABLE_UBSAN)
    message(STATUS
      "Disabled ENABLE_UBSAN")
  endif(ENABLE_UBSAN)
endforeach()
