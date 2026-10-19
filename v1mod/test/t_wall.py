"""wallpaper (/EDMD/WALL.ART on sd/sdw.img): browser, folders, file menu, main menu; v1 and v3"""
import sys
import emu, emu3
from PIL import Image
V1 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
V3 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
which = sys.argv[1] if len(sys.argv) > 1 else 'v1'
logs = []
shots = []
def snap(m):
    m.screen('w.png'); shots.append(Image.open('w.png').resize((320, 224)))
if which == 'v1':
    m = emu.boot(V1, 'sd/sdw.img', None, log=logs.append); snap(m)                                    # main menu
    m.press('down'); m.press('a', after=120); snap(m)                                                  # root
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
    m.press('down'); m.press('down'); m.run(60); snap(m)                                               # USA + cover
    m.press('a', after=200); snap(m)                                                                   # file menu
    m.press('b', after=200); m.press('b', after=200); snap(m)                                          # back, parent
else:
    m = emu3.boot(V3, 'sd/sdw.img', frames=60, log=logs.append)
    m.press('a', after=200); snap(m)
    m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('down'); m.run(40); snap(m)
    m.press('a', after=200); snap(m)
    m.press('b', after=250); snap(m)
    m.press('c', after=200); snap(m)
c = Image.new('RGB', (640, 224 * ((len(shots) + 1) // 2)))
for i, im in enumerate(shots):
    c.paste(im, ((i % 2) * 320, (i // 2) * 224))
c.save(f'wall_{which}.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
