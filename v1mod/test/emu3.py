"""
EverDrive-MD v3 harness: runs MDOS (first 32 KB of the OS file, copied to RAM 0xFF0000) on the
Unicorn 68000 core. Reuses the VDP/screen model of emu.py; the SD card is emulated at the OS
disk layer (ff11da read / ff12a0 write), the pad at the I/O port 0xA10003.
"""
import struct
from pathlib import Path

from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_WRITE, \
    UC_MODE_BIG_ENDIAN, Uc
from unicorn.m68k_const import UC_CPU_M68K_M68000, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_SR

import emu


class MachineV3(emu.Machine):
    def __init__(self, os_path, sd_path, log=print):
        self.log = log
        self.mu = mu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_CPU_M68K_M68000)
        mu.mem_map(0x000000, 0x80000)                   # cart (SRAM lives at 0x100000+)
        mu.mmio_map(0x080000, 0x10000, self.ed_r, None, self.ed_w, None)   # EverDrive v3 registers
        mu.mem_map(0x090000, 0x800000 - 0x090000)
        mu.mem_map(0xFF0000, 0x10000)
        mu.mmio_map(0xA10000, 0x10000, self.io_r, None, self.io_w, None)
        mu.mmio_map(0xC00000, 0x10000, self.vdp_r, None, self.vdp_w, None)
        osimg = Path(os_path).read_bytes()
        mu.mem_write(0xFF0000, osimg[:0x8000])
        # Fake boot-ROM BIOS block at cart 0x200 (the real one lives in the cart's boot ROM):
        # +0 font ptr, +4 header data ptr (copied to 0xFF0020), +0xA its length, +0xC.. service calls.
        font = (emu.MG / 'OS-V38.BIN').read_bytes()[0x17C:0x117C]   # same Krikzz 8x8 font, chars 0x20..
        mu.mem_write(0x1000, font)
        mu.mem_write(0x400, osimg[0x20:0x40])
        mu.mem_write(0x300, bytes.fromhex('4e75' '70014e75'))          # rts ; moveq #1,d0 ; rts
        mu.mem_write(0x200, struct.pack('>IIHHIIII', 0x1000, 0x400, 0, 0x20, 0x300, 0x302, 0x300, 0x300))
        mu.mem_write(0xFFE000, bytes([0xA5]) * 0x1FF0)  # stack low-water pattern
        self.sd = bytearray(Path(sd_path).read_bytes())
        self.vram = bytearray(0x10000)
        self.cram = [0] * 64
        self.regs = [0] * 32
        self.vaddr = self.vcode = 0
        self.pending = None
        self.vbl = 0
        self.vbl_pending = False
        self.pad = 0
        self.th = 0x40
        self.stopped = None
        self.calls = {}
        self.align_errors = []
        for addr, fn in {0xFF11DA: self.disk_read, 0xFF12A0: self.disk_write, 0xFF1162: self.ret_void,
                         0xFF118A: self.ret0, 0xFF567E: self.start_game}.items():
            mu.hook_add(UC_HOOK_CODE, self._wrap(fn), begin=addr, end=addr)
        mu.hook_add(UC_HOOK_MEM_UNMAPPED, self.unmapped)
        mu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.align, begin=0xFF0000, end=0xFFFFFF)

    def ret_void(self):
        return 0

    def disk_read(self):
        lba, dst, cnt, mode = self.arg(0), self.arg(1), self.arg(2) & 0xFFFF, self.arg(3) & 0xFF
        if dst & 1:
            self.align(self.mu, 0, dst, 2, 0, None)
            return 0
        data = bytes(self.sd[lba * 512:(lba + cnt) * 512])
        if mode == 1 or dst >= 0xFF0000:
            self.mu.mem_write(dst & 0xFFFFFF, data)
        else:                                            # into cart memory (game load)
            self.mu.mem_write(dst & 0x7FFFFF, data)
        return 0

    def disk_write(self):
        lba, src, cnt = self.arg(0), self.arg(1), self.arg(2) & 0xFFFF
        self.sd[lba * 512:(lba + cnt) * 512] = self.mu.mem_read(src & 0xFFFFFF, cnt * 512)
        return 0

    def ed_r(self, mu, off, size, ud):
        return 0                                         # MCU idle / ready

    def ed_w(self, mu, off, size, value, ud):
        pass

    def io_r(self, mu, off, size, ud):
        if off in (2, 3):                                # pad 1 data port
            if self.th:
                return 0x40 | (~self.pad & 0x3F)
            return (~(self.pad >> 2) & 0x30) | 0x0C     # A, Start (+ left/right low = 3-button id)
        return 0

    def io_w(self, mu, off, size, value, ud):
        if off in (2, 3):
            self.th = value & 0x40

    def run(self, frames, insns_per_frame=20000):
        pc = self.mu.reg_read(UC_M68K_REG_PC)
        for _ in range(frames):
            if self.stopped:
                return
            self.vbl_pending = True
            self.vbl = (self.vbl + 1) & 0xFFFF
            try:
                self.mu.emu_start(pc, 0xFFFFFFFF, count=insns_per_frame)
            except Exception as e:
                self.stopped = f'CPU error {e} at pc={self.mu.reg_read(UC_M68K_REG_PC):08X}'
                self.log('!! ' + self.stopped)
                return
            pc = self.mu.reg_read(UC_M68K_REG_PC)

    def text(self):
        """both name tables merged (0xC000 over 0xE000), tiles shown as their character"""
        lines = []
        for cy in range(28):
            s = ''
            for cx in range(40):
                ch = ' '
                for base in (0xE000, 0xC000):
                    t = struct.unpack_from('>H', self.vram, base + (cy * 64 + cx) * 2)[0] & 0x7FF
                    if 0x20 < t < 0x7F:
                        ch = chr(t)
                    elif t >= 0x94 and t < 0x100:
                        ch = '#'
                    elif 0x80 <= t < 0x94:
                        ch = '*'
                s += ch
            lines.append(s.rstrip())
        return '\n'.join(lines)


def boot(os_path, sd_path, log=print, frames=200):
    m = MachineV3(os_path, sd_path, log)
    m.mu.reg_write(UC_M68K_REG_SR, 0x2700)
    m.mu.reg_write(UC_M68K_REG_A7, 0x01000000)
    m.mu.reg_write(UC_M68K_REG_PC, 0xFF5430)
    m.run(frames)
    return m
