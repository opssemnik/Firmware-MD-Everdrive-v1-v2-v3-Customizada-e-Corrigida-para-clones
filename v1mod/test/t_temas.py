"""v1 / v2: themes from /EDMD/TEMAS.BIN (sd/sdt.img) and the language item of the main menu.
  1. theme 0 of the file at boot: banner tiles (VRAM 0x2E00), wallpaper names (VRAM 0x0100), colours
  2. "Tema: ..." cycles the file's themes and loads each at once (also the last one, far in the file)
  3. "Idioma: PT-BR" -> English menus and stock strings, kept in flash across a reboot; and back
  4. without TEMAS.BIN (sd.img): the four built-in colour themes"""
import struct
import sys
from pathlib import Path

import emu

R = Path(__file__).resolve().parents[2]
V1 = str(R / 'OS-V38-PTBR.BIN')
PACK = (R / 'sd' / 'EDMD' / 'TEMAS.BIN').read_bytes()
logs = []
ok = True


def check(cond, what):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def lines(m):
    return [l.replace('#', ' ').strip() for l in m.text().splitlines() if l.replace('#', ' ').strip()]


def shows_theme(m, i):
    base = 512 + i * 64 * 512
    banner, wall = PACK[base:base + 7 * 512], PACK[base + 8 * 512:base + 64 * 512]
    tiles = bytes(m.vram[0x2E00:0x2E00 + 0xD80]) == banner[32:32 + 0xD80]
    names = bytes(m.vram[0x0100:0x0100 + 2240]) == wall[32:32 + 2240]
    cols = struct.unpack('>6H', banner[0xDA4:0xDB0])
    return tiles and names and m.cram[0] == cols[0] and m.cram[1] == cols[1]


def item(m, n):
    """main menu item n (from the top), A"""
    for _ in range(n):
        m.press('down')
    m.press('a', after=250)


m = emu.boot(V1, 'sd/sdt.img', None, log=logs.append)
t = '\n'.join(lines(m))
print(t)
check('Tema: PADR*O' in t and 'Idioma: PT-BR' in t, 'main menu: theme name from the file, language item')
check(shows_theme(m, 0), 'boot: theme 0 (PADRÃO)')
item(m, 8)
check('Tema: RG POA' in m.text() and shows_theme(m, 1), 'theme item: RG POA loaded at once')
n0 = m.mu.reg_read(0)
for k in range(2, 7):
    m.press('a', after=400)
check('Tema: MADDRUGA' in m.text() and shows_theme(m, 6), 'cycled to the last theme (MADDRUGA)')
m.press('a', after=400)
check('Tema: PADR*O' in m.text() and shows_theme(m, 0), 'wraps around to PADRÃO')
m.press('a', after=400)                             # theme 1 again, saved
m.press('down')
m.press('a', after=250)                             # Idioma -> English
t = '\n'.join(lines(m))
print(t)
check('Play last game' in t and 'Language: ENGLISH' in t and 'Theme: RG POA' in t, 'English main menu')
flash = bytes(m.mu.mem_read(0x30000, 0x10000))

m = emu.boot(V1, 'sd/sdt.img', flash, log=logs.append)
t = '\n'.join(lines(m))
check('Play last game' in t and 'Theme: RG POA' in t and shows_theme(m, 1), 'after a reboot: English + RG POA')
item(m, 5)                                          # Options (stock screen, stock English strings)
t = '\n'.join(lines(m))
print(t)
check('Reset total' not in t and 'salvando' not in t, 'stock options screen in English')
m.press('b', after=250)
item(m, 4)                                          # Language (the cursor stays on Options) -> Portuguese
t = '\n'.join(lines(m))
check('Jogar *ltimo jogo' in t and 'Idioma: PT-BR' in t, 'back to Portuguese')
for _ in range(4):
    m.press('up')
m.press('a', after=250)
t = '\n'.join(lines(m))
print(t)
check('Reset total' in t, 'stock options screen in Portuguese again')

m = emu.boot(V1, 'sd/sd.img', None, log=logs.append)
check('Tema: PADR*O' in m.text(), 'no TEMAS.BIN: built-in theme names')
item(m, 8)
check('Tema: RG POA' in m.text() and m.cram[1] == 0x00A, 'no TEMAS.BIN: built-in colours')

errs = [l for l in logs if l.startswith('!!')]
print('\n'.join(errs) or 'no emulator errors')
print('PASS' if ok and not errs else 'FAIL')
sys.exit(0 if ok and not errs else 1)
