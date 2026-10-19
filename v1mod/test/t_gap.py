"""blank row between the banner and the game list (v1 and v3), long file name on the last rows"""
import emu, emu3
from PIL import Image
V1 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
V3 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
def rows(m, t):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip(): print(f'{i:2d}|{l}')
shots = []
for img in ('sd/sdb.img', 'sd/sd.img'):
    m = emu.boot(V1, img, None, log=print)
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
    m.press('down'); m.press('a', after=120); [m.press('down') for _ in range(3)]; m.run(60)
    rows(m, 'v1 ' + img); m.screen('g.png'); shots.append(Image.open('g.png').resize((320, 224)))
    m = emu3.boot(V3, img, frames=60, log=print)
    m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    [m.press('down') for _ in range(3)]; m.run(40)
    rows(m, 'v3 ' + img); m.screen('g.png'); shots.append(Image.open('g.png').resize((320, 224)))
c = Image.new('RGB', (640, 448))
for i, im in enumerate(shots):
    c.paste(im, ((i % 2) * 320, (i // 2) * 224))
c.save('gap_grid.png')
