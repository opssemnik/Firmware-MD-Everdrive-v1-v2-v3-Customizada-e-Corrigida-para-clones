"""Screenshots for the README (v1mod/screens, v3/screens, temas/*/previa_*.png), from the emulators.
SD images (sdput.sh): sd.img plain, sdw.img = the banner/wallpaper of the release zips, sdm.img = the
Maddrugamers theme."""
from pathlib import Path

from PIL import Image

import emu
import emu3

MG = Path(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis')
V1, V3 = str(MG / 'OS-V38-PTBR.BIN'), str(MG / 'MDOS.ptbr.BIN')
S1, S3, TM = MG / 'v1mod' / 'screens', MG / 'v3' / 'screens', MG / 'temas' / 'maddrugamers'
KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&"
errors = []


def type_text(m, text, wait=12):
    cx = cy = 0
    for ch in text:
        i = 40 if ch == ' ' else KEYS.index(ch)
        tx, ty = i % 10, i // 10
        while cy != ty:
            m.press('down' if ty > cy else 'up', after=wait)
            cy += 1 if ty > cy else -1
        if ty == 4:
            while cx * 3 // 10:
                m.press('left', after=wait)
                cx = [0, 4, 7][(cx * 3 // 10 + 2) % 3]
        while cx != tx:
            m.press('right' if tx > cx else 'left', after=wait)
            cx += 1 if tx > cx else -1
        m.press('a', after=wait)


def v1(sd):
    return emu.boot(V1, f'sd/{sd}', None, log=lambda s: errors.append(s) if s.startswith('!!') else None)


def v1_usa(m):                      # Selecionar jogo -> ROMS -> USA, cursor on Columns, its cover shown
    m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('down', after=90)


def v3(sd):
    return emu3.boot(V3, f'sd/{sd}', frames=60, log=lambda s: errors.append(s) if s.startswith('!!') else None)


def v3_usa(m):
    m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    m.press('down', after=30); m.press('down', after=90)


# ---- v1, release look (sdw.img)
m = v1('sdw.img'); m.screen(S1 / 'menu_principal.png')
v1_usa(m); m.screen(S1 / 'lista_wallpaper.png')
m.press('a', after=250); m.screen(S1 / 'menu_do_jogo.png')
for _ in range(4):
    m.press('down')
m.press('a', after=200); m.screen(S1 / 'info_da_rom.png')
m.press('a', after=150); m.press('b', after=250)
m.press('c', after=200); m.screen(S1 / 'busca_modos.png')
m.press('a', after=200); type_text(m, 'GAME GEN'); m.screen(S1 / 'busca_teclado.png')
m.press('start', after=1200); m.run(60); m.screen(S1 / 'busca_resultados.png')
m = v1('sdw.img'); [m.press('down') for _ in range(7)]; m.press('a', after=200)
[m.press('down') for _ in range(4)]; m.press('a', after=200); m.screen(S1 / 'creditos.png')
m = v1('sd.img'); v1_usa(m); m.screen(S1 / 'lista_com_capa.png')
m = v1('sd.img'); [m.press('down') for _ in range(8)]
shots = []
for t in range(4):                  # the 4 themes (plain card: their backdrop shows)
    if t:
        m.press('a', after=300)
    m.screen('th.png')
    shots.append(Image.open('th.png').copy())
sheet = Image.new('RGB', (1280, 896))
for i, im in enumerate(shots):
    sheet.paste(im, ((i % 2) * 640, (i // 2) * 448))
sheet.save(S1 / 'temas.png')

# ---- v3, release look (sdw.img)
m = v3('sdw.img'); v3_usa(m); m.screen(S3 / 'lista_wallpaper.png')
m.press('a', after=300); m.screen(S3 / 'menu_do_arquivo.png'); m.press('b', after=300)
m.press('c', after=200); m.screen(S3 / 'menu_principal.png')
m.press('a', after=400); m.press('a', after=300); type_text(m, 'GAME GEN'); m.screen(S3 / 'busca_teclado.png')
m.press('start', after=1500); m.run(60); m.screen(S3 / 'busca_resultados.png')
m = v3('sd.img'); v3_usa(m); m.screen(S3 / 'lista_com_capa.png')

# ---- Maddrugamers theme (sdm.img)
m = v1('sdm.img'); m.screen(TM / 'previa_v1_menu.png')
v1_usa(m); m.screen(TM / 'previa_v1.png')
m = v3('sdm.img'); v3_usa(m); m.screen(TM / 'previa_v3.png')
m.press('c', after=200); m.screen(TM / 'previa_v3_menu.png')
print('\n'.join(errors) or 'no emulator errors')
