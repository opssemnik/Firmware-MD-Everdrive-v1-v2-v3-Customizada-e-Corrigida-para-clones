"""v3: themes from /EDMD/TEMAS.BIN (sd/sdt.img) and the English pages.
  1. theme 0 of the file: banner tiles (VRAM 0x2E00), wallpaper names (VRAM 0x1400), its colours
  2. Opções -> Tema Visual cycles the names of the file; back in the list the new banner/wallpaper load
  3. Idioma: bit 7 of the settings byte $d flips and the console restarts (reset vector)
  4. English after that restart (same SRAM): browser, main menu, options, search, credits
  5. without TEMAS.BIN (sd.img): the four built-in colour themes, as before"""
import struct
import sys
from pathlib import Path

import emu3
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR

R = Path(__file__).resolve().parents[2]
V3 = str(R / 'MDOS.ptbr.BIN')
PACK = (R / 'sd' / 'EDMD' / 'TEMAS.BIN').read_bytes()
logs = []
ok = True


def check(cond, what):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def lines(m):
    return [l.replace('#', ' ').strip() for l in m.text().splitlines() if l.replace('#', ' ').strip()]


def theme(i):
    base = 512 + i * 64 * 512
    return PACK[base:base + 7 * 512], PACK[base + 8 * 512:base + 64 * 512]


def settings(m):
    return struct.unpack('>I', m.mu.mem_read(0xFFC47A, 4))[0]


def shows_theme(m, i):
    banner, wall = theme(i)
    tiles = bytes(m.vram[0x2E00:0x2E00 + 0xD80]) == banner[32:32 + 0xD80]
    names = bytes(m.vram[0x1400:0x1400 + 2240]) == wall[32:32 + 2240]
    cols = struct.unpack('>6H', banner[0xDA4:0xDB0])
    return tiles and names and m.cram[0] == cols[0] and m.cram[1] == cols[1]


def reboot(sram):
    """power cycle: a new machine with the same cart SRAM"""
    m = emu3.MachineV3(V3, 'sd/sdt.img', logs.append)
    m.mu.mem_write(0x100000, sram)
    m.mu.reg_write(UC_M68K_REG_SR, 0x2700)
    m.mu.reg_write(UC_M68K_REG_A7, 0x01000000)
    m.mu.reg_write(UC_M68K_REG_PC, 0xFF5430)
    m.run(60)
    return m


def options(m):
    m.press('c', after=200)                         # browser -> main menu
    m.press('down')
    m.press('a', after=250)                         # Opções


# 1. theme 0
m = emu3.boot(V3, 'sd/sdt.img', frames=60, log=logs.append)
m.press('a', after=250)
check(shows_theme(m, 0), 'boot: theme 0 (PADRÃO) from TEMAS.BIN')

# 2. options: cycle to theme 1, leave, theme 1 loads
options(m)
t = '\n'.join(lines(m))
print(t)
check('Tema Visual:   PADR*O' in t and 'Idioma:        PT-BR' in t, 'options: theme name from the file + language')
for _ in range(4):
    m.press('down')
m.press('a', after=150)
check('Tema Visual:   RG POA' in m.text(), 'options: next theme name')
m.press('b', after=300)                             # back to the main menu (a box over the list)
check(m.mu.mem_read(0xFFC5A4, 2) == bytes(2), 'leaving the options: banner + wallpaper to load again')
m.press('b', after=300)                             # the list redraws: theme 1 loads
check(shows_theme(m, 1) and 'ROMS' in m.text(), 'browser with theme 1 (RG POA)')
options(m)
for _ in range(4):
    m.press('down')
for _ in range(6):                                  # 1 -> 2 .. 6 -> 0 (7 themes)
    m.press('a', after=120)
check('Tema Visual:   PADR*O' in m.text(), 'options: wraps around after the last theme')
m.press('down')
m.mu.mem_write(0, struct.pack('>II', 0x01000000, 0x100) + bytes(0xF8) + bytes.fromhex('60fe'))  # boot ROM vectors
m.press('a', after=200)                             # Idioma: saves and restarts the console
pc = m.mu.reg_read(UC_M68K_REG_PC)
check(pc in (0x100, 0x102), f'language: the console restarts through the reset vector (pc={pc:06X})')
check(m.mu.mem_read(settings(m) + 0xD, 1)[0] == 0x80, 'settings byte $d: bit 7 (English) + theme 0')
sram = bytes(m.mu.mem_read(0x100000, 0x40000))

# 4. English: the console after that restart (same SRAM: theme 0 + English), then theme 4
m = reboot(sram)
m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('A: file     START: replay   C: menu' in t and '1/1' in lines(m)[-1], 'English browser (help line, page counter)')
check(shows_theme(m, 0), 'theme 0 kept')
m.mu.mem_write(settings(m) + 0xD, bytes([0x84]))   # English, theme 4 (OUTRUN): next time the list loads
m.mu.mem_write(0xFFC5A4, bytes(2))
m.press('c', after=200)
t = '\n'.join(lines(m))
print(t)
check('Main Menu' in t and 'Search All Folders' in t and 'System Info' in t, 'English main menu')
m.press('down'); m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('Theme:         OUTRUN' in t and 'Language:      ENGLISH' in t and 'Game Region:' in t, 'English options')
m.press('b', after=200)
m.press('b', after=300)
check(shows_theme(m, 4), 'theme 4 (OUTRUN) with the English pages')
m.press('c', after=200)
m.press('a', after=250)                             # search (first item)
t = '\n'.join(lines(m))
print(t)
check('By Name (type it)' in t, 'English search page')
m = reboot(sram)                                    # credits, from a fresh main menu
m.press('a', after=250)
m.press('c', after=200)
for _ in range(7):
    m.press('down')
m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('Controls:' in t and 'B - back' in t, 'English credits page')

# 5. no TEMAS.BIN: built-in colour themes
m = emu3.boot(V3, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=250)
options(m)
check('Tema Visual:   PADR*O' in m.text(), 'no TEMAS.BIN: built-in theme names')
for _ in range(4):
    m.press('down')
m.press('a', after=150)
check('Tema Visual:   RG POA' in m.text() and m.cram[1] == 0x022A, 'no TEMAS.BIN: built-in colours applied at once')

errs = [l for l in logs if l.startswith('!!')]
print('\n'.join(errs) or 'no emulator errors')
print('PASS' if ok and not errs else 'FAIL')
sys.exit(0 if ok and not errs else 1)
