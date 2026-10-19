"""highlight bar behind [ LIMPAR RECENTES ] (v1 and v3, with and without the image banner)"""
import emu, emu3
from PIL import Image
V1 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
V3 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
shots = []
for img in ('sd/sd.img', 'sd/sdb.img'):
    m = emu.boot(V1, img, None, log=print)
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('down'); m.press('a', after=200)
    m.press('down'); m.press('a', after=900)                    # Só carregar Columns -> recents
    for _ in range(4): m.press('b', after=150)
    m.press('down'); m.press('a', after=200)                    # Jogos recentes
    m.press('down', after=60); m.screen('hi.png'); shots.append(Image.open('hi.png').resize((320, 224)))
    m.press('b', after=200); m.screen('hi_after.png'); shots.append(Image.open('hi_after.png').resize((320, 224)))
    m = emu3.boot(V3, img, frames=60, log=print)
    m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('down'); m.press('a', after=200); m.press('down'); m.press('a', after=900)
    m.press('c', after=200); m.press('down'); m.press('a', after=200)
    m.screen('hi.png'); shots.append(Image.open('hi.png').resize((320, 224)))
    m.press('b', after=200); m.screen('hi_after.png'); shots.append(Image.open('hi_after.png').resize((320, 224)))
c = Image.new('RGB', (640, 896))
for i, im in enumerate(shots):
    c.paste(im, ((i % 2) * 320, (i // 2) * 224))
c.save('hi_grid.png')
