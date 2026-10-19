"""v3: image banner (/EDMD/BANNER.ART on sd/sdb.img) in the browser, file menu and ROM info"""
import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
logs = []
def show(m, t):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip(): print(f'{i:2d}|{l}')
for img, tag in (('sd/sdb.img', 'img'), ('sd/sd.img', 'std')):
    m = emu3.boot(OS, img, frames=60, log=logs.append)
    m.press('a', after=200); show(m, f'{tag}: root'); m.screen(f'v3_banner_{tag}_root.png')
    m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('down'); m.run(40); show(m, f'{tag}: list + cover'); m.screen(f'v3_banner_{tag}_list.png')
    m.press('a', after=200); show(m, f'{tag}: file menu'); m.screen(f'v3_banner_{tag}_filemenu.png')
    m.press('right', after=200); m.screen(f'v3_banner_{tag}_filemenu2.png')
    for _ in range(4): m.press('down')
    m.press('a', after=300); show(m, f'{tag}: rom info'); m.screen(f'v3_banner_{tag}_rominfo.png')
    m.press('a', after=200); m.press('b', after=250); show(m, f'{tag}: back'); m.screen(f'v3_banner_{tag}_back.png')
    m.press('c', after=200); m.screen(f'v3_banner_{tag}_mainmenu.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
