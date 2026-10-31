"""1.28 layout (v1 / v2 and v3, sd/sdbig.img): help line on row 3, row 4 blank, list rows 5-25 (21 per
page), page counter row 26; going back from a full page to a short folder leaves row 25 empty"""
import sys
from pathlib import Path

import emu
import emu3

R = Path(__file__).resolve().parents[2]
ok = True
logs = []


def check(cond, what):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def rows(m):
    return [l.replace('#', ' ').rstrip() for l in m.text().splitlines()]


for name, boot in (('v1', lambda: emu.boot(str(R / 'OS-V38-PTBR.BIN'), 'sd/sdbig.img', None, log=logs.append)),
                   ('v3', lambda: emu3.boot(str(R / 'MDOS.ptbr.BIN'), 'sd/sdbig.img', frames=60, log=logs.append))):
    m = boot()
    if name == 'v1':
        m.press('down'); m.press('a', after=250)    # Selecionar jogo
    else:
        m.press('a', after=250)
    r = rows(m)
    i = next(k for k, l in enumerate(r) if 'MUITOS' in l)
    for _ in range(i - 5):
        m.press('down')
    m.press('a', after=250)                         # into /MUITOS
    r = rows(m)
    print('\n'.join(f'{k:2}|{l}' for k, l in enumerate(r)))
    check('START' in r[3] and not r[4].strip() and 'JOGO01' in r[5] and 'JOGO21' in r[25] and '1' in r[26],
          f'{name}: help row 3, blank row 4, list 5-25, page row 26')
    m.press('right', after=200)                     # page 2: 9 games, rows 14-25 empty
    r = rows(m)
    check('JOGO22' in r[5] and 'JOGO30' in r[13] and not ''.join(r[14:26]).strip(), f'{name}: page 2, rows 14-25 empty')
    m.press('b', after=250)                         # back to the root
    r = rows(m)
    check(not r[25].strip() and 'MUITOS' in '\n'.join(r[5:12]), f'{name}: back in the root, row 25 empty')
errs = [l for l in logs if l.startswith('!!')]
print('\n'.join(errs) or 'no emulator errors')
print('PASS' if ok and not errs else 'FAIL')
sys.exit(0 if ok and not errs else 1)
