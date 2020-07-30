# About

C++ lib

## Installation

```bash
export CXX=clang++-6.0
export CC=clang-6.0

# NOTE: change `build_type=Debug` to `build_type=Release` in production
# NOTE: use --build=missing if you got error `ERROR: Missing prebuilt package`
CONAN_REVISIONS_ENABLED=1 \
CONAN_VERBOSE_TRACEBACK=1 \
CONAN_PRINT_RUN_COMMANDS=1 \
CONAN_LOGGING_LEVEL=10 \
GIT_SSL_NO_VERIFY=true \
    cmake -E time \
      conan create . conan/stable \
      -s build_type=Debug \
      -s llvm_tools:build_type=Release \
      --profile clang \
          -o corrade:shared=False
```

## HOW TO BUILD WITH SANITIZERS ENABLED

Use `enable_asan` or `enable_ubsan`, etc.

```bash
export CC=$(find ~/.conan/data/llvm_tools/master/conan/stable/package/ -path "*bin/clang" | head -n 1)

export CXX=$(find ~/.conan/data/llvm_tools/master/conan/stable/package/ -path "*bin/clang++" | head -n 1)

export CFLAGS="-fsanitize=thread -fuse-ld=lld -stdlib=libc++ -lc++ -lc++abi -lunwind"

export CXXFLAGS="-fsanitize=thread -fuse-ld=lld -stdlib=libc++ -lc++ -lc++abi -lunwind"

export LDFLAGS="-stdlib=libc++ -lc++ -lc++abi -lunwind"

# must exist
file $(dirname $CXX)/../lib/clang/10.0.1/lib/linux/libclang_rt.tsan_cxx-x86_64.a

# NOTE: NO `--profile` argument cause we use `CXX` env. var
# NOTE: change `build_type=Debug` to `build_type=Release` in production
CONAN_REVISIONS_ENABLED=1 \
    CONAN_VERBOSE_TRACEBACK=1 \
    CONAN_PRINT_RUN_COMMANDS=1 \
    CONAN_LOGGING_LEVEL=10 \
    GIT_SSL_NO_VERIFY=true \
    conan create . \
        conan/stable \
        -s build_type=Debug \
        -s llvm_tools:build_type=Release \
        -o llvm_tools:enable_tsan=True \
        -o llvm_tools:include_what_you_use=False \
        -s llvm_tools:compiler=clang \
        -s llvm_tools:compiler.version=6.0 \
        -s llvm_tools:compiler.libcxx=libstdc++11 \
        -o corrade:enable_tsan=True \
        -e corrade:enable_llvm_tools=True \
        -e corrade:compile_with_llvm_tools=True \
        -s compiler=clang \
        -s compiler.version=10 \
        -s compiler.libcxx=libc++ \
        -o openssl:shared=True

# reset changed LDFLAGS
unset LDFLAGS

# reset changed CFLAGS
unset CFLAGS

# reset changed CXXFLAGS
unset CXXFLAGS

NOTE: during compilation conan will print `llvm_tools_ROOT =`. Make sure its path matches `$CC` and `$CXX`.
```
