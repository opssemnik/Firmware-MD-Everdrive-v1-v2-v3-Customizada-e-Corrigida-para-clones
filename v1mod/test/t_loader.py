"""v1 loader: installs/updates the extension from /EDMD/V1EXT.BIN at boot, stock OS without one"""
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
EXT = open(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\V1EXT.BIN', 'rb').read()
OLD = EXT[:8] + b'\x12\x34\x56\x78' + EXT[12:]
orig = emu.Machine.__init__
PRE = [None]
def init(self, *a, **k):
    orig(self, *a, **k)
    if PRE[0]:
        self.mu.mem_write(0x40000, PRE[0])
emu.Machine.__init__ = init
for name, sd, pre, hold in (('first boot', 'sd/sd.img', None, None),
                            ('same one installed', 'sd/sd.img', EXT, None),
                            ('older one installed', 'sd/sd.img', OLD, None),
                            ('no V1EXT.BIN, none installed', 'sd/sdx.img', None, None),
                            ('no V1EXT.BIN, installed', 'sd/sdx.img', EXT, None),
                            ('V1EXT.BIN for another loader (abi 9)', 'sd/sdo.img', None, None),
                            ('B held at power on', 'sd/sd.img', EXT, 'b')):
    logs = []
    PRE[0] = pre
    m = emu.Machine(OS, sd, None, logs.append)
    m.mu.reg_write(emu.UC_M68K_REG_SR, 0x2700)
    m.mu.reg_write(emu.UC_M68K_REG_A7, 0x01000000)
    m.mu.reg_write(emu.UC_M68K_REG_PC, 0xFF127E)
    if hold:
        m.pad = emu.BTN[hold]
    m.run(120)
    m.pad = 0
    m.run(30)
    t = [l.strip() for l in m.text().splitlines() if l.strip()]
    w = sum('flash write' in l and '04' in l.split('flash write')[1][:3] for l in logs)
    print(f'{name:38s} ext={bytes(m.mu.mem_read(0x40000, 12)).hex()} ext writes={w:2d} menu: {t[1] if len(t) > 1 else t} | {t[-2] if len(t) > 2 else ""}')
    for l in logs:
        if l.startswith('!!'):
            print('   ', l)
