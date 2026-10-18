from t_all_lib import *
import emu
OSD = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR-DIAG.BIN'
m = emu.boot(OSD, 'sd/sd.img', None, log=logs.append)
show(m, 'main menu'); m.screen('diag_main.png')
for _ in range(9): m.press('down')
m.press('a', after=150); show(m, 'diagnostico'); m.screen('diag_chip.png')
m.press('a', after=100); show(m, 'tempos (vazio)'); m.press('a', after=60); m.press('b', after=100)
m.press('up'); [m.press('up') for _ in range(7)]          # back to "Selecionar jogo"
m.press('a', after=120); m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('start', after=900)
show(m, 'tempos apos carregar'); m.screen('diag_times.png')
m.press('a', after=100); print('stopped:', m.stopped)
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
