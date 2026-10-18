import emu3
logs = []
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
def show(m, t):
    print('---', t); print('\n'.join(l for l in m.text().splitlines() if l.strip()))
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=200)
m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down'); m.press('down'); m.run(40)            # rest on Columns -> preview
m.press('a', after=200); show(m, 'file menu on Columns')
m.press('a', after=900); print('Carregar e Jogar ->', m.stopped, m.calls.get('disk_read'))
sram = m   # recent list lives in cart SRAM; continue in the same machine for the menus
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=200)
m.press('c', after=200); show(m, 'main menu (C)'); m.screen('v3_mainmenu.png')
m.press('down'); m.press('a', after=200); show(m, 'recent list (fresh card)')
m.press('b', after=150)
for _ in range(5): m.press('down')
m.press('a', after=200); show(m, 'creditos'); m.screen('v3_credits.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
