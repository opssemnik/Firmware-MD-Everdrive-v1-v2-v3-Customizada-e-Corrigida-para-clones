import emu3
logs = []
m = emu3.boot(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN', 'sd/sd.img', frames=60, log=logs.append)
def show(t):
    print('---', t); print('\n'.join(l for l in m.text().splitlines() if l.strip()))
m.press('a', after=200)
m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.run(60); show('rest on 1st game'); m.screen('v3_preview.png')
m.press('a', after=200); show('file menu: Art Alive'); m.screen('v3_fm1.png')
m.press('right', after=250); show('RIGHT -> next game'); m.screen('v3_fm2.png')
m.press('right', after=250); m.press('left', after=250); show('RIGHT, LEFT')
m.press('b', after=250); show('B -> browser (cursor should be on Blockout)'); m.screen('v3_back.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
