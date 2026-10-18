import emu3
from unicorn import UC_HOOK_CODE
logs = []
m = emu3.boot(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN', 'sd/sd.img', frames=60, log=logs.append)
loads = []
m.mu.hook_add(UC_HOOK_CODE, lambda mu, a, s, u: loads.append(1), begin=0xFF2F48, end=0xFF2F48)   # fatOpenFileByName (.ART)
def show(t):
    print('---', t); print('\n'.join(l for l in m.text().splitlines() if l.strip()))
m.press('a', after=200)                       # first-boot message
show('browser root'); m.screen('v3_root.png')
m.press('down'); m.press('a', after=150)      # ROMS
m.press('down'); m.press('a', after=150)      # USA
n0 = len(loads); m.run(60)
show('rest on 1st game (art lookups %d)' % (len(loads) - n0)); m.screen('v3_preview.png')
m.press('down', after=10); show('after down (art cleared?)')
n1 = len(loads)
for _ in range(3): m.press('down', hold=3, after=8)
print('quick taps -> lookups:', len(loads) - n1)
m.run(60); show('rest on another game'); m.screen('v3_preview2.png')
m.press('a', after=200); show('file menu (A)'); m.screen('v3_filemenu.png')
m.press('b', after=200); show('back')
print('stopped', m.stopped); print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
