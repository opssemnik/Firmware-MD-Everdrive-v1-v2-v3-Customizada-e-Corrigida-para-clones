"""v1: letter filter in the browser (C)"""
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
logs = []
def rows(m, t, lo=0, hi=27):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip() and lo <= i <= hi: print(f'{i:2d}|{l}')
m = emu.boot(OS, 'sd/sdw.img', None, log=logs.append)
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('a', after=120)
rows(m, 'USA folder')
m.press('c', after=150); rows(m, 'C: groups')
m.press('down'); m.press('a', after=150); rows(m, 'G - L')
m.press('a', after=400); rows(m, 'filter G'); m.screen('v1_filter_g.png')
m.press('down', after=60); m.press('a', after=200); rows(m, 'A on the 2nd game (file menu)', 3, 5)
m.press('right', after=200); rows(m, 'RIGHT in the file menu', 3, 5)
m.press('b', after=250); rows(m, 'back')
m.press('c', after=150); m.press('b', after=200); rows(m, 'C then B (cancel)')
m.press('c', after=150); [m.press('down') for _ in range(5)]; m.press('a', after=400); rows(m, 'Todos')
m.press('c', after=150); [m.press('down') for _ in range(4)]; m.press('a', after=400); rows(m, '0-9 e outros')
m.press('a', after=200)
m.press('c', after=150); m.press('down'); m.press('a', after=150); m.press('a', after=400); rows(m, 'filter G again', 24, 27)
m.press('b', after=300); rows(m, 'B: parent folder (ROMS)')
m.press('down', after=40); m.press('a', after=300); rows(m, 'USA again: whole folder, no tag')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
