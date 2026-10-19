"""v3 overlay screens: ROM info, options, recents, favourites, credits, Jogar com Cheats"""
import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
logs = []
def show(m, t, first=0, last=28):
    print('---', t)
    for i, l in enumerate(m.text().splitlines()):
        if l.strip() and first <= i <= last: print(f'{i:2d}|{l}')
def to_columns():
    m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
    m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
    m.press('down'); m.press('down'); m.press('a', after=200)
    return m
m = to_columns(); show(m, 'file menu'); m.screen('v3_ovl_filemenu.png')
for _ in range(4): m.press('down')
m.press('a', after=300); show(m, 'Info da ROM'); m.screen('v3_ovl_rominfo.png')
m.press('a', after=200); show(m, 'back to the file menu', 0, 6)
m.press('down', after=20); m.press('down', after=20); m.press('down', after=20); m.press('down', after=20)  # back to row 2
m = to_columns(); m.press('down'); m.press('down'); m.press('a', after=400); show(m, 'Jogar com Cheats -> cheat editor'); m.screen('v3_ovl_cheats.png')
m.press('b', after=600); print('B in the editor ->', m.stopped)
m = to_columns(); m.press('down'); m.press('a', after=900)          # Só Carregar -> recents
m.press('c', after=200); show(m, 'main menu')
m.press('a', after=200); show(m, 'Opções'); m.press('down'); m.press('down'); m.press('down'); m.press('down'); m.press('a', after=200); show(m, 'Opções: tema trocado')
m.press('b', after=200); m.press('down'); m.press('a', after=200); show(m, 'Jogos Recentes')
m.press('b', after=200); m.press('down'); m.press('a', after=200); show(m, 'Favoritos')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
