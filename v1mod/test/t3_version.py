import emu3
logs = []
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=200)
m.press('c', after=200)
for _ in range(5): m.press('down')
m.press('a', after=200)
print('\n'.join(l for l in m.text().splitlines() if l.strip())); m.screen('v3_infosistema.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
