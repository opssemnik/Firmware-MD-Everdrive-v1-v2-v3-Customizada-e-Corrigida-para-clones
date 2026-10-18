import struct, sys
import emu
OS = r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\OS-V38-PTBR.BIN'
logs = []
def new(flash=None):
    m = emu.boot(OS, 'sd/sd.img', flash, log=lambda s: logs.append(s))
    return m
def show(m, t):
    print('---', t)
    print('\n'.join(l for l in m.text().splitlines() if l.strip()))
def lists(m):
    hdr = bytes(m.mu.mem_read(0x30200, 16)); out = {}
    if hdr[:4] != b'RGL1': return 'no lists'
    for l, off in ((0, 0x210), (1, 0x610)):
        n = struct.unpack('>H', hdr[6 + 2 * l:8 + 2 * l])[0]
        out[['recent', 'fav'][l]] = [bytes(m.mu.mem_read(0x30000 + off + i * 128 + 14, 114)).split(b'\0')[0].decode() for i in range(n)]
    out['theme'] = struct.unpack('>H', hdr[4:6])[0]
    out['settings'] = bytes(m.mu.mem_read(0x30000, 8)).hex()
    return out
def flash(m): return bytes(m.mu.mem_read(0x30000, 0x10000))

