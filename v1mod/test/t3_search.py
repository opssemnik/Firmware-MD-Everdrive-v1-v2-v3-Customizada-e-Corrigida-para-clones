"""v3: search in every folder (C -> main menu -> Buscar em Todas as Pastas, overlay page 2)"""
import sys
import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
SD = sys.argv[1] if len(sys.argv) > 1 else 'sd/sdw.img'
KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&"
logs = []


def rows(m, t, lo=0, hi=27):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip() and lo <= i <= hi:
            print(f'{i:2d}|{l}')


def type_text(m, text):
    cx = cy = 0
    for ch in text:
        i = 40 if ch == ' ' else KEYS.index(ch)
        tx, ty = i % 10, i // 10
        while cy != ty:
            m.press('down' if ty > cy else 'up', after=12)
            cy += 1 if ty > cy else -1
        if ty == 4:
            while cx * 3 // 10:
                m.press('left', after=12)
                cx = [0, 4, 7][(cx * 3 // 10 + 2) % 3]
        while cx != tx:
            m.press('right' if tx > cx else 'left', after=12)
            cx += 1 if tx > cx else -1
        m.press('a', after=12)


def search(m):
    m.press('c', after=200)
    m.press('a', after=400)


m = emu3.boot(OS, SD, frames=60, log=logs.append)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down', after=30); m.press('down', after=30)
rows(m, 'USA, cursor on the 3rd', 3, 27); m.screen('v3_help.png')
m.press('c', after=200); rows(m, 'C: main menu')
m.press('a', after=400); rows(m, 'search modes'); m.screen('v3_search_modes.png')
m.press('down', after=20); m.press('a', after=300); rows(m, 'A - F')
m.press('down', after=20); m.press('down', after=20); m.press('a', after=1200)
rows(m, 'letter C in every folder'); m.screen('v3_search_c.png')
m.press('a', after=300); rows(m, 'A on a result (file menu)', 3, 5)
m.press('b', after=300); rows(m, 'back to the results', 3, 27)
m.press('b', after=400); rows(m, 'B: back to USA, cursor on the 3rd', 3, 27)
search(m); m.press('a', after=300); rows(m, 'keyboard'); m.screen('v3_search_kb.png')
type_text(m, 'GAME GEN'); rows(m, 'typed', 3, 20)
m.press('start', after=1500); rows(m, 'name "GAME GEN"', 3, 27); m.screen('v3_search_name.png')
search(m); m.press('a', after=300); type_text(m, 'ZZZ')
m.press('start', after=1200); rows(m, 'name "ZZZ" (nothing)')
m.press('a', after=500); rows(m, 'after the message', 3, 27)
m.press('b', after=400); rows(m, 'B', 3, 27)
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
