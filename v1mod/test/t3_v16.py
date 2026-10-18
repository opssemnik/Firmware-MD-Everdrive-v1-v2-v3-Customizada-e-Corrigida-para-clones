"""v3 1.6: page counter at the bottom, full-screen file menu, recents only take ROMs + Limpar recentes"""
import struct
import emu3
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_D2, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR
logs = []
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
def show(m, t):
    print('---', t); print('\n'.join(l for l in m.text().splitlines() if l.strip()))

# isRomRec on its own
m = emu3.boot(OS, 'sd/sd.img', frames=5, log=logs.append)
syms = {}
import re
isrom = None
code = open(OS, 'rb').read()[:0x8000]
i = code.find(bytes.fromhex('41e8000e7200101867'))        # lea $a(a0),a0; moveq #0,d1; move.b (a0)+,d0; beq.s
isrom = 0xFF0000 + i
for name, want in [('Sonic.bin', 1), ('a.MD', 1), ('x.GEN', 1), ('y.smd', 1), ('z.sms', 1), ('k.32X', 1),
                   ('Game (Rev 1)', 1), ('bkp.rar', 0), ('NOTAS.TXT', 0), ('a.b.bin', 1), ('a.bin.zip', 0),
                   ('x.bins', 0), ('.bin', 1), ('a.b', 0)]:
    m.mu.mem_write(0xFFD000, bytes(14) + name.encode() + b'\0')
    m.mu.mem_write(0xFFD800, bytes.fromhex('57c24e71'))     # return address -> seq d2 (Z)
    m.mu.reg_write(UC_M68K_REG_A0, 0xFFD000)
    m.mu.reg_write(UC_M68K_REG_A7, 0xFFFF00)
    m.mu.mem_write(0xFFFF00, struct.pack('>I', 0xFFD800))
    m.mu.emu_start(isrom, 0xFFD802, count=2000)
    z = m.mu.reg_read(UC_M68K_REG_D2) & 1
    print(f'{name:14s} rom={z}', 'OK' if z == want else '<<< WRONG')

# browser + full-screen file menu
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=logs.append)
m.press('a', after=200); show(m, 'root (page counter at the bottom)'); m.screen('v3_root16.png')
m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down'); m.press('down'); m.run(40)
m.press('a', after=200); show(m, 'file menu (full screen)'); m.screen('v3_filemenu16.png')
m.press('right', after=200); show(m, 'RIGHT -> next game')
m.press('b', after=250); show(m, 'back in the browser')
# load NOTAS.TXT (not a ROM) and a ROM, recents keep only the ROM
sram = None
for k in range(8):
    m.press('down')
show(m, 'cursor at the end')
m.press('a', after=200); show(m, 'file menu on the last entry')
m.press('a', after=900); print('load ->', m.stopped)
sram = bytes(m.mu.mem_read(0x100000, 0x100000))
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
