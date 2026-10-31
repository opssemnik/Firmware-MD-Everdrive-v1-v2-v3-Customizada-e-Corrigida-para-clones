#!/bin/bash
# Compiles the v3 search overlay inside WSL with the rootless m68k toolchain (~/m68k/root).
# usage: build.sh CLS_BANNER [en]   (run by build_custom_mdos.py: address of the mod's clsBanner;
#        "en" builds the English page, build/search_en.*)
set -euo pipefail
R=$HOME/m68k/root
export PATH=$R/usr/bin:$PATH
export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu
CC="m68k-linux-gnu-gcc-14 -B$R/usr/lib/gcc-cross/m68k-linux-gnu/14/ -B$R/usr/m68k-linux-gnu/bin/ -B$R/usr/libexec/gcc-cross/m68k-linux-gnu/14/"
P=m68k-linux-gnu-

cd "$(dirname "$0")"
mkdir -p build
CFLAGS="-m68000 -Os -ffreestanding -fno-pic -fno-pie -fomit-frame-pointer -fno-asynchronous-unwind-tables \
 -fno-tree-loop-distribute-patterns -fno-store-merging -fno-common -Wall -Wno-pointer-sign -Werror"

O=search; D=
if [ "${2:-}" = en ]; then O=search_en; D=-DLANG_EN; fi
$CC $CFLAGS -DCLS_BANNER=$1 $D -c search.c -o build/$O.o
$CC -m68000 -nostdlib -no-pie -static -T link.ld -Wl,-Map=build/$O.map -Wl,--no-warn-rwx-segments -Wl,--build-id=none \
    build/$O.o -o build/$O.elf
${P}objcopy -O binary -j .ovl build/$O.elf build/$O.bin
${P}objdump -h build/$O.elf > build/$O.sections
${P}objdump -d --no-show-raw-insn build/$O.elf > build/$O.lst
