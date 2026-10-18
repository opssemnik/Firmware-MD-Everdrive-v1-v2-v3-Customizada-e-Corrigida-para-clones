"""v3: Só Carregar adds to the recents; the list ends with Limpar recentes, which empties it"""
import emu3
logs = []
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
def show(m, t):
    print('---', t); print('\n'.join(l for l in m.text().splitlines() if l.strip()))
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
for moves in (('down', 'down'), ('up',)):              # Columns, then Blockout
    for k in moves: m.press(k, after=20)
    m.press('a', after=200); show(m, 'file menu'); m.press('down'); m.press('a', after=900)   # Só Carregar
    print('load only ->', m.stopped)
show(m, 'browser after loading')
m.press('c', after=200); m.press('down'); m.press('a', after=200); show(m, 'Jogos Recentes'); m.screen('v3_recent16.png')
m.press('down'); m.press('down'); m.press('a', after=300); show(m, 'after Limpar recentes')
m.press('a', after=200); show(m, 'back')
m.press('a', after=200); show(m, 'Jogos Recentes again')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
