from PIL import Image
from t_all_lib import *
D = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\v1mod\screens'
m = new(); m.screen(D + r'\menu_principal.png')
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.run(60); m.screen(D + r'\lista_com_capa.png')
m.press('down'); m.press('down'); m.press('a', after=200); m.screen(D + r'\menu_do_jogo.png')
for _ in range(3): m.press('down')
m.press('a', after=150); m.screen(D + r'\info_da_rom.png')
m = new(); [m.press('down') for _ in range(7)]; m.press('a', after=200); [m.press('down') for _ in range(4)]
m.press('a', after=200); m.screen(D + r'\creditos.png')
m = new(); [m.press('down') for _ in range(8)]; shots = []
for t in range(4):
    if t: m.press('a', after=300)
    m.screen('th.png'); shots.append(Image.open('th.png').copy())
sheet = Image.new('RGB', (1280, 896))
for i, im in enumerate(shots): sheet.paste(im, ((i % 2) * 640, (i // 2) * 448))
sheet.save(D + r'\temas.png')
