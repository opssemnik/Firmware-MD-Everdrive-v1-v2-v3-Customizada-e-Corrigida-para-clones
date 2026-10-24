"""v1: search in every folder (C -> "Buscar em todas as pastas"), with the flash extension install"""
import sys
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
SD = sys.argv[1] if len(sys.argv) > 1 else 'sd/sd.img'
logs = []


def rows(m, t, lo=0, hi=27):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip() and lo <= i <= hi:
            print(f'{i:2d}|{l}')


def search_menu(m):
    m.press('c', after=150)
    for _ in range(6):
        m.press('down')
    m.press('a', after=300)


m = emu.boot(OS, SD, None, log=logs.append)
print('ext before:', bytes(m.mu.mem_read(0x40000, 8)).hex())
m.press('down'); m.press('a', after=150)
rows(m, 'root folder')
m.press('c', after=150); rows(m, 'C menu')
for _ in range(6):
    m.press('down')
m.press('a', after=600)
print('ext after:', bytes(m.mu.mem_read(0x40000, 8)).hex(), '| flash ops:', [l for l in logs if 'flash' in l][:4], '...')
rows(m, 'search modes'); m.screen('v1_search_modes.png')
m.press('down'); m.press('a', after=150); rows(m, 'A - F'); m.press('down'); m.press('down')
m.press('a', after=900); rows(m, 'letter C in every folder'); m.screen('v1_search_c.png')
m.press('a', after=200); rows(m, 'A on a result (file menu)', 3, 5)
m.press('right', after=200); rows(m, 'RIGHT in the file menu', 3, 5)
m.press('b', after=250); rows(m, 'back to the results', 24, 27)
# by name: G A M E <space> G E N
search_menu(m)
m.press('a', after=200); rows(m, 'keyboard'); m.screen('v1_search_kb.png')
KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&"
cx = cy = 0


def go(ch):
    global cx, cy
    i = 40 if ch == ' ' else KEYS.index(ch)
    tx, ty = i % 10, i // 10
    while cy != ty:
        m.press('down' if ty > cy else 'up', after=8)
        cy += 1 if ty > cy else -1
    if ty == 4:                     # the buttons: ESPACO is the first
        while cx * 3 // 10:
            m.press('left', after=8)
            cx = [0, 4, 7][(cx * 3 // 10 + 2) % 3]
    while cx != tx:
        m.press('right' if tx > cx else 'left', after=8)
        cx += 1 if tx > cx else -1
    m.press('a', after=8)


for ch in 'GAME GEN':
    go(ch)
rows(m, 'typed', 3, 20); m.screen('v1_search_kb2.png')
m.press('start', after=1200); rows(m, 'name "GAME GEN"'); m.screen('v1_search_name.png')
search_menu(m); m.press('a', after=200)
for ch in 'ZZZ':
    go(ch)
m.press('start', after=900); rows(m, 'name "ZZZ" (nothing)')
m.press('a', after=300); rows(m, 'after the message: the folder again')
m.press('c', after=150); [m.press('down') for _ in range(5)]; m.press('a', after=400); rows(m, 'C -> Todos')
m.press('b', after=300); rows(m, 'B')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
