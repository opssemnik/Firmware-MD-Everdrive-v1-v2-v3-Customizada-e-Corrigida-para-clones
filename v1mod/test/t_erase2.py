"""v1: ramEraseWait on its own - stack as inside ff5592 called by the game loader (size 512 KB),
flash busy for 120 frames; screenshots of the bar while it fills"""
import struct, re
import emu
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC
from PIL import Image
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
sym = {l.split()[2]: int(l.split()[0], 16) for l in open(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\v1mod\build\mod.sym') if len(l.split()) == 3}
state = {'until': None}
orig = emu.Machine.io_r
def io_r(self, mu, off, size, ud):
    if off in (0x3002, 0x3003) and state['until'] is not None and self.vbl < state['until']:
        return 1
    return orig(self, mu, off, size, ud)
emu.Machine.io_r = io_r
m = emu.boot(OS, 'sd/sd.img', None, log=print)
m.mu.mem_write(0xFFE306, bytes([5]))                       # status row
sp = 0xFFF000
# stack inside ff5592 at the wait: [jsr return][movem 12 bytes][ff5592 return = FF4D54][addr][size][wait]
frame = struct.pack('>IIIIIIII', 0xFFD000, 0, 0, 0, 0xFF4D54, 0x400000, 512, 1)
m.mu.mem_write(sp, frame)
m.mu.mem_write(0xFFD000, bytes.fromhex('60fe'))            # return lands on bra.s self
m.mu.reg_write(UC_M68K_REG_A7, sp)
m.mu.reg_write(UC_M68K_REG_PC, sym['ramEraseWait'])
state['until'] = m.vbl + 120
shots = []
for i in range(8):
    m.run(20)
    m.screen('e.png'); shots.append(Image.open('e.png').crop((0, 0, 640, 120)))
    print(i, 'vbl', m.vbl, 'pc', hex(m.mu.reg_read(UC_M68K_REG_PC)))
c = Image.new('RGB', (640, 120 * 8))
for i, im in enumerate(shots):
    c.paste(im, (0, i * 120))
c.save('erase_bar.png')
