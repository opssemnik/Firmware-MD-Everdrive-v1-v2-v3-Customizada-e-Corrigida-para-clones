"""Maddrugamers theme (sd/sdm.img): banner + wallpaper + the banner's theme colours, v1 and v3"""
import emu, emu3
V1 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
V3 = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
logs = []
m = emu.boot(V1, 'sd/sdm.img', None, log=logs.append)
m.screen('tema_v1_menu.png')
print('v1 menu:', [l.strip() for l in m.text().splitlines() if 'Tema' in l], 'pal0:', [hex(c) for c in m.cram[0:3]], hex(m.cram[15]), 'pal1.15', hex(m.cram[31]), 'pal2.15', hex(m.cram[47]))
[m.press('down') for _ in range(8)]; m.press('a', after=200)
print('v1 theme item ->', [l.strip() for l in m.text().splitlines() if l.strip()][1:3])
m.press('a', after=200)
m.press('up'); [m.press('up') for _ in range(6)]; m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.screen('tema_v1_lista.png')
m3 = emu3.boot(V3, 'sd/sdm.img', frames=60, log=logs.append)
m3.press('a', after=200); m3.press('down'); m3.press('a', after=150); m3.press('down'); m3.press('a', after=150)
m3.screen('tema_v3_lista.png')
print('v3 pal0:', [hex(c) for c in m3.cram[0:3]], 'pal1.15', hex(m3.cram[31]))
m3.press('c', after=200); m3.screen('tema_v3_menu.png')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
