"""v3: themes from /EDMD/TEMAS.BIN (sd/sdt.img) and the English pages.
  1. theme 0 of the file: banner tiles (VRAM 0x2E00), wallpaper names (VRAM 0x1400), its colours
  2. Opções -> Tema Visual cycles the names of the file; back in the list the new banner/wallpaper load
  3. Idioma: the restart message, the settings byte flips
  4. English (settings byte $c = 1 before the first folder read): browser, main menu, options, search
  5. without TEMAS.BIN (sd.img): the four built-in colour themes, as before"""
import struct
import sys
from pathlib import Path

import emu3

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
m.press('a', after=200)                             # Idioma
t = '\n'.join(lines(m))
check('Reinicie o console / Restart the console' in t, 'language: restart message')
check(m.mu.mem_read(settings(m) + 0xC, 1)[0] == 1, 'language byte = 1')
m.press('a', after=200)
check('Idioma:        ENGLISH' in m.text(), 'options: ENGLISH shown')

# 4. English
m = emu3.boot(V3, 'sd/sdt.img', frames=60, log=logs.append)
m.mu.mem_write(settings(m) + 0xC, bytes([1, 4]))    # English, theme 4 (OUTRUN)
m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('A: file     START: replay   C: menu' in t and 'Page' in t, 'English browser (help line, page counter)')
check(shows_theme(m, 4), 'theme 4 (OUTRUN) at boot')
m.press('c', after=200)
t = '\n'.join(lines(m))
print(t)
check('Main Menu' in t and 'Search All Folders' in t and 'System Info' in t, 'English main menu')
m.press('down'); m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('Theme:         OUTRUN' in t and 'Language:      ENGLISH' in t and 'Game Region:' in t, 'English options')
m.press('b', after=200)
m.press('up')
m.press('a', after=250)                             # search
t = '\n'.join(lines(m))
print(t)
check('By Name (type it)' in t, 'English search page')
m.press('b', after=200)
for _ in range(7):
    m.press('down')
m.press('a', after=250)                             # credits
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
