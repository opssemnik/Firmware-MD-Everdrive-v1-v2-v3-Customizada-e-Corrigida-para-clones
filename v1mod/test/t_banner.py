"""v1: image banner (/EDMD/BANNER.ART on sd/sdb.img) on the menus and the browser; built-in without it"""
import sys
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
logs = []
def show(m, t):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip(): print(f'{i:2d}|{l}')
for img, tag in (('sd/sdb.img', 'img'), ('sd/sd.img', 'std')):
    m = emu.boot(OS, img, None, log=logs.append)
    show(m, f'{tag}: main menu'); m.screen(f'v1_banner_{tag}_main.png')
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('down'); m.run(60)
    show(m, f'{tag}: browser USA'); m.screen(f'v1_banner_{tag}_list.png')
    m.press('a', after=200); show(m, f'{tag}: file menu'); m.screen(f'v1_banner_{tag}_filemenu.png')
    m.press('b', after=200); show(m, f'{tag}: back in the browser')
    m.press('b', after=200); show(m, f'{tag}: parent folder'); m.screen(f'v1_banner_{tag}_parent.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
