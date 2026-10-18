import struct, emu
logs=[]
m = emu.boot(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN', 'sd/sd.img', log=logs.append)
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('a', after=120); m.press('down', after=60)
# force the vblank counter to stay a multiple of 4 while the game loads
orig = m.run
def run4(frames, insns_per_frame=20000):
    for _ in range(frames):
        m.mu.mem_write(0xFFE308, struct.pack('>I', 3))   # run() adds 1 -> 4
        orig(1, insns_per_frame)
m.run = run4
m.press('start', after=3000)
print('mine ->', m.stopped)
print('\n'.join(l for l in logs if l.startswith('!!')))

from unicorn import m68k_const as K
print({n: hex(m.mu.reg_read(getattr(K, 'UC_M68K_REG_' + n))) for n in ['D0','D1','D2','D3','A0','A1','A2','A3','A7','PC']})
