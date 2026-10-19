"""map VRAM / plane / palette use of the v3 OS across the main flows"""
import struct
import emu3
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
writes = {}
orig = emu3.emu.Machine.data
def data(self, w):
    if self.vcode & 0xF == 1:
        writes.setdefault(self.vaddr & 0xFC00, set()).add(self.vaddr)
    return orig(self, w)
emu3.MachineV3.data = data
cram_w = set()
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=print)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down'); m.press('down'); m.run(40); m.press('a', after=200)
for _ in range(3): m.press('down')
m.press('a', after=300); m.press('a', after=200); m.press('b', after=200)
m.press('c', after=200); m.press('down'); m.press('a', after=200); m.press('b', after=100)
for _ in range(5): m.press('down')
m.press('a', after=200); m.press('b', after=100)
print('VDP regs:', ' '.join(f'{i}:{v:02X}' for i, v in enumerate(m.regs[:24])))
runs = []
for k in sorted(writes):
    if runs and runs[-1][1] == k: runs[-1][1] = k + 0x400
    else: runs.append([k, k + 0x400])
print('VRAM written:', ', '.join(f'{a:04X}-{b - 1:04X}' for a, b in runs))
print('CRAM:', ' '.join(f'{c:03X}' for c in m.cram))
used = {}
for base in (0xC000, 0xD000, 0xE000):
    t = set()
    for i in range(0x800):
        e = struct.unpack_from('>H', m.vram, base + i * 2)[0]
        if e & 0x7FF: t.add((e >> 13) & 3)
    used[hex(base)] = sorted(t)
print('palettes used per table:', used)
