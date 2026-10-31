"""temas/previa_temas.png: the game list (v3, sd/sdt.img) with each theme of TEMAS.BIN, side by side"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw

import emu3

R = Path(__file__).resolve().parents[2]
V3 = str(R / 'MDOS.ptbr.BIN')
NAMES = ['PADRÃO', 'RG POA', 'SEGA 16', 'OUTRUN', 'SYNTHWAVE', 'MADDRUGA', 'RETROCHIMP']
shots = []
for t, name in enumerate(NAMES):
    m = emu3.boot(V3, 'sd/sdt.img', frames=60, log=lambda s: None)
    sp = struct.unpack('>I', m.mu.mem_read(0xFFC47A, 4))[0]
    m.mu.mem_write(sp + 0xD, bytes([t]))
    m.press('a', after=250)
    m.press('down'); m.press('a', after=150); m.press('down', after=60)    # ROMS, a game (cover)
    p = Path(__file__).with_name(f'previa_{t}.png')     # git-ignored (test/*.png)
    m.screen(str(p))
    shots.append((name, Image.open(p).convert('RGB')))
w, h = shots[0][1].size
cols = 4
sheet = Image.new('RGB', (cols * (w + 8) + 8, 2 * (h + 26) + 8), (24, 24, 24))
d = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(shots):
    x, y = 8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 26)
    sheet.paste(im, (x, y))
    d.text((x + 4, y + h + 6), name.replace('Ã', 'A'), fill=(230, 230, 230))     # PIL's default font: ASCII
sheet.save(R / 'temas' / 'previa_temas.png')
print('ok', sheet.size)
