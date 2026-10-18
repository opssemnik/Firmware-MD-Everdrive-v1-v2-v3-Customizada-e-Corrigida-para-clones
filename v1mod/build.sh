#!/bin/bash
# Compiles the v1 mod inside WSL with the rootless m68k toolchain (~/m68k/root).
# usage: build.sh BUILD_ID   (run by build_v1_ptbr.py)
set -euo pipefail
R=$HOME/m68k/root
export PATH=$R/usr/bin:$PATH
export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu
CC="m68k-linux-gnu-gcc-14 -B$R/usr/lib/gcc-cross/m68k-linux-gnu/14/ -B$R/usr/m68k-linux-gnu/bin/ -B$R/usr/libexec/gcc-cross/m68k-linux-gnu/14/"
P=m68k-linux-gnu-

cd "$(dirname "$0")"
mkdir -p build
CFLAGS="-m68000 -Os -ffreestanding -fno-pic -fno-pie -fomit-frame-pointer -fno-asynchronous-unwind-tables \
 -fno-tree-loop-distribute-patterns -fno-common -Wall -Wno-pointer-sign -Werror"

$CC $CFLAGS -I. -Ibuild -c mod.c -o build/mod.o
$CC $CFLAGS -I. -Ibuild -c build/gen.c -o build/gen.o
$CC -m68000 -DBUILD_ID=$1 -c hooks.S -o build/hooks.o
$CC -m68000 -nostdlib -no-pie -static -T link.ld -Wl,-Map=build/mod.map -Wl,--no-warn-rwx-segments \
    build/mod.o build/gen.o build/hooks.o -o build/mod.elf

for s in text strb strc ramstub data; do
    ${P}objcopy -O binary -j .$s build/mod.elf build/$s.bin
done
${P}nm -n build/mod.elf > build/mod.sym
${P}objdump -h build/mod.elf > build/mod.sections
${P}objdump -d --no-show-raw-insn build/mod.elf > build/mod.lst
