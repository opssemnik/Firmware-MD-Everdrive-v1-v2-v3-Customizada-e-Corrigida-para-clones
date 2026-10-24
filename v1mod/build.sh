#!/bin/bash
# Compiles the v1 mod inside WSL with the rootless m68k toolchain (~/m68k/root).
# usage: build.sh BUILD_ID [DEFINES]   (run by build_v1_ptbr.py; BUILD_ID = the extension's, DEFINES e.g. "-DDIAG")
set -euo pipefail
DEFS="${2:-}"
R=$HOME/m68k/root
export PATH=$R/usr/bin:$PATH
export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu
CC="m68k-linux-gnu-gcc-14 -B$R/usr/lib/gcc-cross/m68k-linux-gnu/14/ -B$R/usr/m68k-linux-gnu/bin/ -B$R/usr/libexec/gcc-cross/m68k-linux-gnu/14/"
P=m68k-linux-gnu-

cd "$(dirname "$0")"
mkdir -p build
CFLAGS="-m68000 -Os -ffreestanding -fno-pic -fno-pie -fomit-frame-pointer -fno-asynchronous-unwind-tables \
 -fno-tree-loop-distribute-patterns -fno-store-merging -fno-common -Wall -Wno-pointer-sign -Werror"

$CC $CFLAGS -fno-builtin -I. -c loader.c -o build/loader.o
$CC $CFLAGS $DEFS -DBUILD_ID=$1 -I. -Ibuild -c mod.c -o build/mod.o
$CC $CFLAGS $DEFS -I. -Ibuild -c build/gen.c -o build/gen.o
$CC -m68000 $DEFS -c hooks.S -o build/hooks.o
$CC -m68000 -nostdlib -no-pie -static -T link.ld -Wl,-Map=build/mod.map -Wl,--no-warn-rwx-segments     build/loader.o build/mod.o build/gen.o build/hooks.o -o build/mod.elf

${P}objcopy -O binary -j .base build/mod.elf build/base.bin
# the extension image: everything loaded at 0x40000 (header + code + data, RAM stubs, patch table)
${P}objcopy -O binary --gap-fill 0xff -j .ext -j .ramstub -j .patch -j .data build/mod.elf build/ext.bin
${P}nm -n build/mod.elf > build/mod.sym
${P}objdump -h build/mod.elf > build/mod.sections
${P}objdump -d --no-show-raw-insn build/mod.elf > build/mod.lst
