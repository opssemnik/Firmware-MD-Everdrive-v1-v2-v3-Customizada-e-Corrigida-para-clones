"""
Minimal EverDrive-MD v1 harness: runs the OS (RAM image + flash image) on Unicorn's 68000 core,
with the VDP, pad, cart registers, flash and SD card emulated at the level the OS uses them.
Screens are rendered from VRAM/CRAM to PNG.
"""
import struct
import sys
from pathlib import Path

from PIL import Image
from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED, UC_MODE_BIG_ENDIAN, Uc, UcError
from unicorn.m68k_const import UC_CPU_M68K_M68000, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR

MG = Path(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis')

BTN = {'up': 1, 'down': 2, 'left': 4, 'right': 8, 'b': 0x10, 'c': 0x20, 'a': 0x40, 'start': 0x80}


class Machine:
    def __init__(self, os_path, sd_path, flash_init=None, log=print):
        self.log = log
        self.mu = mu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_CPU_M68K_M68000)
        mu.mem_map(0x000000, 0x800000)                  # cart (boot/OS/settings/games)
        mu.mem_map(0xFF0000, 0x10000)                   # work RAM
        mu.mem_map(0xA00000, 0x10000)                   # Z80 RAM (counter faked per frame in run())
        mu.mmio_map(0xA10000, 0x10000, self.io_r, None, self.io_w, None)
        mu.mmio_map(0xC00000, 0x10000, self.vdp_r, None, self.vdp_w, None)
        osimg = Path(os_path).read_bytes()
        boot = (MG / 'BOOT-V38.BIN').read_bytes()
        mu.mem_write(0, boot)
        mu.mem_write(0x10000, osimg)
        mu.mem_write(0x30000, flash_init if flash_init else b'\xff' * 0x10000)
        mu.mem_write(0xFF0000, osimg)
        mu.mem_write(0xFFEE00, bytes([0xA5]) * (0x10000 - 0xEE00 - 0x10))   # stack low-water pattern
        self.sd = bytearray(Path(sd_path).read_bytes())
        self.vram = bytearray(0x10000)
        self.cram = [0] * 64
        self.vsram = [0] * 64
        self.regs = [0] * 32
        self.vaddr = 0
        self.vcode = 0
        self.pending = None
        self.vbl = 0
        self.vbl_pending = False
        self.pad = 0
        self.th = 0x40
        self.stopped = None
        self.calls = {}
        for addr, fn in {0xFF175A: self.sd_init, 0xFF182C: self.sd_read, 0xFF1912: self.sd_write,
                         0xFF1866: self.sd_write1, 0xFF5592: self.flash_erase, 0xFF57D0: self.flash_write,
                         0xFF7FEE: self.ret0, 0xFF8080: self.ret0, 0xFF4F32: self.start_game}.items():
            mu.hook_add(UC_HOOK_CODE, self._wrap(fn), begin=addr, end=addr)
        mu.hook_add(UC_HOOK_MEM_UNMAPPED, self.unmapped)
        # a real 68000 raises an address error for word/long accesses at odd addresses
        for lo, hi in ((0x000000, 0x7FFFFF), (0xFF0000, 0xFFFFFF)):
            mu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.align, begin=lo, end=hi)
        self.align_errors = []

    # ------------------------------------------------------------ helpers
    def u32(self, a):
        return struct.unpack('>I', self.mu.mem_read(a, 4))[0]

    def arg(self, n):
        return self.u32(self.mu.reg_read(UC_M68K_REG_A7) + 4 + 4 * n)

    def _wrap(self, fn):
        def cb(mu, addr, size, ud):
            self.calls[fn.__name__] = self.calls.get(fn.__name__, 0) + 1
            r = fn()
            if r is None:
                return
            sp = mu.reg_read(UC_M68K_REG_A7)
            mu.reg_write(UC_M68K_REG_D0, r)
            mu.reg_write(UC_M68K_REG_PC, self.u32(sp))
            mu.reg_write(UC_M68K_REG_A7, sp + 4)
        return cb

    def align(self, mu, access, addr, size, value, ud):
        if size > 1 and addr & 1:
            pc = mu.reg_read(UC_M68K_REG_PC)
            msg = f'!! ADDRESS ERROR: {size}-byte access at odd address {addr:06X} pc={pc:06X}'
            if len(self.align_errors) < 5:
                self.log(msg)
            self.align_errors.append(msg)
            self.stopped = msg
            mu.emu_stop()

    def unmapped(self, mu, access, addr, size, value, ud):
        self.log(f'!! unmapped access {access} at {addr:08X} pc={mu.reg_read(UC_M68K_REG_PC):08X}')
        return False

    # ------------------------------------------------------------ stubs
    def ret0(self):
        return 0

    def sd_init(self):
        return 0

    def sd_read(self):
        lba, dst, cnt = self.arg(0), self.arg(1), self.arg(2) & 0xFFFF
        if dst & 1:     # the real SPI read loop stores words
            self.align(self.mu, 0, dst, 2, 0, None)
            return 0
        self.mu.mem_write(dst & 0xFFFFFF, bytes(self.sd[lba * 512:(lba + cnt) * 512]))
        return 0

    def sd_write(self):
        lba, src, cnt = self.arg(0), self.arg(1), self.arg(2) & 0xFFFF
        self.sd[lba * 512:(lba + cnt) * 512] = self.mu.mem_read(src & 0xFFFFFF, cnt * 512)
        return 0

    def sd_write1(self):
        lba, src = self.arg(0), self.arg(1)
        self.sd[lba * 512:(lba + 1) * 512] = self.mu.mem_read(src & 0xFFFFFF, 512)
        return 0

    def flash_erase(self):
        addr, size = self.arg(0), self.arg(1) & 0xFFFF
        if size & 0x7F:
            size += 0x80
        if not self.mu.mem_read(0xFFCC88, 1)[0]:
            size <<= 1
        n = (size >> 7) << 3
        self.log(f'   flash erase {addr:06X} x{n} * 0x2000')
        self.mu.mem_write(addr, b'\xff' * (n * 0x2000))
        return 0

    def flash_write(self):
        src, addr, n = self.arg(0), self.arg(1), self.arg(2) & 0xFF
        self.log(f'   flash write {addr:06X} <- {src:06X} {n} sectors')
        self.mu.mem_write(addr, bytes(self.mu.mem_read(src & 0xFFFFFF, n * 512)))
        return 0

    def start_game(self):
        self.stopped = f'startGame({self.arg(0)})'
        self.mu.emu_stop()
        return None

    # ------------------------------------------------------------ I/O
    def io_r(self, mu, off, size, ud):
        if off in (0x3002, 0x3003):
            return 3                 # cart status: SPI/flash ready
        if off in (0x3000, 0x3001):
            return 0xFF
        if off == 3:                    # pad 1 data port, active low: TH=1 -> C B R L D U, TH=0 -> START A
            p = self.pad
            v = (p & 0x3F) if self.th else ((p >> 2) & 0x30)
            return (~v & 0x3F) | (0x40 if self.th else 0)
        return 0

    def io_w(self, mu, off, size, value, ud):
        if off == 3:
            self.th = value & 0x40

    # ------------------------------------------------------------ VDP
    def vdp_r(self, mu, off, size, ud):
        if off in (4, 5, 6, 7):
            v = 0x3600 | (8 if self.vbl_pending else 0)     # vblank seen once per frame
            self.vbl_pending = False
            return v >> 8 if off in (4, 6) and size == 1 else v
        if off in (8, 9):
            return (self.mu.reg_read(UC_M68K_REG_PC) * 7 + self.vbl) & 0xFFFF
        if off in (0, 1, 2, 3):
            if self.vcode & 1:          # reading the data port while set up for a write hangs the real 68000
                self.log(f'!! VDP data port read in write mode (code {self.vcode:02X}) at pc={self.mu.reg_read(UC_M68K_REG_PC):06X}')
            v = struct.unpack_from('>H', self.vram, self.vaddr & 0xFFFE)[0]
            self.vaddr = (self.vaddr + self.regs[15]) & 0xFFFF
            return v
        return 0

    def ctrl(self, w):
        if self.pending is not None:
            first = self.pending
            self.pending = None
            self.vcode = ((first >> 14) & 3) | ((w >> 2) & 0x3C)
            self.vaddr = (first & 0x3FFF) | ((w & 3) << 14)
            if self.vcode & 0x20:
                self.log(f'!! VDP DMA requested code={self.vcode:02X}')
        elif (w & 0xC000) == 0x8000:
            self.regs[(w >> 8) & 0x1F] = w & 0xFF
        else:
            self.pending = w

    def data(self, w):
        code = self.vcode & 0xF
        if code == 1:
            struct.pack_into('>H', self.vram, self.vaddr & 0xFFFE, w)
        elif code == 3:
            self.cram[(self.vaddr >> 1) & 63] = w
        elif code == 5:
            self.vsram[(self.vaddr >> 1) & 63] = w
        self.vaddr = (self.vaddr + self.regs[15]) & 0xFFFF

    def vdp_w(self, mu, off, size, value, ud):
        words = [value >> 16, value & 0xFFFF] if size == 4 else [value]
        for w in words:
            (self.ctrl if off in (4, 6) else self.data)(w & 0xFFFF)

    # ------------------------------------------------------------ run / screen
    def run(self, frames, insns_per_frame=20000):
        pc = self.mu.reg_read(UC_M68K_REG_PC)
        for _ in range(frames):
            if self.stopped:
                return
            self.mu.mem_write(0xFFE30C, struct.pack('>H', self.pad))
            cnt = self.u32(0xFFE308) + 1
            self.mu.mem_write(0xFFE308, struct.pack('>I', cnt))
            self.vbl_pending = True
            self.vbl = (self.vbl + 1) & 0xFFFF
            if self.mu.mem_read(0xA00000, 1)[0] == 0xF3:            # diagnostics Z80 stopwatch loaded
                z = struct.unpack('<I', self.mu.mem_read(0xA01F00, 4))[0] + 63920 // 60
                self.mu.mem_write(0xA01F00, struct.pack('<I', z))
            try:
                self.mu.emu_start(pc, 0xFFFFFFFF, count=insns_per_frame)
            except UcError as e:
                self.stopped = f'CPU error {e} at pc={self.mu.reg_read(UC_M68K_REG_PC):08X}'
                self.log('!! ' + self.stopped)
                return
            pc = self.mu.reg_read(UC_M68K_REG_PC)

    def press(self, *names, hold=4, after=30):
        self.pad = sum(BTN[n] for n in names)
        self.run(hold)
        self.pad = 0
        self.run(after)

    def color(self, c):
        return (((c >> 1) & 7) * 36, ((c >> 5) & 7) * 36, ((c >> 9) & 7) * 36)

    def screen(self, path, plane_b=True):
        img = Image.new('RGB', (320, 224), self.color(self.cram[0]))
        px = img.load()
        planes = ([0xE000] if plane_b else []) + [0xC000]
        for base in planes:
            vs = (self.vsram[1 if base == 0xE000 else 0] >> 3) & 63
            for cy in range(28):
                for cx in range(40):
                    ent = struct.unpack_from('>H', self.vram, base + (((cy + vs) & 63) * 64 + cx) * 2)[0]
                    tile, pal = ent & 0x7FF, (ent >> 13) & 3
                    hf, vf = ent & 0x800, ent & 0x1000
                    for r in range(8):
                        row = self.vram[tile * 32 + r * 4: tile * 32 + r * 4 + 4]
                        for p in range(8):
                            v = (row[p >> 1] >> (0 if p & 1 else 4)) & 15
                            if v:
                                x = cx * 8 + (7 - p if hf else p)
                                y = cy * 8 + (7 - r if vf else r)
                                px[x, y] = self.color(self.cram[pal * 16 + v])
        img.resize((640, 448), Image.NEAREST).save(path)

    def text(self, base=0xC000):
        """plane A as text (font chars only)"""
        lines = []
        for cy in range(28):
            s = ''
            for cx in range(40):
                t = struct.unpack_from('>H', self.vram, base + (cy * 64 + cx) * 2)[0] & 0x7FF
                c = t - 0x4E0
                s += chr(c) if 0x20 <= c < 0x7F else ('*' if 0xA0 <= c < 0xD0 else ' ')
            lines.append(s.rstrip())
        return '\n'.join(l for l in lines)


def boot(os_path, sd_path, flash_init=None, log=print):
    m = Machine(os_path, sd_path, flash_init, log)
    m.mu.reg_write(UC_M68K_REG_SR, 0x2700)
    m.mu.reg_write(UC_M68K_REG_A7, 0x01000000)
    m.mu.reg_write(UC_M68K_REG_PC, 0xFF127E)
    m.run(120)
    return m
