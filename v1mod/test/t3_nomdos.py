import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
logs = []
m = emu3.boot(OS, 'sd/sdn.img', frames=60, log=logs.append)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down'); m.press('down'); m.press('a', after=200)
for _ in range(4): m.press('down')
m.press('a', after=300); print([l.strip() for l in m.text().splitlines() if l.strip()][:3])
m.press('c', after=200); m.press('a', after=200); print([l.strip() for l in m.text().splitlines() if l.strip()][:12])
m.press('down', after=40); m.press('a', after=200); print('still alive:', m.stopped)
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
