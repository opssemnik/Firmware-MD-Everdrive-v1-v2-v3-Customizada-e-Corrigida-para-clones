"""v3: letter filter from the main menu (C -> Filtrar por Letra)"""
import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
logs = []
def rows(m, t, lo=0, hi=27):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip() and lo <= i <= hi: print(f'{i:2d}|{l}')
def filt(m, group, letter=None):
    m.press('c', after=200)
    for _ in range(7): m.press('down', after=20)
    m.press('a', after=300)
    for _ in range(group): m.press('down', after=20)
    m.press('a', after=300)
    if letter is not None:
        for _ in range(letter): m.press('down', after=20)
        m.press('a', after=500)
m = emu3.boot(OS, 'sd/sdw.img', frames=60, log=logs.append)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
rows(m, 'USA', 3, 27)
m.press('c', after=200); [m.press('down', after=20) for _ in range(7)]; rows(m, 'main menu, cursor on the new item'); m.press('a', after=300); rows(m, 'groups'); m.press('b', after=300); m.press('b', after=300)
filt(m, 1, 0); rows(m, 'filter G', 3, 27); m.screen('v3_filter_g.png')
m.press('down', after=30); m.press('a', after=300); rows(m, 'file menu on the 2nd', 3, 5); m.press('b', after=300)
rows(m, 'back from the file menu', 24, 27)
filt(m, 4); rows(m, '0-9 e outros (none)')
m.press('a', after=400); rows(m, 'after the message', 3, 27)
filt(m, 5); rows(m, 'Todos', 3, 27)
filt(m, 1, 0); m.press('b', after=400); rows(m, 'B from the filtered folder -> ROMS', 3, 27)
m.press('down', after=30); m.press('a', after=400); rows(m, 'USA again', 3, 27)
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
