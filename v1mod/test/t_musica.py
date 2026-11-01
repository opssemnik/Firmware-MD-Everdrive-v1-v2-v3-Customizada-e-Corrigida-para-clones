"""1.30 menu music (sd/sdt.img: TEMAS.BIN with each theme's song), v1 / v2 and v3:
  - after the first screen the Z80 RAM holds musica/z80drv.bin + the theme's song and the Z80 runs
  - another theme: its song; music off: the Z80 held in reset, every FM key off; on again: it runs
  - starting a game stops it first (the Z80 in reset, FM keys off) before the OS goes on"""
import struct
import sys
from pathlib import Path

import emu
import emu3

R = Path(__file__).resolve().parents[2]
DRV = (R / 'musica' / 'z80drv.bin').read_bytes()
PACK = (R / 'sd' / 'EDMD' / 'TEMAS.BIN').read_bytes()
SLOT, MUSIC = struct.unpack('>HH', PACK[6:8] + PACK[10:12])
logs = []
ok = True


def check(cond, what):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def song(t):
    base = (1 + t * SLOT + MUSIC) * 512
    return PACK[base:base + 13 * 512]


def playing(m, t):
    ram = bytes(m.mu.mem_read(0xA00000, 0x2000))
    return ram[:len(DRV)] == DRV and ram[0x400:0x400 + 13 * 512] == song(t) and m.z80[0x1200] == 0x100 and m.z80[0x1100] == 0


def silent(m):
    keys = {v for p, r, v in m.ym[-60:] if p == 0 and r == 0x28}
    return m.z80[0x1200] == 0 and m.z80[0x1100] == 0 and {0, 1, 2, 4, 5, 6} <= keys


# ---- v1 / v2: main menu item "Música" (11th), theme item (9th)
m = emu.boot(str(R / 'OS-V38-PTBR.BIN'), 'sd/sdt.img', None, log=logs.append)
t = m.text()
check('M*sica: LIG' in t, 'v1: main menu "Música: LIG"')
check(playing(m, 0), 'v1: the player + PADRÃO\'s song in the Z80 RAM, the Z80 running')
for _ in range(8):
    m.press('down')
m.press('a', after=400)                             # Tema -> RG POA
check(playing(m, 1), 'v1: theme RG POA -> its song')
m.press('down'); m.press('down')
m.press('a', after=250)                             # Música -> DESL
check('M*sica: DESL' in m.text() and silent(m), 'v1: music off: Z80 in reset, FM keys off')
m.press('a', after=250)
check('M*sica: LIG' in m.text() and playing(m, 1), 'v1: music on again')
flash = bytes(m.mu.mem_read(0x30000, 0x10000))
for _ in range(10):
    m.press('up')
m.ym.clear()
m.press('a', after=300)                             # Jogar último jogo -> osStartGame
check(m.stopped and m.stopped.startswith('startGame') and silent(m), f'v1: game start stops the music ({m.stopped})')

m = emu.boot(str(R / 'OS-V38-PTBR.BIN'), 'sd/sdt.img', flash, log=logs.append)
check(playing(m, 1), 'v1: after a reboot: RG POA\'s song')

# ---- v3: Opções -> Música (7th item)
m = emu3.boot(str(R / 'MDOS.ptbr.BIN'), 'sd/sdt.img', frames=60, log=logs.append)
m.press('a', after=250)
check(playing(m, 0), 'v3: the player + PADRÃO\'s song in the Z80 RAM, the Z80 running')
m.press('c', after=200)
m.press('down')
m.press('a', after=250)                             # Opções
check('M*sica:        LIG' in m.text().replace('#', ' '), 'v3: options "Música: LIG"')
for _ in range(6):
    m.press('down')
m.press('a', after=150)
check('M*sica:        DESL' in m.text().replace('#', ' '), 'v3: "Música: DESL"')
m.press('b', after=300)
m.press('b', after=400)                             # back in the list: theme reloads, no music
check(silent(m), 'v3: music off: Z80 in reset, FM keys off')
m.press('c', after=200)
m.press('down')
m.press('a', after=250)
for _ in range(6):
    m.press('down')
m.press('a', after=150)                             # on again
m.press('up'); m.press('up')
m.press('a', after=150)                             # and the next theme (RG POA)
m.press('b', after=300)
m.press('b', after=400)
check(playing(m, 1), 'v3: music on again, with RG POA\'s song')
m.press('down'); m.press('a', after=200)            # ROMS
m.press('down'); m.press('a', after=200)            # USA
m.ym.clear()
m.press('start', after=400)                         # a game from the list
r = m.stopped or ''
if not r.startswith('startGame'):
    m.press('a', after=200)
    m.press('a', after=600)                         # file menu: Carregar e Jogar
    r = m.stopped or ''
check(r.startswith('startGame') and silent(m), f'v3: game start stops the music ({r})')

errs = [l for l in logs if l.startswith('!!')]
print('\n'.join(errs) or 'no emulator errors')
print('PASS' if ok and not errs else 'FAIL')
sys.exit(0 if ok and not errs else 1)
