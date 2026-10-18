import struct
import emu
from t_all_lib import *
low = [0x1000000]
def track(m):
    ram = bytes(m.mu.mem_read(0xFFEE00, 0x10000 - 0xEE00 - 0x10))
    i = next((k for k, b in enumerate(ram) if b != 0xA5), len(ram))
    low[0] = min(low[0], 0xFFEE00 + i)

# phase A again to get lists (favourite Columns, recent Blockout)
m = new()
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('a', after=120)
# A on NOTAS.TXT (6th) -> file menu without art / header / too small
for _ in range(5): m.press('down')
m.press('a', after=200); show(m, 'txt file menu')
for _ in range(3): m.press('down')
m.press('a', after=150); show(m, 'txt rom info'); m.press('b', after=60)
for _ in range(3): m.press('up')
m.press('a', after=150); show(m, 'txt load -> guard'); m.press('a', after=100)
track(m)
show(m, 'back in browser after guard')
# Só carregar on Columns (3rd): up x3 from NOTAS
for _ in range(3): m.press('up')
m.press('a', after=200); m.press('down'); m.press('a', after=900)
show(m, 'load only result'); m.screen('shot_loadonly.png'); print('stopped', m.stopped)
m.press('a', after=200); show(m, 'browser after load-only')
track(m)
m.press('b', after=200); m.press('b', after=200); m.press('b', after=200); show(m, 'back at main?')
F = flash(m); print('lists', lists(m))

# deleted file in recents
m = new(F)
rec0 = bytes(m.mu.mem_read(0x30210, 14)); cl, sz, sec, idx = struct.unpack('>IIIH', rec0)
m.sd[sec * 512 + idx * 32] = 0xE5
m.press('down'); m.press('down'); m.press('a', after=200); m.press('a', after=300)
show(m, 'recent with deleted file'); track(m)

# play last game
m = new(F); m.press('a', after=100); print('play last ->', m.stopped)

# cheats menu in/out
m = new(F); [m.press('down') for _ in range(6)]; m.press('a', after=300); show(m, 'cheats'); m.screen('shot_cheats.png')
m.press('b', after=300); show(m, 'after cheats B'); track(m)

# toolbox -> SRAM tool browser: A on a file must be stock (no PT-BR file menu)
m = new(F); [m.press('down') for _ in range(7)]; m.press('a', after=200); m.press('a', after=200)
show(m, 'sram tool'); m.screen('shot_sramtool.png'); track(m)

# signature broken (simulates a half-written OS update): menus fall back, toolbox loops
m = new(F)
m.mu.mem_write(0x1FFF8, b'\xff' * 8)
[m.press('down') for _ in range(7)]; m.press('a', after=200); show(m, 'toolbox (no signature)')
m.press('b', after=300); show(m, 'after B (should stay in toolbox)')
print('stack low-water mark: %06X' % low[0])
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
