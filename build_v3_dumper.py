import struct
import hashlib
from capstone import *

# 8x8 1bpp ASCII font for 0x20..0x5F (64 chars, 8 bytes per char = 512 bytes)
FONT_1BPP = {
    ' ': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '!': [0x18,0x18,0x18,0x18,0x18,0x00,0x18,0x00],
    '"': [0x66,0x66,0x24,0x00,0x00,0x00,0x00,0x00],
    '#': [0x6c,0xfe,0x6c,0x6c,0xfe,0x6c,0x00,0x00],
    '$': [0x18,0x7e,0x58,0x7c,0x1a,0x7c,0x18,0x00],
    '%': [0x62,0x64,0x08,0x10,0x26,0x46,0x00,0x00],
    '&': [0x38,0x6c,0x38,0x76,0xdc,0xcc,0x76,0x00],
    "'": [0x18,0x18,0x30,0x00,0x00,0x00,0x00,0x00],
    '(': [0x0c,0x18,0x30,0x30,0x30,0x18,0x0c,0x00],
    ')': [0x30,0x18,0x0c,0x0c,0x0c,0x18,0x30,0x00],
    '*': [0x00,0x66,0x3c,0xff,0x3c,0x66,0x00,0x00],
    '+': [0x00,0x18,0x18,0x7e,0x18,0x18,0x00,0x00],
    ',': [0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x30],
    '-': [0x00,0x00,0x00,0x7e,0x00,0x00,0x00,0x00],
    '.': [0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00],
    '/': [0x06,0x0c,0x18,0x30,0x60,0xc0,0x00,0x00],
    '0': [0x7c,0xc6,0xce,0xd6,0xe6,0xc6,0x7c,0x00],
    '1': [0x18,0x38,0x18,0x18,0x18,0x18,0x7e,0x00],
    '2': [0x7c,0xc6,0x06,0x3c,0x60,0xc6,0xfe,0x00],
    '3': [0x7c,0xc6,0x06,0x3c,0x06,0xc6,0x7c,0x00],
    '4': [0x1c,0x3c,0x6c,0xcc,0xfe,0x0c,0x1e,0x00],
    '5': [0xfe,0xc0,0xfc,0x06,0x06,0xc6,0x7c,0x00],
    '6': [0x38,0x60,0xc0,0xfc,0xc6,0xc6,0x7c,0x00],
    '7': [0xfe,0xc6,0x0c,0x18,0x30,0x30,0x30,0x00],
    '8': [0x7c,0xc6,0xc6,0x7c,0xc6,0xc6,0x7c,0x00],
    '9': [0x7c,0xc6,0xc6,0x7e,0x06,0x0c,0x78,0x00],
    ':': [0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00],
    ';': [0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x30],
    '<': [0x0c,0x18,0x30,0x60,0x30,0x18,0x0c,0x00],
    '=': [0x00,0x00,0x7e,0x00,0x7e,0x00,0x00,0x00],
    '>': [0x30,0x18,0x0c,0x06,0x0c,0x18,0x30,0x00],
    '?': [0x7c,0xc6,0x0c,0x18,0x18,0x00,0x18,0x00],
    '@': [0x7c,0xc6,0xde,0xde,0xde,0xc0,0x7c,0x00],
    'A': [0x38,0x6c,0xc6,0xc6,0xfe,0xc6,0xc6,0x00],
    'B': [0xfc,0x66,0x66,0x7c,0x66,0x66,0xfc,0x00],
    'C': [0x3c,0x66,0xc0,0xc0,0xc0,0x66,0x3c,0x00],
    'D': [0xf8,0x6c,0x66,0x66,0x66,0x6c,0xf8,0x00],
    'E': [0xfe,0x62,0x68,0x78,0x68,0x62,0xfe,0x00],
    'F': [0xfe,0x62,0x68,0x78,0x68,0x60,0xf0,0x00],
    'G': [0x3c,0x66,0xc0,0xc0,0xce,0x66,0x3e,0x00],
    'H': [0xc6,0xc6,0xc6,0xfe,0xc6,0xc6,0xc6,0x00],
    'I': [0x3c,0x18,0x18,0x18,0x18,0x18,0x3c,0x00],
    'J': [0x1e,0x0c,0x0c,0x0c,0xcc,0xcc,0x78,0x00],
    'K': [0xe6,0x66,0x6c,0x78,0x6c,0x66,0xe6,0x00],
    'L': [0xf0,0x60,0x60,0x60,0x62,0x66,0xfe,0x00],
    'M': [0xc6,0xee,0xfe,0xfe,0xd6,0xc6,0xc6,0x00],
    'N': [0xc6,0xe6,0xf6,0xde,0xce,0xc6,0xc6,0x00],
    'O': [0x7c,0xc6,0xc6,0xc6,0xc6,0xc6,0x7c,0x00],
    'P': [0xfc,0x66,0x66,0x7c,0x60,0x60,0xf0,0x00],
    'Q': [0x7c,0xc6,0xc6,0xc6,0xd6,0xde,0x7c,0x06],
    'R': [0xfc,0x66,0x66,0x7c,0x6c,0x66,0xe6,0x00],
    'S': [0x7c,0xc6,0x60,0x38,0x0c,0xc6,0x7c,0x00],
    'T': [0x7e,0x5a,0x18,0x18,0x18,0x18,0x3c,0x00],
    'U': [0xc6,0xc6,0xc6,0xc6,0xc6,0xc6,0x7c,0x00],
    'V': [0xc6,0xc6,0xc6,0xc6,0xc6,0x6c,0x38,0x00],
    'W': [0xc6,0xc6,0xc6,0xd6,0xfe,0xee,0xc6,0x00],
    'X': [0xc6,0xc6,0x6c,0x38,0x6c,0xc6,0xc6,0x00],
    'Y': [0x66,0x66,0x66,0x3c,0x18,0x18,0x3c,0x00],
    'Z': [0xfe,0xc6,0x8c,0x18,0x32,0x66,0xfe,0x00],
    '[': [0x3c,0x30,0x30,0x30,0x30,0x30,0x3c,0x00],
    '\\':[0xc0,0x60,0x30,0x18,0x0c,0x06,0x00,0x00],
    ']': [0x3c,0x0c,0x0c,0x0c,0x0c,0x0c,0x3c,0x00],
    '^': [0x10,0x38,0x6c,0xc6,0x00,0x00,0x00,0x00],
    '_': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xff],
}


class Asm68k:
    def __init__(self, base_addr):
        self.base = base_addr
        self.buf = bytearray()
        self.labels = {}
        self.fixups = []

    @property
    def pc(self):
        return self.base + len(self.buf)

    def label(self, name):
        if len(self.buf) % 2 != 0:
            self.buf.append(0)
        self.labels[name] = self.pc

    def emit(self, *words):
        for w in words:
            self.buf.extend(struct.pack('>H', w & 0xffff))

    def emit_b(self, data):
        self.buf.extend(data)
        if len(self.buf) % 2 != 0:
            self.buf.append(0)

    def emit_str(self, s):
        self.emit_b(s.encode('ascii') + b'\x00')

    def bsr_w(self, target_label):
        self.emit(0x6100, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def bra_w(self, target_label):
        self.emit(0x6000, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def beq_w(self, target_label):
        self.emit(0x6700, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def bne_w(self, target_label):
        self.emit(0x6600, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def bcs_w(self, target_label):
        self.emit(0x6500, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def bcc_w(self, target_label):
        self.emit(0x6400, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def dbra(self, dreg, target_label):
        self.emit(0x51c8 | dreg, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def lea_abs(self, areg, target_label):
        self.emit(0x41f9 | (areg << 9), 0x0000, 0x0000)
        self.fixups.append((len(self.buf) - 4, target_label, 'abs32'))

    def resolve(self):
        for off, name, kind in self.fixups:
            target = self.labels[name]
            if kind == 'w16':
                disp = target - (self.base + off)
                assert -32768 <= disp <= 32767, f"Disp out of range for {name}: {disp}"
                struct.pack_into('>h', self.buf, off, disp)
            elif kind == 'abs32':
                struct.pack_into('>I', self.buf, off, target)


def build_rom():
    rom = bytearray(65536)

    # Embed MDOS.patched.BIN (first 32 KB: 0x0000..0x7FFF) at ROM 0x8000..0xFFFF
    # so the ROM can perform an instant byte-for-byte comparison on screen!
    with open('mega-genesis/MDOS.patched.BIN', 'rb') as f:
        patched_32k = f.read(0x8000)
    rom[0x8000:0x10000] = patched_32k

    # 1. 68000 Vector Table (0x0000..0x00FF)
    struct.pack_into('>II', rom, 0, 0x00FFF600, 0x00000200)
    for v in range(2, 64):
        struct.pack_into('>I', rom, v * 4, 0x000002EE)

    # 2. Sega Mega Drive Header (0x0100..0x01FF) with Standard SRAM Header
    hdr = bytearray(b' ' * 0x100)
    hdr[0x00:0x10] = b'SEGA EVERDRIVE  '
    hdr[0x10:0x20] = b'(C)KRIKZZ 2026  '
    title = b'EVERDRIVE-MD V3 OS DUMPER'.ljust(48, b' ')
    hdr[0x20:0x50] = title
    hdr[0x50:0x80] = title
    hdr[0x80:0x8E] = b'GM 00000003-01'
    hdr[0x90:0xA0] = b'J               '
    struct.pack_into('>IIII', hdr, 0xA0, 0x00000000, 0x0000FFFF, 0x00FF0000, 0x00FFFFFF)
    # Standard Mega Drive SRAM metadata at 0x1B0..0x1BB
    hdr[0xB0:0xB2] = b'RA'
    struct.pack_into('>HII', hdr, 0xB2, 0xF820, 0x00200001, 0x0020FFFF)
    hdr[0xF0:0x100] = b'JUE             '
    rom[0x100:0x200] = hdr

    # 3. Entry Stub at 0x0200 (copies 0x0300..0x12FF -> 0xFFE000..0xFFEFFF and jumps to 0xFFE000)
    stub = Asm68k(0x0200)
    stub.emit(0x46fc, 0x2700)                  # move.w #$2700, sr
    stub.emit(0x4ff9, 0x00ff, 0xf600)          # lea.l $fff600.l, a7
    stub.emit(0x41f9, 0x0000, 0x0300)          # lea.l $300.l, a0
    stub.emit(0x43f9, 0x00ff, 0xe000)          # lea.l $ffe000.l, a1
    stub.emit(0x303c, 0x03ff)                  # move.w #$3ff, d0 (1024 longs = 4096 bytes)
    stub.label('copy_loop')
    stub.emit(0x22d8)                          # move.l (a0)+, (a1)+
    stub.dbra(0, 'copy_loop')                  # dbra d0, copy_loop
    stub.emit(0x4ef9, 0x00ff, 0xe000)          # jmp $ffe000.l
    stub.resolve()
    rom[0x200:0x200 + len(stub.buf)] = stub.buf
    struct.pack_into('>H', rom, 0x2EE, 0x4E73) # rte at 0x02EE

    # 4. Relocated RAM Payload at 0xFFE000 (stored at ROM offset 0x0300)
    p = Asm68k(0xFFE000)

    # Initialize VDP registers so display & Plane B at 0xE000 work cleanly
    for reg_val in [
        0x8004, # Reg 0: normal mode
        0x8174, # Reg 1: display ON, MD mode, DMA on
        0x8230, # Reg 2: Plane A at 0xC000
        0x8407, # Reg 4: Plane B at 0xE000
        0x8600, # Reg 6: Sprite base
        0x8700, # Reg 7: BG color = Pal 0 Col 0
        0x8B00, # Reg 11: Full scroll
        0x8C81, # Reg 12: H40 (320px)
        0x8D2E, # Reg 13: HScroll at 0xB800
        0x8F02, # Reg 15: Auto-inc = 2
        0x9011, # Reg 16: 64x64 plane size
    ]:
        p.emit(0x33fc, reg_val, 0x00c0, 0x0004) # move.w #reg_val, $c00004.l

    # Reset VSRAM (0x40000010) to 0 so double-buffered VScroll from MDOS doesn't hide Plane B
    p.emit(0x23fc, 0x4000, 0x0010, 0x00c0, 0x0004) # move.l #$40000010, $c00004.l
    p.emit(0x23fc, 0x0000, 0x0000, 0x00c0, 0x0000) # move.l #$0, $c00000.l

    # Set CRAM Palette 0: Color 0 = 0x0400 (navy), Colors 1..15 = 0x0EEE (white)
    p.emit(0x23fc, 0xc000, 0x0000, 0x00c0, 0x0004) # move.l #$c0000000, $c00004.l
    p.emit(0x33fc, 0x0400, 0x00c0, 0x0000)          # move.w #$0400, $c00000.l
    p.emit(0x303c, 0x000e)                          # move.w #$e, d0
    p.label('cram_loop')
    p.emit(0x33fc, 0x0eee, 0x00c0, 0x0000)          # move.w #$0eee, $c00000.l
    p.dbra(0, 'cram_loop')

    # Upload 1bpp ASCII font (64 chars = 512 bytes) to VRAM 0xA000 (Tile 0x0500..0x053F)
    p.emit(0x23fc, 0x6000, 0x0002, 0x00c0, 0x0004) # move.l #$60000002, $c00004.l
    p.lea_abs(0, 'font_data')                       # lea font_data, a0
    p.emit(0x343c, 0x01ff)                          # move.w #$1ff, d2 (512 bytes)
    p.label('font_byte_loop')
    p.emit(0x1218)                                  # move.b (a0)+, d1
    p.emit(0x4280)                                  # clr.l d0
    p.emit(0x7607)                                  # moveq #$7, d3 (8 bits per byte)
    p.label('font_bit_loop')
    p.emit(0xe988)                                  # lsl.l #$4, d0
    p.emit(0xe309)                                  # lsl.b #$1, d1
    p.bcc_w('font_bit_0')
    p.emit(0x5280)                                  # addq.l #$1, d0 (pixel = color 1)
    p.label('font_bit_0')
    p.dbra(3, 'font_bit_loop')
    p.emit(0x23c0, 0x00c0, 0x0000)                  # move.l d0, $c00000.l
    p.dbra(2, 'font_byte_loop')

    # Clear VRAM Plane A & B (0xC000..0xFFFF = 0x4000 bytes = 0x2000 words)
    p.emit(0x23fc, 0x4000, 0x0003, 0x00c0, 0x0004) # move.l #$40000003, $c00004.l
    p.emit(0x303c, 0x1fff)                          # move.w #$1fff, d0
    p.label('clear_vram')
    p.emit(0x33fc, 0x0000, 0x00c0, 0x0000)          # move.w #$0, $c00000.l
    p.dbra(0, 'clear_vram')

    # Row 1: Title
    p.emit(0x7001, 0x7202)
    p.lea_abs(0, 'str_title')
    p.bsr_w('print_str')

    # Row 3: OS VER / BIOS VER ($FF0010 and $FF002E..$FF0031)
    p.emit(0x7003, 0x7202)
    p.lea_abs(0, 'str_os_bios')
    p.bsr_w('print_str')
    p.emit(0x7003, 0x7210)
    p.emit(0x2439, 0x00ff, 0x0010)                  # move.l $ff0010.l, d2 (OS version)
    p.bsr_w('print_hex')
    p.emit(0x7003, 0x7219)
    p.emit(0x2439, 0x00ff, 0x002e)                  # move.l $ff002e.l, d2 (BIOS version major.minor)
    p.bsr_w('print_hex')

    # Row 4: Compute & display FULL 32K CRC ($FF0000..$FF7FFF = 8192 longs)
    p.emit(0x207c, 0x00ff, 0x0000)                  # movea.l #$ff0000, a0
    p.emit(0x303c, 0x1fff)                          # move.w #$1fff, d0 (8192 longs)
    p.bsr_w('calc_crc_longs')
    p.emit(0x2c07)                                  # move.l d7, d6 (save full 32K CRC in d6)
    p.emit(0x7004, 0x7202)
    p.lea_abs(0, 'str_full_crc')
    p.bsr_w('print_str')
    p.emit(0x7004, 0x7210, 0x2407)
    p.bsr_w('print_hex')

    # Row 5: Compute & display BIOS HAL CRC ($FF0020..$FF081F = 512 longs)
    p.emit(0x207c, 0x00ff, 0x0020)                  # movea.l #$ff0020, a0
    p.emit(0x303c, 0x01ff)                          # move.w #$01ff, d0 (512 longs = 2048 bytes)
    p.bsr_w('calc_crc_longs')
    p.emit(0x7005, 0x7202)
    p.lea_abs(0, 'str_bios_crc')
    p.bsr_w('print_str')
    p.emit(0x7005, 0x7210, 0x2407)
    p.bsr_w('print_hex')

    # Row 6: Compute & display OS CODE CRC ($FF0820..$FF7FFF = 7672 longs = 0x1DF8 longs)
    p.emit(0x207c, 0x00ff, 0x0820)                  # movea.l #$ff0820, a0
    p.emit(0x303c, 0x1df7)                          # move.w #$1df7, d0 (7672 longs = 30688 bytes)
    p.bsr_w('calc_crc_longs')
    p.emit(0x7006, 0x7202)
    p.lea_abs(0, 'str_os_crc')
    p.bsr_w('print_str')
    p.emit(0x7006, 0x7210, 0x2407)
    p.bsr_w('print_hex')
    # Check if OS CODE CRC matches MDOS.patched.BIN (0x8118FCD8)
    p.emit(0x0c87, 0x8118, 0xfcd8)                  # cmpi.l #$8118fcd8, d7
    p.bne_w('check_os_stock')
    p.emit(0x7006, 0x7219)
    p.lea_abs(0, 'str_match_p')
    p.bsr_w('print_str')
    p.bra_w('do_byte_diff')
    p.label('check_os_stock')
    p.emit(0x0c87, 0x9efd, 0xf853)                  # cmpi.l #$9efdf853, d7
    p.bne_w('do_byte_diff')
    p.emit(0x7006, 0x7219)
    p.lea_abs(0, 'str_match_s')
    p.bsr_w('print_str')

    # --- Byte-for-byte comparison against MDOS.patched.BIN at ROM $008000..$00FFFF ---
    p.label('do_byte_diff')
    # 1. Compare HDR ($FF0000..$FF001F vs $008000..$00801F, 32 bytes)
    p.emit(0x207c, 0x00ff, 0x0000)                  # movea.l #$ff0000, a0
    p.emit(0x227c, 0x0000, 0x8000)                  # movea.l #$008000, a1
    p.emit(0x303c, 0x001f)                          # move.w #$001f, d0 (32 bytes)
    p.bsr_w('count_diffs')
    p.emit(0x2804)                                  # move.l d4, d4 (d4 = count)
    p.emit(0x7008, 0x7202)
    p.lea_abs(0, 'str_diff_hdr')
    p.bsr_w('print_str')
    p.emit(0x7008, 0x7210, 0x2404)
    p.bsr_w('print_hex')

    # 2. Compare BIOS HAL ($FF0020..$FF081F vs $008020..$00881F, 2048 bytes)
    p.emit(0x207c, 0x00ff, 0x0020)                  # movea.l #$ff0020, a0
    p.emit(0x227c, 0x0000, 0x8020)                  # movea.l #$008020, a1
    p.emit(0x303c, 0x07ff)                          # move.w #$07ff, d0 (2048 bytes)
    p.bsr_w('count_diffs')
    p.emit(0x7009, 0x7202)
    p.lea_abs(0, 'str_diff_bios')
    p.bsr_w('print_str')
    p.emit(0x7009, 0x7210, 0x2404)
    p.bsr_w('print_hex')

    # 3. Compare OS CODE ($FF0820..$FF7FFF vs $008820..$00FFFF, 30688 bytes)
    p.emit(0x207c, 0x00ff, 0x0820)                  # movea.l #$ff0820, a0
    p.emit(0x227c, 0x0000, 0x8820)                  # movea.l #$008820, a1
    p.emit(0x303c, 0x77df)                          # move.w #$77df, d0 (30688 bytes)
    p.bsr_w('count_diffs')
    p.emit(0x700a, 0x7202)
    p.lea_abs(0, 'str_diff_os')
    p.bsr_w('print_str')
    p.emit(0x700a, 0x7210, 0x2404)
    p.bsr_w('print_hex')

    p.emit(0x4a84)                                  # tst.l d4
    p.bne_w('show_first_diff')
    p.emit(0x700b, 0x7202)
    p.lea_abs(0, 'str_os_exact')
    p.bsr_w('print_str')
    p.bra_w('do_sram_dump')

    p.label('show_first_diff')
    # d5 holds the RAM address of the first differing byte in OS CODE
    p.emit(0x700b, 0x7202)
    p.lea_abs(0, 'str_first_diff')
    p.bsr_w('print_str')
    p.emit(0x700b, 0x7210, 0x2405)                  # move.l d5, d2
    p.bsr_w('print_hex')

    # --- Dump full 32 KB ($FF0000..$FF7FFF) into Cartridge SRAM ($200001..$20FFFF odd bytes) ---
    p.label('do_sram_dump')
    p.emit(0x700d, 0x7202)
    p.lea_abs(0, 'str_sram_dump')
    p.bsr_w('print_str')

    # Enable Mega Drive SRAM at $200000 via $A130F1 = 1
    p.emit(0x13fc, 0x0001, 0x00a1, 0x30f1)          # move.b #$1, $a130f1.l

    # Copy 32,768 bytes from $FF0000..$FF7FFF to odd bytes of $200000..$20FFFF
    p.emit(0x207c, 0x00ff, 0x0000)                  # movea.l #$ff0000, a0
    p.emit(0x227c, 0x0020, 0x0000)                  # movea.l #$200000, a1
    p.emit(0x303c, 0x7fff)                          # move.w #$7fff, d0 (32768 bytes)
    p.label('sram_write_loop')
    p.emit(0x1218)                                  # move.b (a0)+, d1
    p.emit(0x32c1)                                  # move.w d1, (a1)+ (writes d1 to odd byte $200001+2*i)
    p.dbra(0, 'sram_write_loop')

    # Also copy to $100000..$10FFFF in case OS-mode SRAM window is active
    p.emit(0x207c, 0x00ff, 0x0000)                  # movea.l #$ff0000, a0
    p.emit(0x227c, 0x0010, 0x0000)                  # movea.l #$100000, a1
    p.emit(0x303c, 0x7fff)                          # move.w #$7fff, d0 (32768 bytes)
    p.label('sram_write_loop2')
    p.emit(0x1218)                                  # move.b (a0)+, d1
    p.emit(0x32c1)                                  # move.w d1, (a1)+
    p.dbra(0, 'sram_write_loop2')

    # Read back 32,768 odd bytes from $200000..$20FFFF and compute rolling 32-bit CRC
    p.emit(0x227c, 0x0020, 0x0000)                  # movea.l #$200000, a1
    p.bsr_w('calc_sram_crc')
    # If $200000 CRC matches d6 (full 32K CRC), great! Otherwise check $100000
    p.emit(0xbef8) if False else None
    p.emit(0xbe86)                                  # cmp.l d6, d7
    p.beq_w('sram_crc_ok')
    p.emit(0x227c, 0x0010, 0x0000)                  # movea.l #$100000, a1
    p.bsr_w('calc_sram_crc')

    p.label('sram_crc_ok')
    p.emit(0x700e, 0x7202)
    p.lea_abs(0, 'str_sram_crc')
    p.bsr_w('print_str')
    p.emit(0x700e, 0x7210, 0x2407)
    p.bsr_w('print_hex')
    p.emit(0xbe86)                                  # cmp.l d6, d7
    p.bne_w('sram_crc_mismatch')
    p.emit(0x700e, 0x7219)
    p.lea_abs(0, 'str_ok')
    p.bsr_w('print_str')
    p.bra_w('show_instructions')

    p.label('sram_crc_mismatch')
    p.emit(0x700e, 0x7219)
    p.lea_abs(0, 'str_err')
    p.bsr_w('print_str')

    # Instructions to save SRAM to SD card via EverDrive menu
    p.label('show_instructions')
    p.emit(0x7010, 0x7202)
    p.lea_abs(0, 'str_inst1')
    p.bsr_w('print_str')
    p.emit(0x7011, 0x7202)
    p.lea_abs(0, 'str_inst2')
    p.bsr_w('print_str')
    p.emit(0x7012, 0x7202)
    p.lea_abs(0, 'str_inst3')
    p.bsr_w('print_str')
    p.emit(0x7013, 0x7202)
    p.lea_abs(0, 'str_inst4')
    p.bsr_w('print_str')

    p.label('halt')
    p.bra_w('halt')

    # --- Subroutine: calc_crc_longs ---
    # Inputs: a0 = start address, d0.w = (num_longs - 1)
    # Output: d7.l = rolling 32-bit CRC
    p.label('calc_crc_longs')
    p.emit(0x4287)                                  # clr.l d7
    p.label('crc_loop')
    p.emit(0x2218)                                  # move.l (a0)+, d1
    p.emit(0xe39f)                                  # rol.l #$1, d7
    p.emit(0xde81)                                  # add.l d1, d7
    p.dbra(0, 'crc_loop')
    p.emit(0x4e75)                                  # rts

    # --- Subroutine: calc_sram_crc ---
    # Inputs: a1 = SRAM base ($200000 or $100000)
    # Reads 8192 longwords (32,768 odd bytes) and computes rolling 32-bit CRC in d7
    p.label('calc_sram_crc')
    p.emit(0x4287)                                  # clr.l d7
    p.emit(0x303c, 0x1fff)                          # move.w #$1fff, d0 (8192 longs)
    p.label('sram_crc_loop')
    p.emit(0x7603)                                  # moveq #$3, d3 (4 bytes per longword)
    p.emit(0x4281)                                  # clr.l d1
    p.label('sram_byte_loop')
    p.emit(0xe189)                                  # lsl.l #$8, d1
    p.emit(0x3419)                                  # move.w (a1)+, d2
    p.emit(0x1202)                                  # move.b d2, d1
    p.dbra(3, 'sram_byte_loop')
    p.emit(0xe39f)                                  # rol.l #$1, d7
    p.emit(0xde81)                                  # add.l d1, d7
    p.dbra(0, 'sram_crc_loop')
    p.emit(0x4e75)                                  # rts

    # --- Subroutine: count_diffs ---
    # Inputs: a0 = live RAM start, a1 = ROM copy start, d0.w = (num_bytes - 1)
    # Outputs: d4.l = number of differing bytes, d5.l = address of first diff (or 0)
    p.label('count_diffs')
    p.emit(0x4284)                                  # clr.l d4
    p.emit(0x4285)                                  # clr.l d5
    p.label('diff_loop')
    p.emit(0x1218)                                  # move.b (a0)+, d1
    p.emit(0x1419)                                  # move.b (a1)+, d2
    p.emit(0xb202)                                  # cmp.b d2, d1
    p.beq_w('diff_same')
    p.emit(0x5284)                                  # addq.l #$1, d4
    p.emit(0x4a85)                                  # tst.l d5
    p.bne_w('diff_same')
    p.emit(0x2a08)                                  # move.l a0, d5
    p.emit(0x5385)                                  # subq.l #$1, d5
    p.label('diff_same')
    p.dbra(0, 'diff_loop')
    p.emit(0x4e75)                                  # rts

    # --- VDP Subroutines: set_vdp_pos, print_str, print_hex ---
    p.label('set_vdp_pos')
    p.emit(0x48e7, 0xc000)                          # movem.l d0-d1, -(a7)
    p.emit(0xef40)                                  # asl.w #$7, d0
    p.emit(0xd241)                                  # add.w d1, d1
    p.emit(0xd041)                                  # add.w d1, d0
    p.emit(0x0280, 0x0000, 0x1fff)                  # andi.l #$1fff, d0
    p.emit(0x0040, 0x6000)                          # ori.w #$6000, d0
    p.emit(0x4840)                                  # swap d0
    p.emit(0x303c, 0x0003)                          # move.w #$3, d0
    p.emit(0x23c0, 0x00c0, 0x0004)                  # move.l d0, $c00004.l
    p.emit(0x4cdf, 0x0003)                          # movem.l (a7)+, d0-d1
    p.emit(0x4e75)                                  # rts

    p.label('print_str')
    p.bsr_w('set_vdp_pos')
    p.label('pstr_loop')
    p.emit(0x4240)                                  # clr.w d0
    p.emit(0x1018)                                  # move.b (a0)+, d0
    p.beq_w('pstr_done')
    p.emit(0x0640, 0x04e0)                          # addi.w #$4e0, d0
    p.emit(0x33c0, 0x00c0, 0x0000)                  # move.w d0, $c00000.l
    p.bra_w('pstr_loop')
    p.label('pstr_done')
    p.emit(0x4e75)                                  # rts

    p.label('print_hex')
    p.emit(0x48e7, 0x3000)                          # movem.l d2-d3, -(a7)
    p.bsr_w('set_vdp_pos')
    p.emit(0x7607)                                  # moveq #$7, d3
    p.label('phex_loop')
    p.emit(0xe99a)                                  # rol.l #$4, d2
    p.emit(0x3002)                                  # move.w d2, d0
    p.emit(0x0240, 0x000f)                          # andi.w #$f, d0
    p.emit(0x0c40, 0x000a)                          # cmpi.w #$a, d0
    p.bcs_w('phex_digit')
    p.emit(0x5e40)                                  # addq.w #$7, d0
    p.label('phex_digit')
    p.emit(0x0640, 0x0510)                          # addi.w #$510, d0
    p.emit(0x33c0, 0x00c0, 0x0000)                  # move.w d0, $c00000.l
    p.dbra(3, 'phex_loop')
    p.emit(0x4cdf, 0x000c)                          # movem.l (a7)+, d2-d3
    p.emit(0x4e75)                                  # rts

    code_end_off = len(p.buf)

    # --- Strings and Font Data ---
    p.label('str_title')
    p.emit_str('=== EVERDRIVE-MD V3 OS DUMPER V2 ===')
    p.label('str_os_bios')
    p.emit_str('OS / BIOS VR:')
    p.label('str_full_crc')
    p.emit_str('FULL 32K CRC:')
    p.label('str_bios_crc')
    p.emit_str('BIOS HAL CRC:')
    p.label('str_os_crc')
    p.emit_str('OS CODE CRC :')
    p.label('str_match_p')
    p.emit_str('(PATCHED V1)')
    p.label('str_match_s')
    p.emit_str('(STOCK V2)')
    p.label('str_diff_hdr')
    p.emit_str('HDR DIFFS   :')
    p.label('str_diff_bios')
    p.emit_str('BIOS DIFFS  :')
    p.label('str_diff_os')
    p.emit_str('OS DIFFS    :')
    p.label('str_os_exact')
    p.emit_str('OS CODE: 100% MATCH MDOS.PATCHED!')
    p.label('str_first_diff')
    p.emit_str('1ST OS DIFF :')
    p.label('str_sram_dump')
    p.emit_str('COPYING 32KB MDOS TO CART SRAM...')
    p.label('str_sram_crc')
    p.emit_str('SRAM VERIFY :')
    p.label('str_ok')
    p.emit_str('OK! (32KB SAVED)')
    p.label('str_err')
    p.emit_str('MISMATCH!')
    p.label('str_inst1')
    p.emit_str('TO SAVE DUMP TO SD CARD:')
    p.label('str_inst2')
    p.emit_str('1. PRESS RESET TO ENTER ED MENU')
    p.label('str_inst3')
    p.emit_str('2. LOAD ANY GAME (AUTO-SAVES TO')
    p.label('str_inst4')
    p.emit_str('   /EDMD/SAVE/OSV3DUMP.SRM)')

    p.label('font_data')
    font_bytes = bytearray()
    for code in range(0x20, 0x60):
        ch = chr(code)
        rows = FONT_1BPP.get(ch, [0]*8)
        font_bytes.extend(rows)
    p.emit_b(font_bytes)

    p.resolve()
    assert len(p.buf) <= 0x1000, f"Payload size {len(p.buf)} exceeds 0x1000!"
    rom[0x300:0x300 + len(p.buf)] = p.buf

    # 5. Compute Mega Drive ROM Checksum (sum of 16-bit words from 0x0200 to end of ROM)
    cksum = sum(struct.unpack('>32512H', rom[0x200:])) & 0xFFFF
    struct.pack_into('>H', rom, 0x18E, cksum)

    out_path = 'mega-genesis/OSV3DUMP.BIN'
    with open(out_path, 'wb') as f:
        f.write(rom)

    print(f"Built {out_path}: {len(rom)} bytes, payload={len(p.buf)} bytes, checksum=0x{cksum:04X}, sha256={hashlib.sha256(rom).hexdigest()}")

    # Verify disassembly of code region
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    insns = list(md.disasm(bytes(p.buf[:code_end_off]), 0xFFE000))
    last_end = 0xFFE000
    for i in insns:
        last_end = i.address + i.size
    assert last_end == 0xFFE000 + code_end_off, f"Disassembly stopped early at 0x{last_end:06x} vs 0x{0xFFE000+code_end_off:06x}"
    print("Disassembly 100% verified with zero invalid instructions!")

if __name__ == '__main__':
    build_rom()
