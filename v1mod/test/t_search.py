"""v1: search in every folder (C in the browser), the extension installed by the loader at boot"""
import sys
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
SD = sys.argv[1] if len(sys.argv) > 1 else 'sd/sd.img'
logs = []
KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&"


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


m = emu.boot(OS, SD, None, log=logs.append)
print('ext:', bytes(m.mu.mem_read(0x40000, 16)).hex())
m.press('down'); m.press('a', after=150)
m.press('down'); m.press('a', after=150)          # ROMS
m.press('down'); m.press('a', after=150)          # USA
m.press('down'); m.press('down')                  # cursor on the 3rd game
rows(m, 'USA folder, cursor on the 3rd'); m.screen('v1_help.png')
m.press('c', after=150); rows(m, 'C: search modes'); m.screen('v1_search_modes.png')
m.press('down'); m.press('a', after=150); rows(m, 'A - F')
m.press('down'); m.press('down'); m.press('a', after=900)
rows(m, 'letter C in every folder'); m.screen('v1_search_c.png')
m.press('a', after=200); rows(m, 'A on a result (file menu)', 3, 5)
m.press('right', after=200); rows(m, 'RIGHT in the file menu', 3, 5)
m.press('b', after=250); rows(m, 'back to the results', 24, 27)
m.press('b', after=300); rows(m, 'B: back to USA, cursor on the 3rd', 3, 27)
m.press('c', after=150); m.press('a', after=200); rows(m, 'keyboard'); m.screen('v1_search_kb.png')
type_text(m, 'GAME GEN')
rows(m, 'typed', 3, 20); m.screen('v1_search_kb2.png')
m.press('start', after=1200); rows(m, 'name "GAME GEN"'); m.screen('v1_search_name.png')
m.press('c', after=150); m.press('a', after=200)
type_text(m, 'ZZZ')
m.press('start', after=900); rows(m, 'name "ZZZ" (nothing)')
m.press('a', after=300); rows(m, 'after the message')
m.press('c', after=150); m.press('b', after=300); rows(m, 'C then B (cancel)', 24, 27)
m.press('b', after=300); rows(m, 'B')
m.press('b', after=300); rows(m, 'B')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
