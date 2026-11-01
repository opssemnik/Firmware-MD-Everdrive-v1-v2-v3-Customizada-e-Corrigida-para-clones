#!/bin/bash
# Assembles the Z80 menu music player (z80drv.asm -> z80drv.bin) in WSL with z80asm, unpacked rootless
# in ~/z80/root (apt-get download z80asm; dpkg -x z80asm_*.deb ~/z80/root). Run by make_musica.py.
set -euo pipefail
cd "$(dirname "$0")"
~/z80/root/usr/bin/z80asm -i z80drv.asm -o z80drv.bin
