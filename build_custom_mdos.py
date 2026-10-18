import struct
import hashlib
from capstone import *

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

    def emit_l(self, *longs):
        for l in longs:
            self.buf.extend(struct.pack('>I', l & 0xffffffff))

    def emit_b(self, data):
        self.buf.extend(data)
        if len(self.buf) % 2 != 0:
            self.buf.append(0)

    def emit_str(self, s_bytes):
        if isinstance(s_bytes, str):
            s_bytes = s_bytes.encode('latin1')
        self.emit_b(s_bytes + b'\x00')

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

    def bls_w(self, target_label):
        self.emit(0x6300, 0x0000)
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

    def b_s(self, cc, target_label):
        """short branch: cc = 0x60 bra, 0x61 bsr, 0x65 bcs, 0x66 bne, 0x67 beq ..."""
        self.emit(cc << 8)
        self.fixups.append((len(self.buf) - 1, target_label, 'b8'))

    def dbeq(self, dreg, target_label):
        self.emit(0x57c8 | dreg, 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def lea_pc(self, areg, target_label):
        self.emit(0x41fa | (areg << 9), 0x0000)
        self.fixups.append((len(self.buf) - 2, target_label, 'w16'))

    def pea_label(self, target_label):
        self.emit(0x4879, 0x0000, 0x0000)
        self.fixups.append((len(self.buf) - 4, target_label, 'abs32'))

    def lea_label(self, areg, target_label):
        self.emit(0x41f9 | (areg << 9), 0x0000, 0x0000)
        self.fixups.append((len(self.buf) - 4, target_label, 'abs32'))

    def jmp_label(self, target_label):
        self.emit(0x4ef9, 0x0000, 0x0000)
        self.fixups.append((len(self.buf) - 4, target_label, 'abs32'))

    def jsr_label(self, target_label):
        self.emit(0x4eb9, 0x0000, 0x0000)
        self.fixups.append((len(self.buf) - 4, target_label, 'abs32'))

    def resolve(self, external_labels=None):
        all_labels = dict(self.labels)
        if external_labels:
            all_labels.update(external_labels)
        for off, name, kind in self.fixups:
            target = all_labels[name]
            if kind == 'w16':
                disp = target - (self.base + off)
                assert -32768 <= disp <= 32767, f"Disp out of range for {name}: {disp}"
                struct.pack_into('>h', self.buf, off, disp)
            elif kind == 'b8':
                disp = target - (self.base + off + 1)
                assert -128 <= disp <= 127 and disp not in (0, -1), f"Short disp out of range for {name}: {disp}"
                struct.pack_into('>b', self.buf, off, disp)
            elif kind == 'abs32':
                struct.pack_into('>I', self.buf, off, target)


def pack_2bpp_tile(rows_str):
    assert len(rows_str) == 8
    out = bytearray()
    val_map = {'.': 0, '0': 0, '1': 1, '2': 2, '3': 3, '#': 3}
    for row in rows_str:
        assert len(row) == 8, f"Row must be 8 chars: {row!r}"
        b0 = (val_map[row[0]] << 6) | (val_map[row[1]] << 4) | (val_map[row[2]] << 2) | val_map[row[3]]
        b1 = (val_map[row[4]] << 6) | (val_map[row[5]] << 4) | (val_map[row[6]] << 2) | val_map[row[7]]
        out.append(b0)
        out.append(b1)
    return bytes(out)


def build_font_and_banner_2bpp():
    """
    Builds 20 contiguous 2bpp tiles (320 bytes):
      - Tiles 0x80..0x87 (8 tiles): PT-BR accented glyphs matching Krikzz's 8x8 font
          0x80 = ç, 0x81 = ã, 0x82 = õ, 0x83 = á, 0x84 = é, 0x85 = í, 0x86 = ó, 0x87 = Ã
      - Tiles 0x88..0x97 (16 tiles = 128x8 px): "RETROGAMER POA" banner in the OS font
    """
    accent_glyphs = [
        # 0x80: ç
        [
            "........",
            "..####..",
            ".##.....",
            ".##.....",
            ".##.....",
            "..####..",
            "...##...",
            "..##....",
        ],
        # 0x81: ã
        [
            "..##.#..",
            ".#..##..",
            "........",
            "..####..",
            ".....##.",
            "..#####.",
            ".##..##.",
            "..#####.",
        ],
        # 0x82: õ
        [
            "..##.#..",
            ".#..##..",
            "........",
            "..####..",
            ".##..##.",
            ".##..##.",
            "..####..",
            "........",
        ],
        # 0x83: á
        [
            "....##..",
            "...##...",
            "..####..",
            ".....##.",
            "..#####.",
            ".##..##.",
            "..#####.",
            "........",
        ],
        # 0x84: é
        [
            "....##..",
            "...##...",
            "..####..",
            ".##..##.",
            ".######.",
            ".##.....",
            "..####..",
            "........",
        ],
        # 0x85: í
        [
            "....##..",
            "...##...",
            "........",
            "..###...",
            "...##...",
            "...##...",
            "..####..",
            "........",
        ],
        # 0x86: ó
        [
            "....##..",
            "...##...",
            "..####..",
            ".##..##.",
            ".##..##.",
            ".##..##.",
            "..####..",
            "........",
        ],
        # 0x87: Ã
        [
            "..##.#..",
            ".#..##..",
            "...##...",
            "..####..",
            ".##..##.",
            ".######.",
            ".##..##.",
            "........",
        ],
    ]

    # Banner in the v1 style: 16 tiles, one OS-font letter per tile, rounded crimson bar.
    # 1 = crimson bar, 2 = gold letter, 0 = shadow (transparent, shows the backdrop).
    text = " RETROGAMER POA "
    W, H = 8 * len(text), 8
    canvas = [['1' for _ in range(W)] for _ in range(H)]
    for y in (0, 7):
        canvas[y][0] = canvas[y][W - 1] = '0'           # rounded ends
    font = {    # Krikzz OS font, columns 1..7 of rows 1..6
        'R': ["#####..", "##..##.", "##..##.", "#####..", "##.##..", "##..##."],
        'E': ["######.", "##.....", "#####..", "##.....", "##.....", "######."],
        'T': ["######.", "..##...", "..##...", "..##...", "..##...", "..##..."],
        'O': [".####..", "##..##.", "##..##.", "##..##.", "##..##.", ".####.."],
        'G': [".#####.", "##.....", "##.....", "##.###.", "##..##.", ".#####."],
        'A': ["..##...", ".####..", "##..##.", "##..##.", "######.", "##..##."],
        'M': ["##...##", "###.###", "#######", "##.#.##", "##...##", "##...##"],
        'P': ["#####..", "##..##.", "##..##.", "#####..", "##.....", "##....."],
    }
    for i, c in enumerate(text):
        if c == ' ':
            continue
        for ry, row in enumerate(font[c]):
            for rx, px in enumerate(row):
                if px == '#':
                    x = i * 8 + 1 + rx
                    canvas[1 + ry][x] = '2'
                    if canvas[2 + ry][x + 1] == '1':
                        canvas[2 + ry][x + 1] = '0'

    out = bytearray()
    for tile_rows in accent_glyphs:
        out.extend(pack_2bpp_tile(tile_rows))
    for t in range(16):
        tile_rows = [''.join(canvas[r][t * 8 : (t + 1) * 8]) for r in range(8)]
        out.extend(pack_2bpp_tile(tile_rows))
    assert len(out) == 24 * 16
    return bytes(out)


MOD_VERSION = '1.6'      # same number for v1 and v3, shown in Info Sistema
PREVIEW_FRAMES = 19     # vblanks resting on a file before its cover is shown (~0.32 s NTSC)


def build_custom_mdos():
    with open('mega-genesis/MDOS.patched.BIN', 'rb') as f:
        orig = bytearray(f.read())
    assert len(orig) == 131072

    rom = bytearray(orig)

    # =========================================================================
    # Block 1: Helper routines at 0xFF0B92..0xFF0BFA (104 bytes of dead romFileMenu)
    #   - sramReadBytes, sramWriteBytes, draw_top_banner
    # =========================================================================
    blk1 = Asm68k(0xFF0B92)

    blk1.label('sramReadBytes')
    blk1.emit(0x226f, 0x0004)                       # movea.l $4(a7), a1 (sram_src)
    blk1.emit(0x206f, 0x0008)                       # movea.l $8(a7), a0 (ram_dst)
    blk1.emit(0x322f, 0x000e)                       # move.w $e(a7), d1 (count)
    blk1.emit(0x5341)                               # subq.w #1, d1
    blk1.emit(0x0c41, 0xffff)                       # cmpi.w #$ffff, d1
    blk1.beq_w('sramRead_done')
    blk1.label('sramRead_loop')
    blk1.emit(0x3019)                               # move.w (a1)+, d0
    blk1.emit(0x10c0)                               # move.b d0, (a0)+
    blk1.dbra(1, 'sramRead_loop')
    blk1.label('sramRead_done')
    blk1.emit(0x4e75)                               # rts

    blk1.label('sramWriteBytes')
    blk1.emit(0x226f, 0x0004)                       # movea.l $4(a7), a1 (ram_src)
    blk1.emit(0x206f, 0x0008)                       # movea.l $8(a7), a0 (sram_dst)
    blk1.emit(0x322f, 0x000e)                       # move.w $e(a7), d1 (count)
    blk1.emit(0x5341)                               # subq.w #1, d1
    blk1.emit(0x0c41, 0xffff)                       # cmpi.w #$ffff, d1
    blk1.beq_w('sramWrite_done')
    blk1.label('sramWrite_loop')
    blk1.emit(0x4240)                               # clr.w d0
    blk1.emit(0x1019)                               # move.b (a1)+, d0
    blk1.emit(0x30c0)                               # move.w d0, (a0)+
    blk1.dbra(1, 'sramWrite_loop')
    blk1.label('sramWrite_done')
    blk1.emit(0x4e75)                               # rts

    blk1.label('draw_top_banner')
    blk1.emit(0x4878, 0x0002)                       # pea.l $2.w (Palette 2)
    blk1.emit(0x4e94)                               # jsr (a4) (gSetPal)
    blk1.emit(0x4878, 0x0001)                       # pea.l $1.w (y = 1)
    blk1.emit(0x4878, 0x000c)                       # pea.l $c.w (x = 12, centred)
    blk1.pea_label('str_banner_tiles')              # "\x88..\x93"
    blk1.emit(0x4e95)                               # jsr (a5) (gPrintAt)
    blk1.emit(0x4297)                               # clr.l (a7) (Palette 0)
    blk1.emit(0x4e94)                               # jsr (a4) (gSetPal)
    blk1.emit(0x4fef, 0x0010)                       # lea.l $10(a7), a7
    blk1.emit(0x2079, 0x00ff, 0xc46c)               # movea.l $ffc46c.l, a0 (original instruction)
    blk1.emit(0x4e75)                               # rts

    # =========================================================================
    # Block 2: aboutScreen_ptbr at 0xFF4F74..0xFF5034 (192 bytes of old aboutScreen)
    # =========================================================================
    blk2 = Asm68k(0xFF4F74)
    blk2.label('aboutScreen_ptbr')
    blk2.emit(0x48e7, 0x3038)                       # movem.l d2-d3/a2-a4, -(a7)
    blk2.emit(0x2879, 0x00ff, 0x0024)               # movea.l $ff0024.l, a4
    blk2.emit(0x7400)                               # moveq #0, d2
    blk2.emit(0x4eb9, 0x00ff, 0x3802)               # jsr $ff3802.l (gCleanPlan)
    blk2.emit(0x45f9, 0x00ff, 0x3700)               # lea.l $ff3700.l, a2 (gAppendLine)
    blk2.emit(0x47f9, 0x00ff, 0x30a0)               # lea.l $ff30a0.l, a3 (gSetPal)

    # Loop over 18 lines in about_table (each entry = 6 bytes: word pal, long str_ptr)
    blk2.lea_label(0, 'about_table')                 # lea about_table, a0
    blk2.emit(0x7611)                                # moveq #17, d3 (18 lines)
    blk2.label('ab_loop')
    blk2.emit(0x2848)                                # movea.l a0, a4 (save table ptr in a4 temporarily)
    blk2.emit(0x301c)                                # move.w (a4)+, d0 (pal)
    blk2.emit(0x4840)                                # swap d0
    blk2.emit(0x4240)                                # clr.w d0
    blk2.emit(0x4840)                                # swap d0 (zero-extended long)
    blk2.emit(0x2f00)                                # move.l d0, -(a7)
    blk2.emit(0x4e93)                                # jsr (a3) (gSetPal)
    blk2.emit(0x2f1c)                                # move.l (a4)+, -(a7) (str_ptr)
    blk2.emit(0x4e92)                                # jsr (a2) (gAppendLine)
    blk2.emit(0x508f)                                # addq.l #8, a7
    blk2.emit(0x204c)                                # movea.l a4, a0
    blk2.dbra(3, 'ab_loop')

    blk2.emit(0x2879, 0x00ff, 0x0024)                # movea.l $ff0024.l, a4 (restore a4 = SRAM base for $ff5040!)
    blk2.emit(0x47f9, 0x00ff, 0x33b6)                # lea.l $ff33b6.l, a3
    blk2.emit(0x4e93)                                # jsr (a3)
    blk2.emit(0x4ef9, 0x00ff, 0x5040)                # jmp $ff5040.l
    blk2_code_end = len(blk2.buf)

    blk2.label('about_table')
    ab_entries = [
        (0, 'str_empty'),
        (2, 'str_ab_title'),
        (2, 'str_ab_dev'),
        (0, 'str_empty'),
        (2, 'str_ab_mod_hdr'),
        (2, 'str_banner_tiles'),
        (1, 'str_ab_mod_2'),
        (0, 'str_empty'),
        (2, 'str_ab_sup_hdr'),
        (0, 'str_ab_sup_1'),
        (0, 'str_ab_sup_2'),
        (0, 'str_empty'),
        (2, 'str_ab_ctl_hdr'),
        (0, 'str_ab_ctl_1'),
        (0, 'str_ab_ctl_2'),
        (0, 'str_ab_ctl_3'),
        (0, 'str_ab_ctl_4'),
        (0, 'str_ab_ctl_5'),
    ]
    for pal, lbl_name in ab_entries:
        blk2.emit(pal)
        off = len(blk2.buf)
        blk2.emit_l(0)
        blk2.fixups.append((off, lbl_name, 'abs32'))

    # =========================================================================
    # Block 3: playRandomGame & loadRomWithRecent at 0xFF50BC..0xFF5194 (216 bytes)
    # =========================================================================
    blk3 = Asm68k(0xFF50BC)

    blk3.label('loadRomWithRecent')
    blk3.emit(0x2f2f, 0x0004)                       # move.l $4(a7), -(a7) (fat_rec)
    blk3.emit(0x4eb9, 0x00ff, 0x5f22)               # jsr $ff5f22.l        (loadRom)
    blk3.emit(0x588f)                               # addq.l #4, a7
    blk3.emit(0x4a40)                               # tst.w d0
    blk3.bne_w('loadRomRecent_exit')
    blk3.emit(0x2f2f, 0x0004)                       # move.l $4(a7), -(a7) (fat_rec)
    blk3.jsr_label('addRecentIfRom')
    blk3.emit(0x588f)                               # addq.l #4, a7
    blk3.emit(0x7000)                               # moveq #0, d0
    blk3.label('loadRomRecent_exit')
    blk3.emit(0x4e75)                               # rts

    blk3.label('playRandomGame')
    blk3.emit(0x48e7, 0x3820)                       # movem.l d2-d4/a2, -(a7)
    blk3.emit(0x2479, 0x00ff, 0xc46c)               # movea.l $ffc46c.l, a2 (dir_hdr)
    blk3.emit(0x3412)                               # move.w (a2), d2 (dir entry count)
    blk3.beq_w('rand_empty')
    blk3.emit(0x4280)                               # clr.l d0
    blk3.emit(0x3039, 0x00c0, 0x0008)               # move.w $c00008.l, d0 (VDP HV counter)
    blk3.emit(0xd079, 0x00ff, 0xc474)               # add.w $ffc474.l, d0
    blk3.emit(0x80c2)                               # divu.w d2, d0
    blk3.emit(0x4840)                               # swap d0 (d0.w = random index 0..d2-1)
    blk3.emit(0x3600)                               # move.w d0, d3
    blk3.emit(0x3802)                               # move.w d2, d4
    blk3.emit(0x5344)                               # subq.w #1, d4
    blk3.label('rand_find_loop')
    blk3.emit(0x4280)                               # clr.l d0
    blk3.emit(0x3003)                               # move.w d3, d0
    blk3.emit(0xe588)                               # lsl.l #2, d0
    blk3.emit(0x41f2, 0x0800)                       # lea.l (a2, d0.l), a0
    blk3.emit(0x2068, 0x3016)                       # movea.l $3016(a0), a0 (dir entry ptr)
    blk3.emit(0x4a68, 0x000a)                       # tst.w $a(a0) (0 = file, !=0 = dir)
    blk3.beq_w('rand_found')
    blk3.label('rand_skip')
    blk3.emit(0x5243)                               # addq.w #1, d3
    blk3.emit(0xb642)                               # cmp.w d2, d3
    blk3.bcs_w('rand_next')
    blk3.emit(0x4243)                               # clr.w d3
    blk3.label('rand_next')
    blk3.dbra(4, 'rand_find_loop')

    blk3.label('rand_empty')
    blk3.emit(0x42a7)                               # clr.l -(a7)
    blk3.emit(0x4878, 0x0001)                       # pea.l $1.w
    blk3.pea_label('menu_no_rand')
    blk3.emit(0x4eb9, 0x00ff, 0x4834)               # jsr $ff4834.l (menuDraw)
    blk3.emit(0x4fef, 0x000c)                       # lea.l $c(a7), a7
    blk3.emit(0x7000)                               # moveq #0, d0
    blk3.bra_w('rand_exit')

    blk3.label('rand_found')
    blk3.emit(0x4879, 0x00ff, 0xc800)               # pea.l $ffc800.l (fat_rec buf in free RAM)
    blk3.emit(0x2f08)                               # move.l a0, -(a7) (dir entry ptr)
    blk3.emit(0x4eb9, 0x00ff, 0x2872)               # jsr $ff2872.l (fatGetRec)
    blk3.emit(0x508f)                               # addq.l #8, a7
    blk3.emit(0x4a00)                               # tst.b d0
    blk3.bne_w('rand_exit')
    blk3.emit(0x41f9, 0x00ff, 0xc800)               # lea.l $ffc800.l, a0
    blk3.jsr_label('isRomRec')                      # only ROMs (no .txt/.rar/saves)
    blk3.bne_w('rand_skip')
    blk3.emit(0x4879, 0x00ff, 0xc800)               # pea.l $ffc800.l
    blk3.bsr_w('loadRomWithRecent')
    blk3.emit(0x588f)                               # addq.l #4, a7
    blk3.emit(0x4a40)                               # tst.w d0
    blk3.bne_w('rand_exit')
    blk3.emit(0x4eb9, 0x00ff, 0x567e)               # jsr $ff567e.l (startGame)

    blk3.label('rand_exit')
    blk3.emit(0x4cdf, 0x041c)                       # movem.l (a7)+, d2-d4/a2
    blk3.emit(0x4e75)                               # rts

    # =========================================================================
    # Block 4: Primary Extension Space 0xFF6E48..0xFF7FFF
    # =========================================================================
    ext = Asm68k(0xFF6E48)

    # 1. init_recent_sram (20 slots: 10 Recent at $ffc500 + 10 Favorites at $ffc528)
    ext.label('init_recent_sram')
    ext.emit(0x23c0, 0x00ff, 0xc49e)                # move.l d0, $ffc49e.l
    ext.emit(0x48e7, 0x3030)                        # movem.l d2-d3/a2-a3, -(a7)
    ext.emit(0x45f9, 0x00ff, 0x556c)                # lea.l $ff556c.l, a2 (sramAlloc)
    ext.emit(0x47f9, 0x00ff, 0xc500)                # lea.l $ffc500.l, a3
    ext.emit(0x7613)                                # moveq #19, d3 (20 slots)
    ext.label('init_recent_loop')
    ext.emit(0x4878, 0x0220)                        # pea.l $220.w
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.emit(0x26c0)                                # move.l d0, (a3)+
    ext.dbra(3, 'init_recent_loop')
    ext.emit(0x4cdf, 0x0c0c)                        # movem.l (a7)+, d2-d3/a2-a3
    ext.emit(0x4e75)                                # rts

    # 2. clear_recent_sram (first boot SRAM init)
    ext.label('clear_recent_sram')
    ext.emit(0x2079, 0x00ff, 0xc47a)                # movea.l $ffc47a.l, a0
    ext.emit(0x4268, 0x000c)                        # clr.w $c(a0) (default Theme = 0)
    ext.emit(0x43f9, 0x00ff, 0xc500)                # lea.l $ffc500.l, a1
    ext.emit(0x7213)                                # moveq #19, d1 (20 slots)
    ext.b_s(0x61, 'clr_slots')
    ext.emit(0x4ef9, 0x00ff, 0x37e6)                # jmp $ff37e6.l

    # clr_slots(a1 = slot pointer table, d1 = slots - 1): zero the SRAM records
    ext.label('clr_slots')
    ext.emit(0x2059)                                # movea.l (a1)+, a0
    ext.emit(0x303c, 0x010f)                        # move.w #$10f, d0
    ext.label('clr_slot_word')
    ext.emit(0x4258)                                # clr.w (a0)+
    ext.dbra(0, 'clr_slot_word')
    ext.dbra(1, 'clr_slots')
    ext.emit(0x4e75)                                # rts

    # 3. boot_init_vram_and_theme (runs on every boot at 0xFF63E2)
    ext.label('boot_init_vram_and_theme')
    ext.emit(0x4eb9, 0x00ff, 0x662a)                # jsr $ff662a.l
    ext.emit(0x48e7, 0x3c30)                        # movem.l d2-d5/a2-a3, -(a7)
    ext.emit(0x23fc, 0x5000, 0x0000, 0x00c0, 0x0004)# move.l #$50000000, $c00004.l (VRAM Write @ 0x1000)
    ext.lea_label(0, 'tiles_2bpp_data')
    ext.lea_label(1, 'lut_2bpp_to_4bpp')
    ext.emit(0x363c, 0x017f)                        # move.w #383, d3 (24 2bpp tiles -> VRAM 0x1000)
    ext.label('unpack_byte_loop')
    ext.emit(0x1018)                                # move.b (a0)+, d0
    ext.emit(0x7803)                                # moveq #3, d4
    ext.label('unpack_pix_loop')
    ext.emit(0xe518)                                # rol.b #2, d0
    ext.emit(0x7203)                                # moveq #3, d1
    ext.emit(0xc200)                                # and.b d0, d1
    ext.emit(0xe94a)                                # lsl.w #4, d2
    ext.emit(0x8431, 0x1000)                        # or.b (a1, d1.w), d2
    ext.dbra(4, 'unpack_pix_loop')
    ext.emit(0x33c2, 0x00c0, 0x0000)                # move.w d2, $c00000.l
    ext.dbra(3, 'unpack_byte_loop')

    # Set Banner colors in Palette 2: Col 1 = 0x00A (Crimson), Col 2 = 0x0AE (Gold)
    ext.emit(0x45f9, 0x00ff, 0x65ae)                # lea.l $ff65ae.l, a2 (vdpSetPal)
    ext.emit(0x4878, 0x000a)                        # pea.l $a.w
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4878, 0x00ae)                        # pea.l $ae.w
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4fef, 0x0018)                        # lea.l $18(a7), a7
    ext.bsr_w('applyTheme')
    ext.emit(0x42b9, 0x00ff, 0xc5a0)                # clr.l $ffc5a0.l (L/R flags + cursor)
    ext.emit(0x4cdf, 0x0c3c)                        # movem.l (a7)+, d2-d5/a2-a3
    ext.emit(0x4e75)                                # rts

    # 4. applyTheme
    ext.label('applyTheme')
    ext.emit(0x48e7, 0x2030)                        # movem.l d2/a2-a3, -(a7)
    ext.emit(0x2079, 0x00ff, 0xc47a)                # movea.l $ffc47a.l, a0
    ext.emit(0x3028, 0x000c)                        # move.w $c(a0), d0
    ext.emit(0x0240, 0x0003)                        # andi.w #3, d0
    ext.emit(0xe740)                                # lsl.w #3, d0
    ext.lea_label(3, 'theme_pal_table')
    ext.emit(0xd6c0)                                # adda.w d0, a3
    ext.emit(0x45f9, 0x00ff, 0x65ae)                # lea.l $ff65ae.l, a2 (vdpSetPal)

    ext.emit(0x7400)                                # moveq #0, d2 (col 0, 1, 2 of Pal 0)
    ext.label('theme_pal0_loop')
    ext.emit(0x4280)                                # clr.l d0
    ext.emit(0x301b)                                # move.w (a3)+, d0
    ext.emit(0x2f00)                                # move.l d0, -(a7)
    ext.emit(0x2f02)                                # move.l d2, -(a7) (col = d2)
    ext.emit(0x42a7)                                # clr.l -(a7) (pal = 0)
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x5242)                                # addq.w #1, d2
    ext.emit(0x0c42, 0x0002)                        # cmpi.w #2, d2
    ext.bls_w('theme_pal0_loop')

    # Pal 1, Col 15 = Selected / Cursor text
    ext.emit(0x4280)                                # clr.l d0
    ext.emit(0x301b)                                # move.w (a3)+, d0
    ext.emit(0x2f00)                                # move.l d0, -(a7)
    ext.emit(0x4878, 0x000f)                        # pea.l $f.w (col = 15)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w (pal = 1)
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4cdf, 0x0c04)                        # movem.l (a7)+, d2/a2-a3
    ext.emit(0x4e75)                                # rts

    # 5. addRecentlyPlayed, addFavorite & addSlotEntry
    ext.label('addRecentlyPlayed')
    ext.emit(0x43f9, 0x00ff, 0xc500)                # lea.l $ffc500.l, a1
    ext.bra_w('addSlotEntry')

    ext.label('addFavorite')
    ext.emit(0x43f9, 0x00ff, 0xc528)                # lea.l $ffc528.l, a1

    ext.label('addSlotEntry')
    ext.emit(0x48e7, 0x2020)                        # movem.l d2/a2, -(a7)
    ext.emit(0x2449)                                # movea.l a1, a2
    ext.emit(0x7408)                                # moveq #8, d2
    ext.label('addSlot_loop')
    ext.emit(0x4878, 0x0220)                        # pea.l $220.w
    ext.emit(0x2002)                                # move.l d2, d0
    ext.emit(0xe588)                                # lsl.l #2, d0
    ext.emit(0x41f2, 0x0800)                        # lea.l (a2, d0.l), a0
    ext.emit(0x2f28, 0x0004)                        # move.l $4(a0), -(a7)
    ext.emit(0x2f10)                                # move.l (a0), -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x5642)                # jsr $ff5642.l (edMemcpy)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4a42)                                # tst.w d2
    ext.beq_w('addSlot_write0')
    ext.emit(0x5342)                                # subq.w #1, d2
    ext.bra_w('addSlot_loop')
    ext.label('addSlot_write0')
    ext.emit(0x4878, 0x0110)                        # pea.l $110.w
    ext.emit(0x2f12)                                # move.l (a2), -(a7)
    ext.emit(0x2f2f, 0x0014)                        # move.l $14(a7), -(a7)
    ext.jsr_label('sramWriteBytes')
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4cdf, 0x0404)                        # movem.l (a7)+, d2/a2
    ext.emit(0x4e75)                                # rts

    # 6. recentlyPlayedMenu, favoritesMenu & slotListMenu
    ext.label('recentlyPlayedMenu')
    ext.lea_label(0, 'str_recent_title')
    ext.lea_label(1, 'menu_no_recent')
    ext.emit(0x203c, 0x00ff, 0xc500)                # move.l #$ffc500, d0
    ext.bra_w('slotListMenu')

    ext.label('favoritesMenu')
    ext.lea_label(0, 'str_fav_title')
    ext.lea_label(1, 'menu_no_fav')
    ext.emit(0x203c, 0x00ff, 0xc528)                # move.l #$ffc528, d0

    ext.label('slotListMenu')
    # frame: 0 menu title, 4 item ptrs (10 + "Limpar recentes"), 52 fat_rec, 324 names 10 x 37,
    # 694 "list empty" menu
    ext.emit(0x48e7, 0x3838)                        # movem.l d2-d4/a2-a4, -(a7)
    ext.emit(0x4fef, 0xfd46)                        # lea.l -698(a7), a7
    ext.emit(0x2e88)                                # move.l a0, (a7) (title)
    ext.emit(0x2f49, 694)                           # move.l a1, 694(a7)
    ext.emit(0x2640)                                # movea.l d0, a3 (slot table)
    ext.label('sl_restart')
    ext.emit(0x45ef, 0x0004)                        # lea.l 4(a7), a2 (item ptrs)
    ext.emit(0x49ef, 324)                           # lea.l 324(a7), a4 (names)
    ext.emit(0x7600)                                # moveq #0, d3 (count)
    ext.label('sl_read')
    ext.emit(0x3003, 0xe548)                        # move.w d3, d0 ; lsl.w #2, d0
    ext.emit(0x4878, 0x0110)                        # pea.l $110.w
    ext.emit(0x486f, 56)                            # pea.l 56(a7) (fat_rec)
    ext.emit(0x2f33, 0x0000)                        # move.l (a3, d0.w), -(a7)
    ext.jsr_label('sramReadBytes')
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4a2f, 66)                            # tst.b 66(a7) (name)
    ext.b_s(0x67, 'sl_done')
    ext.emit(0x24cc)                                # move.l a4, (a2)+
    ext.emit(0x41ef, 66)                            # lea.l 66(a7), a0
    ext.emit(0x7020)                                # moveq #32, d0 (33 chars)
    ext.label('sl_copy')
    ext.emit(0x18d8)                                # move.b (a0)+, (a4)+
    ext.dbeq(0, 'sl_copy')
    ext.b_s(0x67, 'sl_next')
    ext.emit(0x702e)                                # moveq #'.', d0 (long name: "...")
    ext.emit(0x18c0, 0x18c0, 0x18c0)                # move.b d0, (a4)+ x3
    ext.emit(0x4214)                                # clr.b (a4)
    ext.label('sl_next')
    ext.emit(0x286a, 0xfffc)                        # movea.l -4(a2), a4
    ext.emit(0x49ec, 37)                            # lea.l 37(a4), a4
    ext.emit(0x5243)                                # addq.w #1, d3
    ext.emit(0x0c43, 10)                            # cmpi.w #10, d3
    ext.b_s(0x65, 'sl_read')
    ext.label('sl_done')
    ext.emit(0x4292)                                # clr.l (a2)
    ext.emit(0x7800, 0x3803)                        # moveq #0, d4 ; move.w d3, d4 (items)
    ext.b_s(0x67, 'sl_empty')
    ext.emit(0xb7fc, 0x00ff, 0xc500)                # cmpa.l #$ffc500, a3 (recent list?)
    ext.b_s(0x66, 'sl_show')
    ext.emit(0x24bc, 0, 0)                          # move.l #str_clear_recent, (a2)
    ext.fixups.append((len(ext.buf) - 4, 'str_clear_recent', 'abs32'))
    ext.emit(0x42aa, 0x0004)                        # clr.l 4(a2)
    ext.emit(0x5244)                                # addq.w #1, d4
    ext.label('sl_show')
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x2f04)                                # move.l d4, -(a7)
    ext.emit(0x486f, 0x0008)                        # pea.l 8(a7) (menu)
    ext.emit(0x4eb9, 0x00ff, 0x4834)                # jsr $ff4834.l (menuDraw)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x7200)                                # moveq #0, d1
    ext.emit(0x0c00, 0x00ff)                        # cmpi.b #$ff, d0 (B)
    ext.b_s(0x67, 'sl_exit')
    ext.emit(0xb043)                                # cmp.w d3, d0 ("Limpar recentes"?)
    ext.b_s(0x67, 'sl_clear')
    ext.emit(0x0240, 0x000f, 0xe548)                # andi.w #$f, d0 ; lsl.w #2, d0
    ext.emit(0x4878, 0x0110)                        # pea.l $110.w
    ext.emit(0x486f, 56)                            # pea.l 56(a7) (fat_rec)
    ext.emit(0x2f33, 0x0000)                        # move.l (a3, d0.w), -(a7)
    ext.jsr_label('sramReadBytes')
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x486f, 68)                            # pea.l 68(a7) (fat_rec)
    ext.emit(0x4eb9, 0x00ff, 0x5f22)                # jsr $ff5f22.l (loadRom)
    ext.emit(0x4fef, 0x0014)                        # lea.l $14(a7), a7
    ext.emit(0x7200, 0x1200)                        # moveq #0, d1 ; move.b d0, d1
    ext.b_s(0x66, 'sl_exit')
    ext.emit(0x4eb9, 0x00ff, 0x567e)                # jsr $ff567e.l (startGame)
    ext.emit(0x7200, 0x1200)                        # moveq #0, d1 ; move.b d0, d1
    ext.b_s(0x60, 'sl_exit')
    ext.label('sl_clear')
    ext.emit(0x224b)                                # movea.l a3, a1
    ext.emit(0x7209)                                # moveq #9, d1
    ext.bsr_w('clr_slots')
    ext.bra_w('sl_restart')                         # now empty: shows "Nenhum jogo recente"
    ext.label('sl_empty')
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.emit(0x2f2f, 694 + 8)                       # move.l 702(a7), -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x4834)                # jsr $ff4834.l (menuDraw)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x7200)                                # moveq #0, d1
    ext.label('sl_exit')
    ext.emit(0x2001)                                # move.l d1, d0
    ext.emit(0x4fef, 698)                           # lea.l 698(a7), a7
    ext.emit(0x4cdf, 0x1c1c)                        # movem.l (a7)+, d2-d4/a2-a4
    ext.emit(0x4e75)                                # rts

    # 7. calcRomArtPath(fat_rec in a4)
    ext.label('calcRomArtPath')
    ext.emit(0x48e7, 0x3020)                        # movem.l d2-d3/a2, -(a7)
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x260a)                # jsr $ff260a.l (fatOpenFile)
    ext.emit(0x508f)                                # addq.l #8, a7
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('calcArt_err')
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.emit(0x4879, 0x00ff, 0xc600)                # pea.l $ffc600.l
    ext.emit(0x4eb9, 0x00ff, 0x23c6)                # jsr $ff23c6.l (fatRead)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('calcArt_err')

    ext.emit(0x41f9, 0x00ff, 0xc600)                # lea.l $ffc600.l, a0
    ext.emit(0x7400)                                # moveq #0, d2
    ext.emit(0x363c, 0x00ff)                        # move.w #255, d3
    ext.label('hash_word_loop')
    ext.emit(0xeb9a)                                # rol.l #5, d2
    ext.emit(0x3018)                                # move.w (a0)+, d0
    ext.emit(0xb142)                                # eor.w d0, d2
    ext.dbra(3, 'hash_word_loop')

    ext.lea_label(0, 'str_art_prefix')
    ext.emit(0x43f9, 0x00ff, 0xc580)                # lea.l $ffc580.l, a1
    ext.emit(0x7609)                                # moveq #9, d3
    ext.label('copy_art_pfx')
    ext.emit(0x12d8)                                # move.b (a0)+, (a1)+
    ext.dbra(3, 'copy_art_pfx')

    ext.emit(0x7607)                                # moveq #7, d3
    ext.label('fmt_hex_loop')
    ext.emit(0xe99a)                                # rol.l #4, d2
    ext.emit(0x700f)                                # moveq #$f, d0
    ext.emit(0xc002)                                # and.b d2, d0
    ext.emit(0x0c00, 0x0009)                        # cmpi.b #9, d0
    ext.bls_w('fmt_hex_dig')
    ext.emit(0x5e00)                                # addq.b #7, d0
    ext.label('fmt_hex_dig')
    ext.emit(0x0600, 0x0030)                        # addi.b #$30, d0
    ext.emit(0x12c0)                                # move.b d0, (a1)+
    ext.dbra(3, 'fmt_hex_loop')

    ext.emit(0x12fc, 0x002e)                        # move.b #'.', (a1)+
    ext.emit(0x12fc, 0x0041)                        # move.b #'A', (a1)+
    ext.emit(0x12fc, 0x0052)                        # move.b #'R', (a1)+
    ext.emit(0x12fc, 0x0054)                        # move.b #'T', (a1)+
    ext.emit(0x4211)                                # clr.b (a1)

    ext.emit(0x33f9, 0x00ff, 0xc78e, 0x00ff, 0xc57c)# move.w $ffc78e.l, $ffc57c.l
    ext.emit(0x41f9, 0x00ff, 0xc700)                # lea.l $ffc700.l, a0
    ext.emit(0x363c, 0x00ff)                        # move.w #255, d3
    ext.label('san_hdr_loop')
    ext.emit(0x1010)                                # move.b (a0), d0
    ext.emit(0x0c00, 0x0020)                        # cmpi.b #$20, d0
    ext.bcs_w('san_hdr_spc')
    ext.emit(0x0c00, 0x007f)                        # cmpi.b #$7f, d0
    ext.bcs_w('san_hdr_ok')
    ext.label('san_hdr_spc')
    ext.emit(0x10bc, 0x0020)                        # move.b #$20, (a0)
    ext.label('san_hdr_ok')
    ext.emit(0x5288)                                # addq.l #1, a0
    ext.dbra(3, 'san_hdr_loop')
    ext.emit(0x7000)                                # moveq #0, d0
    ext.label('calcArt_err')
    ext.emit(0x4cdf, 0x040c)                        # movem.l (a7)+, d2-d3/a2
    ext.emit(0x4e75)                                # rts

    # 8a. clsTitle(a4 = fat_rec): blank screen, banner, game name centred on row 3 (max 38 chars)
    ext.label('clsTitle')
    ext.b_s(0x61, 'clsBanner')
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w (Pal 1 gold)
    ext.emit(0x4eb9, 0x00ff, 0x30a0)                # jsr $ff30a0.l (gSetPal)
    ext.emit(0x41ec, 0x000e)                        # lea.l $e(a4), a0 (name)
    ext.emit(0x43f9, 0x00ff, 0xd720)                # lea.l $ffd720.l, a1 (free RAM)
    ext.emit(0x7025)                                # moveq #37, d0
    ext.label('ct_copy')
    ext.emit(0x12d8)                                # move.b (a0)+, (a1)+
    ext.dbeq(0, 'ct_copy')
    ext.emit(0x4211)                                # clr.b (a1)
    ext.emit(0x4878, 0x0003)                        # pea.l $3.w (y=3)
    ext.emit(0x4879, 0x00ff, 0xd720)                # pea.l $ffd720.l
    ext.emit(0x4eb9, 0x00ff, 0x35fe)                # jsr $ff35fe.l (gPrintCenter)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4e75)                                # rts

    # 8b. clsBanner: blank screen + RETROGAMER POA banner (palette left at 2)
    ext.label('clsBanner')
    ext.emit(0x4eb9, 0x00ff, 0x3802)                # jsr $ff3802.l (gCleanPlan)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w (Pal 2)
    ext.emit(0x4eb9, 0x00ff, 0x30a0)                # jsr $ff30a0.l (gSetPal)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w (y=1)
    ext.emit(0x4878, 0x000c)                        # pea.l $c.w (x=12, centred)
    ext.pea_label('str_banner_tiles')
    ext.emit(0x4eb9, 0x00ff, 0x3556)                # jsr $ff3556.l (gPrintAt)
    ext.emit(0x4fef, 0x0010)                        # lea.l $10(a7), a7
    ext.emit(0x4e75)                                # rts

    # 8. showRomInfo (Compact table-driven ROM Header Info screen)
    ext.label('showRomInfo')
    ext.emit(0x48e7, 0x3838)                        # movem.l d2-d4/a2-a4, -(a7)
    ext.emit(0x286f, 0x001c)                        # movea.l $1c(a7), a4 (fat_rec)
    ext.bsr_w('calcRomArtPath')
    ext.bsr_w('clsBanner')
    ext.emit(0x45f9, 0x00ff, 0x3556)                # lea.l $ff3556.l, a2 (gPrintAt)
    ext.emit(0x47f9, 0x00ff, 0x30a0)                # lea.l $ff30a0.l, a3 (gSetPal)
    ext.emit(0x4878, 0x0003)                        # pea.l $3.w (y=3)
    ext.emit(0x4878, 0x0006)                        # pea.l $6.w (x=6)
    ext.pea_label('str_ri_title')
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7

    # Loop over 8 entries in ri_table (each entry = 8 bytes: word y, word max_len, word hdr_off, word lbl_off)
    ext.lea_label(4, 'ri_table')                    # lea ri_table, a4
    ext.emit(0x7807)                                # moveq #7, d4 (8 rows)
    ext.label('ri_loop')
    ext.emit(0x341c)                                # move.w (a4)+, d2 (y)
    ext.emit(0x361c)                                # move.w (a4)+, d3 (max_len)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w (Pal 2)
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x2f02)                                # move.l d2, -(a7) (y)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w (x=2)
    ext.emit(0x2f1c)                                # move.l (a4)+, -(a7) (label_ptr)
    ext.emit(0x4e92)                                # jsr (a2) (gPrintAt)
    ext.emit(0x4297)                                # clr.l (a7) (Pal 0)
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x2f03)                                # move.l d3, -(a7) (max_len)
    ext.emit(0x2f02)                                # move.l d2, -(a7) (y)
    ext.emit(0x4878, 0x000d)                        # pea.l $d.w (x=13)
    ext.emit(0x2f1c)                                # move.l (a4)+, -(a7) (hdr_addr)
    ext.emit(0x4eb9, 0x00ff, 0x3526)                # jsr $ff3526.l (gPrintMaxLenAt)
    ext.emit(0x4fef, 0x0020)                        # lea.l $20(a7), a7
    ext.dbra(4, 'ri_loop')

    # Row 19: Checksum
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x4878, 0x0013)                        # pea.l $13.w (y=19)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w (x=2)
    ext.pea_label('str_ri_chk')
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4297)                                # clr.l (a7)
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x4878, 0x0013)                        # pea.l $13.w (y=19)
    ext.emit(0x4878, 0x000d)                        # pea.l $d.w (x=13)
    ext.emit(0x4280)                                # clr.l d0
    ext.emit(0x3039, 0x00ff, 0xc57c)                # move.w $ffc57c.l, d0
    ext.emit(0x2f00)                                # move.l d0, -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x36b2)                # jsr $ff36b2.l (gPrintHex16At)
    ext.emit(0x4fef, 0x001c)                        # lea.l $1c(a7), a7

    # Row 21: Artwork Path ($ffc580)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x4878, 0x0015)                        # pea.l $15.w (y=21)
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w (x=2)
    ext.pea_label('str_ri_art')
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w (Pal 1 Gold)
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x4878, 0x0015)                        # pea.l $15.w (y=21)
    ext.emit(0x4878, 0x000d)                        # pea.l $d.w (x=13)
    ext.emit(0x4879, 0x00ff, 0xc580)                # pea.l $ffc580.l
    ext.emit(0x4e92)                                # jsr (a2)
    ext.emit(0x4fef, 0x0020)                        # lea.l $20(a7), a7

    # Row 25: Press any key
    ext.emit(0x4878, 0x0002)                        # pea.l $2.w
    ext.emit(0x4e93)                                # jsr (a3)
    ext.emit(0x4878, 0x0019)                        # pea.l $19.w (y=25)
    ext.pea_label('str_press_key')
    ext.emit(0x4eb9, 0x00ff, 0x35fe)                # jsr $ff35fe.l (gPrintCenter)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7

    ext.emit(0x4eb9, 0x00ff, 0x33b6)                # jsr $ff33b6.l (gRepaint)
    ext.emit(0x4eb9, 0x00ff, 0x6224)                # jsr $ff6224.l (edWaitKey)
    ext.emit(0x7000)                                # moveq #0, d0
    ext.emit(0x4cdf, 0x1c1c)                        # movem.l (a7)+, d2-d4/a2-a4
    ext.emit(0x4e75)                                # rts

    # 9a. loadArtVram(a4 = fat_rec): box art of the ROM -> palette 3 + tiles 0x100.. ; d0 = 0 when loaded
    ext.label('loadArtVram')
    ext.bsr_w('calcRomArtPath')
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('lav_ret')
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x4879, 0x00ff, 0xc580)                # pea.l $ffc580.l
    ext.emit(0x4eb9, 0x00ff, 0x2f48)                # jsr $ff2f48.l (fatOpenFileByName)
    ext.emit(0x508f)                                # addq.l #8, a7
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('lav_ret')
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.emit(0x4878, 0x0007)                        # pea.l $7.w (7 sectors)
    ext.emit(0x4879, 0x00ff, 0xc800)                # pea.l $ffc800.l
    ext.emit(0x4eb9, 0x00ff, 0x23c6)                # jsr $ff23c6.l (fatRead)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('lav_ret')
    ext.emit(0x45f9, 0x00ff, 0xc802)                # lea.l $ffc802.l, a2
    ext.emit(0x7601)                                # moveq #1, d3
    ext.label('rfm_pal_loop')
    ext.emit(0x4280)                                # clr.l d0
    ext.emit(0x301a)                                # move.w (a2)+, d0
    ext.emit(0x2f00)                                # move.l d0, -(a7)
    ext.emit(0x2f03)                                # move.l d3, -(a7)
    ext.emit(0x4878, 0x0003)                        # pea.l $3.w
    ext.emit(0x4eb9, 0x00ff, 0x65ae)                # jsr $ff65ae.l (vdpSetPal)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x5243)                                # addq.w #1, d3
    ext.emit(0x0c43, 0x000e)                        # cmpi.w #14, d3
    ext.bls_w('rfm_pal_loop')
    ext.emit(0x4878, 0x0d80)                        # pea.l $d80.w
    ext.emit(0x4878, 0x2000)                        # pea.l $2000.w (tiles 0x100.., char codes stay free)
    ext.emit(0x4879, 0x00ff, 0xc820)                # pea.l $ffc820.l
    ext.emit(0x4eb9, 0x00ff, 0x651a)                # jsr $ff651a.l (vdpVramWrite)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x7000)                                # moveq #0, d0
    ext.label('lav_ret')
    ext.emit(0x4e75)                                # rts

    # 9b. drawArtTiles lives in blkA (old English file-menu strings, see below)

    # 9c. browseIdle: replaces the browser's "wait for a button" loop (jsr at 0xFF0E0C).
    #     Returns with d0 = pad like ff620a. ff620a waits for the next vblank, so each loop
    #     iteration is one frame: after PREVIEW_FRAMES idle frames on a file the cover is shown
    #     at the centre right; the key that ends the wait first redraws the page (wiping it).
    ext.label('browseIdle')
    ext.emit(0x33c4, 0x00ff, 0xc5a2)                # move.w d4, $ffc5a2.l (cursor, for L/R in the file menu)
    ext.emit(0x4eb9, 0x00ff, 0x620a)                # jsr $ff620a.l (read pad, waits 1 vblank)
    ext.emit(0x4a40)                                # tst.w d0
    ext.bne_w('bi_ret')
    ext.emit(0x48e7, 0x3e38)                        # movem.l d2-d6/a2-a4, -(a7)
    ext.emit(0x7600)                                # moveq #0, d3 (idle frames)
    ext.emit(0x7c00)                                # moveq #0, d6 (cover drawn)
    ext.label('bi_wait')
    ext.emit(0x4247)                                # clr.w d7 (browser key repeat counter, as stock)
    ext.emit(0x4eb9, 0x00ff, 0x620a)                # jsr $ff620a.l
    ext.emit(0x4a40)                                # tst.w d0
    ext.bne_w('bi_pressed')
    ext.emit(0x5243)                                # addq.w #1, d3
    ext.emit(0x0c43, PREVIEW_FRAMES)                # cmpi.w #PREVIEW_FRAMES, d3
    ext.bne_w('bi_wait')                            # fires exactly once per idle period
    ext.bsr_w('previewEntry')
    ext.emit(0x7600 | (PREVIEW_FRAMES + 1))         # moveq #PREVIEW_FRAMES+1, d3 (past the trigger)
    ext.bra_w('bi_wait')
    ext.label('bi_pressed')
    ext.emit(0x4a06)                                # tst.b d6
    ext.beq_w('bi_out')
    ext.emit(0x2f00)                                # move.l d0, -(a7) (keep the pad state)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w (full redraw)
    ext.emit(0x2f04)                                # move.l d4, -(a7) (cursor)
    ext.emit(0x4eb9, 0x00ff, 0x08e8)                # jsr $ff08e8.l (draw page: wipes the cover)
    ext.emit(0x508f)                                # addq.l #8, a7
    ext.emit(0x201f)                                # move.l (a7)+, d0
    ext.label('bi_out')
    ext.emit(0x4cdf, 0x1c7c)                        # movem.l (a7)+, d2-d6/a2-a4
    ext.label('bi_ret')
    ext.emit(0x4e75)                                # rts

    # 9d. previewEntry(d4 = cursor index): cover of that file at x=27, y=9 (rows 9-17)
    ext.label('previewEntry')
    ext.emit(0x2279, 0x00ff, 0xc46c)                # movea.l $ffc46c.l, a1 (dir_hdr)
    ext.emit(0x3011)                                # move.w (a1), d0 (entry count)
    ext.emit(0xb044)                                # cmp.w d4, d0
    ext.bls_w('pe_no')
    ext.emit(0x7000)                                # moveq #0, d0
    ext.emit(0x3004)                                # move.w d4, d0
    ext.emit(0xe588)                                # lsl.l #2, d0
    ext.emit(0x41f1, 0x0800)                        # lea.l (a1, d0.l), a0
    ext.emit(0x2068, 0x3016)                        # movea.l $3016(a0), a0 (dir entry)
    ext.emit(0x4a68, 0x000a)                        # tst.w $a(a0) (directory?)
    ext.bne_w('pe_no')
    ext.emit(0x4879, 0x00ff, 0xd600)                # pea.l $ffd600.l (fat_rec buffer)
    ext.emit(0x2f08)                                # move.l a0, -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x2872)                # jsr $ff2872.l (fatGetRec)
    ext.emit(0x508f)                                # addq.l #8, a7
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('pe_no')
    ext.emit(0x49f9, 0x00ff, 0xd600)                # lea.l $ffd600.l, a4
    ext.bsr_w('loadArtVram')
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('pe_no')
    ext.emit(0x4eb9, 0x00ff, 0x620a)                # jsr $ff620a.l (pressed while loading?)
    ext.emit(0x4a40)                                # tst.w d0
    ext.bne_w('pe_no')
    ext.emit(0x7c01)                                # moveq #1, d6 (cover drawn)
    ext.emit(0x7a1b)                                # moveq #27, d5
    ext.emit(0x7c09)                                # moveq #9, d6
    ext.bsr_w('drawArtTiles')
    ext.emit(0x4eb9, 0x00ff, 0x33b6)                # jsr $ff33b6.l (gRepaint: the page is double buffered)
    ext.label('pe_no')
    ext.emit(0x4e75)                                # rts

    # 9. romFileMenu_v2
    ext.label('romFileMenu_v2')
    ext.emit(0x48e7, 0x3e38)                        # movem.l d2-d6/a2-a4, -(a7)
    ext.emit(0x286f, 0x0024)                        # movea.l $24(a7), a4 (fat_rec)
    ext.label('rfm_restart')
    ext.bsr_w('clsTitle')                           # full screen, like the v1 game menu
    ext.bsr_w('loadArtVram')
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('rfm_draw_menu')

    ext.emit(0x4878, 0x000a)                        # pea.l $a.w (h = 10)
    ext.emit(0x4878, 0x000c)                        # pea.l $c.w (w = 12)
    ext.emit(0x4878, 0x0007)                        # pea.l $7.w (y = 7)
    ext.emit(0x4878, 0x0019)                        # pea.l $19.w (x = 25)
    ext.emit(0x4eb9, 0x00ff, 0x4778)                # jsr $ff4778.l (gDrawBox)
    ext.emit(0x4fef, 0x0010)                        # lea.l $10(a7), a7

    ext.emit(0x4878, 0x0003)                        # pea.l $3.w (Pal 3)
    ext.emit(0x4eb9, 0x00ff, 0x30a0)                # jsr $ff30a0.l (gSetPal)
    ext.emit(0x4878, 0x0007)                        # pea.l $7.w (y = 7)
    ext.emit(0x4878, 0x001c)                        # pea.l $1c.w (x = 28)
    ext.pea_label('str_boxart_hdr')
    ext.emit(0x4eb9, 0x00ff, 0x3556)                # jsr $ff3556.l (gPrintAt)
    ext.emit(0x4fef, 0x0010)                        # lea.l $10(a7), a7

    ext.emit(0x7a19)                                # moveq #25, d5
    ext.emit(0x7c08)                                # moveq #8, d6
    ext.bsr_w('drawArtTiles')

    ext.emit(0x13fc, 0x0016, 0x00ff, 0x4895)        # move.b #$16, $ff4895.l
    ext.emit(0x13fc, 0x0016, 0x00ff, 0x361f)        # move.b #$16, $ff361f.l

    ext.label('rfm_draw_menu')
    ext.emit(0x13fc, 0x0001, 0x00ff, 0xc5a0)        # move.b #1, $ffc5a0.l (menuDraw returns L/R)
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x4878, 0x0005)                        # pea.l $5.w
    ext.pea_label('menu_rom_5')
    ext.emit(0x4eb9, 0x00ff, 0x4834)                # jsr $ff4834.l (menuDraw)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x4239, 0x00ff, 0xc5a0)                # clr.b $ffc5a0.l
    ext.emit(0x13fc, 0x0028, 0x00ff, 0x4895)        # move.b #$28, $ff4895.l
    ext.emit(0x13fc, 0x0028, 0x00ff, 0x361f)        # move.b #$28, $ff361f.l
    ext.emit(0x0c40, 0x0081)                        # cmpi.w #$81, d0 (left: previous game)
    ext.beq_w('rfm_lr')
    ext.emit(0x0c40, 0x0082)                        # cmpi.w #$82, d0 (right: next game)
    ext.beq_w('rfm_lr')

    ext.emit(0x4a40)                                # tst.w d0
    ext.bne_w('rfm_chk1')
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.jsr_label('loadRomWithRecent')
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.emit(0x4281)                                # clr.l d1
    ext.emit(0x3200)                                # move.w d0, d1
    ext.emit(0x4a40)                                # tst.w d0
    ext.bne_w('rfm_exit')
    ext.emit(0x4eb9, 0x00ff, 0x567e)                # jsr $ff567e.l (startGame)
    ext.emit(0x4281)                                # clr.l d1
    ext.emit(0x3200)                                # move.w d0, d1
    ext.bra_w('rfm_exit')

    ext.label('rfm_chk1')
    ext.emit(0x0c40, 0x0001)                        # cmpi.w #1, d0
    ext.bne_w('rfm_chk2')
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.jsr_label('loadRomWithRecent')
    ext.bra_w('rfm_pop_ret')

    ext.label('rfm_chk2')
    ext.emit(0x0c40, 0x0002)                        # cmpi.w #2, d0
    ext.bne_w('rfm_chk3')
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.bsr_w('addFavorite')
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.emit(0x42a7)                                # clr.l -(a7)
    ext.emit(0x4878, 0x0001)                        # pea.l $1.w
    ext.pea_label('menu_fav_saved')
    ext.emit(0x4eb9, 0x00ff, 0x4834)                # jsr $ff4834.l (menuDraw)
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.bra_w('rfm_ret0')

    ext.label('rfm_chk3')
    ext.emit(0x0c40, 0x0003)                        # cmpi.w #3, d0
    ext.bne_w('rfm_chk4')
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.bsr_w('showRomInfo')
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.bra_w('rfm_ret0')

    ext.label('rfm_chk4')
    ext.emit(0x0c40, 0x0004)                        # cmpi.w #4, d0
    ext.bne_w('rfm_ret0')
    ext.emit(0x2f0c)                                # move.l a4, -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x5194)                # jsr $ff5194.l (hexView)
    ext.label('rfm_pop_ret')
    ext.emit(0x4281)                                # clr.l d1
    ext.emit(0x3200)                                # move.w d0, d1
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.bra_w('rfm_exit')

    ext.label('rfm_ret0')
    ext.emit(0x7200)                                # moveq #0, d1
    ext.label('rfm_exit')
    ext.emit(0x2001)                                # move.l d1, d0
    ext.bsr_w('rfmFixCursor')                       # browser cursor follows L/R
    ext.emit(0x4cdf, 0x1c7c)                        # movem.l (a7)+, d2-d6/a2-a4
    ext.emit(0x4e75)                                # rts

    # 10. mainMenu_v2 (7-item Main Menu)
    ext.label('mainMenu_v2')
    ext.emit(0x4e56, 0xee10)                        # link.w a6, #$ee10
    ext.emit(0x48e7, 0x3020)                        # movem.l d2-d3/a2, -(a7)
    ext.emit(0x4242)                                # clr.w d2
    ext.emit(0x486e, 0xee80)                        # pea.l -$1180(a6)
    ext.emit(0x4eb9, 0x00ff, 0x32c2)                # jsr $ff32c2.l (saveScreen)
    ext.label('mm_loop')
    ext.emit(0x4257)                                # clr.w (a7)
    ext.emit(0x3f42, 0x0002)                        # move.w d2, $2(a7)
    ext.emit(0x4878, 0x0007)                        # pea.l $7.w (7 items!)
    ext.pea_label('menu_main_7')
    ext.emit(0x4eb9, 0x00ff, 0x4834)                # jsr $ff4834.l (menuDraw)
    ext.emit(0x3400)                                # move.w d0, d2
    ext.emit(0x4fef, 0x000c)                        # lea.l $c(a7), a7
    ext.emit(0x260e)                                # move.l a6, d3
    ext.emit(0x0683, 0xffff, 0xee80)                # addi.l #$ffffee80, d3
    ext.emit(0x41f9, 0x00ff, 0x333c)                # lea.l $ff333c.l, a0 (restoreScreen)
    ext.emit(0x0c40, 0xffff)                        # cmpi.w #$ffff, d0
    ext.bne_w('mm_selected')
    ext.emit(0x2f03)                                # move.l d3, -(a7)
    ext.emit(0x4e90)                                # jsr (a0)
    ext.emit(0x7000)                                # moveq #0, d0
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.bra_w('mm_exit')

    ext.label('mm_selected')
    ext.emit(0x2f03)                                # move.l d3, -(a7)
    ext.emit(0x2448)                                # movea.l a0, a2
    ext.emit(0x4e90)                                # jsr (a0)
    ext.emit(0x588f)                                # addq.l #4, a7
    ext.emit(0x4a42)                                # tst.w d2 (0 = Opções)
    ext.bne_w('mm_chk1')
    ext.emit(0x4eb9, 0x00ff, 0x49b6)                # jsr $ff49b6.l (optionsMenu_v2)
    ext.bra_w('mm_restore')

    ext.label('mm_chk1')
    ext.emit(0x0c42, 0x0001)                        # cmpi.w #1, d2 (1 = Jogos Recentes)
    ext.bne_w('mm_chk2')
    ext.bsr_w('recentlyPlayedMenu')
    ext.label('mm_chk_launch_err')
    ext.emit(0x4a00)                                # tst.b d0
    ext.beq_w('mm_restore')
    ext.emit(0x0280, 0x0000, 0x00ff)                # andi.l #$ff, d0
    ext.bra_w('mm_exit')

    ext.label('mm_chk2')
    ext.emit(0x0c42, 0x0002)                        # cmpi.w #2, d2 (2 = Favoritos)
    ext.bne_w('mm_chk3')
    ext.bsr_w('favoritesMenu')
    ext.bra_w('mm_chk_launch_err')

    ext.label('mm_chk3')
    ext.emit(0x0c42, 0x0003)                        # cmpi.w #3, d2 (3 = Jogo Aleatório)
    ext.bne_w('mm_chk4')
    ext.jsr_label('playRandomGame')
    ext.bra_w('mm_chk_launch_err')

    ext.label('mm_chk4')
    ext.emit(0x0c42, 0x0004)                        # cmpi.w #4, d2 (4 = Cheats)
    ext.bne_w('mm_chk5')
    ext.emit(0x4241)                                # clr.w d1
    ext.label('mm_clr_cheats')
    ext.emit(0x4280)                                # clr.l d0
    ext.emit(0x3001)                                # move.w d1, d0
    ext.emit(0x41f6, 0x0800)                        # lea.l (a6, d0.l), a0
    ext.emit(0x4228, 0xee70)                        # clr.b -$1190(a0)
    ext.emit(0x2001)                                # move.l d1, d0
    ext.emit(0xe588)                                # lsl.l #2, d0
    ext.emit(0x0280, 0x0003, 0xfffc)                # andi.l #$3fffc, d0
    ext.emit(0x41f6, 0x0800)                        # lea.l (a6, d0.l), a0
    ext.emit(0x42a8, 0xee10)                        # clr.l -$11f0(a0)
    ext.emit(0x2001)                                # move.l d1, d0
    ext.emit(0xd080)                                # add.l d0, d0
    ext.emit(0x0280, 0x0001, 0xfffe)                # andi.l #$1fffe, d0
    ext.emit(0x41f6, 0x0800)                        # lea.l (a6, d0.l), a0
    ext.emit(0x4268, 0xee50)                        # clr.w -$11b0(a0)
    ext.emit(0x5241)                                # addq.w #1, d1
    ext.emit(0x0c41, 0x000f)                        # cmpi.w #$f, d1
    ext.bls_w('mm_clr_cheats')
    ext.emit(0x486e, 0xee10)                        # pea.l -$11f0(a6)
    ext.emit(0x2f03)                                # move.l d3, -(a7)
    ext.emit(0x4eb9, 0x00ff, 0x4362)                # jsr $ff4362.l (cheatsMenu)
    ext.emit(0x508f)                                # addq.l #8, a7
    ext.bra_w('mm_restore')

    ext.label('mm_chk5')
    ext.emit(0x0c42, 0x0005)                        # cmpi.w #5, d2 (5 = Info do Sistema)
    ext.bne_w('mm_chk6')
    ext.emit(0x4eb9, 0x00ff, 0x4b54)                # jsr $ff4b54.l (deviceInfo)
    ext.bra_w('mm_restore')

    ext.label('mm_chk6')
    ext.emit(0x0c42, 0x0006)                        # cmpi.w #6, d2 (6 = Créditos)
    ext.bne_w('mm_restore')
    ext.jsr_label('aboutScreen_ptbr')

    ext.label('mm_restore')
    ext.emit(0x486e, 0xee80)                        # pea.l -$1180(a6)
    ext.emit(0x4e92)                                # jsr (a2) (saveScreen)
    ext.bra_w('mm_loop')

    ext.label('mm_exit')
    ext.emit(0x4cee, 0x040c, 0xee04)                # movem.l -$11fc(a6), d2-d3/a2
    ext.emit(0x4e5e)                                # unlk a6
    ext.emit(0x4e75)                                # rts

    ext.label('call_mainMenu_from_browser')
    ext.bsr_w('mainMenu_v2')
    ext.emit(0x4a00)                                # tst.b d0
    ext.bne_w('browser_err_exit')
    ext.emit(0x4ef9, 0x00ff, 0x0ff6)                # jmp $ff0ff6.l
    ext.label('browser_err_exit')
    ext.emit(0x4ef9, 0x00ff, 0x0f3a)                # jmp $ff0f3a.l

    code_end_off = len(ext.buf)

    # =========================================================================
    # Data Tables, 2bpp Font/Banner Tiles, Menu Pointer Tables & PT-BR Strings
    # =========================================================================
    ext.label('lut_2bpp_to_4bpp')
    ext.emit_b(bytes([0x00, 0x01, 0x02, 0x0F]))

    ext.label('theme_pal_table')
    ext.emit(0x0000, 0x0c88, 0x0222, 0x02aa)        # 0: PADRÃO
    ext.emit(0x0002, 0x022a, 0x0006, 0x00ee)        # 1: RG POA
    ext.emit(0x0200, 0x0a40, 0x0420, 0x00e6)        # 2: SEGA 16
    ext.emit(0x0202, 0x0a28, 0x0404, 0x0ee0)        # 3: OUTRUN

    # ROM Info table: 8 entries of (word y, word max_len, long label_ptr, long hdr_addr)
    ext.label('ri_table')
    ri_entries = [
        (5,  25, 'str_ri_us',  0x00FFC750),
        (6,  23, 'str_empty',  0x00FFC769),
        (8,  25, 'str_ri_jp',  0x00FFC720),
        (9,  23, 'str_empty',  0x00FFC739),
        (11, 16, 'str_ri_sys', 0x00FFC700),
        (13, 16, 'str_ri_cop', 0x00FFC710),
        (15, 14, 'str_ri_ser', 0x00FFC780),
        (17, 16, 'str_ri_reg', 0x00FFC7F0),
    ]
    for y, mlen, lbl_name, hdr_addr in ri_entries:
        ext.emit(y, mlen)
        lbl_off = len(ext.buf)
        ext.emit_l(0, hdr_addr)
        ext.fixups.append((lbl_off, lbl_name, 'abs32'))

    ext.label('tiles_2bpp_data')
    ext.emit_b(build_font_and_banner_2bpp())

    def emit_menu_table(table_label, item_labels):
        ext.label(table_label)
        base_off = len(ext.buf)
        ext.emit_l(*([0] * len(item_labels)))
        for idx, lbl in enumerate(item_labels):
            ext.fixups.append((base_off + idx * 4, lbl, 'abs32'))

    emit_menu_table('menu_main_7', [
        'str_mm_title',
        'str_opt_title',
        'str_recent_title',
        'str_fav_title',
        'str_rand_title',
        'str_mm_cheats',
        'str_mm_devinfo',
        'str_mm_about',
    ])

    emit_menu_table('menu_rom_5', [
        'str_file_menu',
        'str_load_start',
        'str_load_only',
        'str_add_fav',
        'str_rom_info',
        'str_hex_view',
    ])

    emit_menu_table('menu_options_5', [
        'str_opt_title',
        'str_opt_region',
        'str_opt_megakey',
        'str_opt_sram',
        'str_opt_rst',
        'str_opt_theme',
    ])

    emit_menu_table('menu_no_recent', ['str_recent_title', 'str_no_recent'])
    emit_menu_table('menu_no_fav',    ['str_fav_title',    'str_no_fav'])
    emit_menu_table('menu_fav_saved', ['str_fav_title',    'str_fav_saved'])
    emit_menu_table('menu_no_rand',   ['str_rand_title',   'str_no_files'])

    emit_menu_table('theme_names_ptrs', [
        'str_thm_0',
        'str_thm_1',
        'str_thm_2',
        'str_thm_3',
    ])

    # Strings
    ext.label('str_empty')
    ext.emit_str(b'')

    ext.label('str_banner_tiles')
    ext.emit_str(bytes(range(0x88, 0x98)))

    ext.label('str_art_prefix')
    ext.emit_str(b'/EDMD/ART/')

    ext.label('str_boxart_hdr')
    ext.emit_str(b'Boxart')

    # File & Main Menus
    ext.label('str_file_menu')
    ext.emit_str(b'Menu Arquivo')
    ext.label('str_load_cheats')
    ext.emit_str(b'Carregar Cheats')
    ext.label('str_hex_view')
    ext.emit_str(b'Ver em Hex')
    ext.label('str_cancel')
    ext.emit_str(b'Cancelar')
    ext.label('str_file_to_sram')
    ext.emit_str(b' Arquivo -> SRAM ')
    ext.label('str_sram_to_file')
    ext.emit_str(b' SRAM -> Arquivo ')
    ext.label('str_load_start')
    ext.emit_str(b'Carregar e Jogar')
    ext.label('str_load_only')
    ext.emit_str(b'S\x86 Carregar')
    ext.label('str_add_fav')
    ext.emit_str(b'Favoritar Jogo')
    ext.label('str_rom_info')
    ext.emit_str(b'Info da ROM')
    ext.label('str_unzip_rom')
    ext.emit_str(b'Descompacte o arquivo ROM')

    # Browser UI
    ext.label('str_page')
    ext.emit_str(b'P\x83g. ')
    ext.label('str_of')
    ext.emit_str(b' de ')
    ext.label('str_no_files')
    ext.emit_str(b'Pasta vazia')

    # Cheats UI
    ext.label('str_apply_codes_q')
    ext.emit_str(b'Aplicar c\x86digos?')
    ext.label('str_apply')
    ext.emit_str(b'Aplicar')
    ext.label('str_modify')
    ext.emit_str(b'Editar')
    ext.label('str_flash_patch')
    ext.emit_str(b'Aplicando cheats...')
    ext.label('str_raw_code')
    ext.emit_str(b'C\x86d. RAW')
    ext.label('str_gg_code')
    ext.emit_str(b'C\x86d. GG')
    ext.label('str_cheats_menu')
    ext.emit_str(b'Menu de Cheats')

    # Options Menu
    ext.label('str_opt_title')
    ext.emit_str(b'Op\x80\x82es')
    ext.label('str_opt_region')
    ext.emit_str(b'Regi\x81o Jogo:   %%%%%%%')
    ext.label('str_opt_megakey')
    ext.emit_str(b'MegaKey:       %%%    ')
    ext.label('str_opt_sram')
    ext.emit_str(b'Backup SRAM:   %%%    ')
    ext.label('str_opt_rst')
    ext.emit_str(b'Reset p/ Jogo: %%%    ')
    ext.label('str_opt_theme')
    ext.emit_str(b'Tema Visual:   %%%%%%%')
    ext.label('str_world_7')
    ext.emit_str(b'MUNDO  ')
    ext.label('str_off_7')
    ext.emit_str(b'DESL   ')
    ext.label('str_on_7')
    ext.emit_str(b'LIG    ')
    ext.label('str_thm_0')
    ext.emit_str(b'PADR\x87O ')
    ext.label('str_thm_1')
    ext.emit_str(b'RG POA ')
    ext.label('str_thm_2')
    ext.emit_str(b'SEGA 16')
    ext.label('str_thm_3')
    ext.emit_str(b'OUTRUN ')

    # Main Menu, Recently Played, Favorites, Random Game
    ext.label('str_mm_title')
    ext.emit_str(b'Menu Principal')
    ext.label('str_recent_title')
    ext.emit_str(b'Jogos Recentes')
    ext.label('str_clear_recent')
    ext.emit_str(b'Limpar recentes')
    ext.label('ir_exts')                            # isRomRec: 1 marker + lower-case extension
    for e in ('bin', 'md', 'gen', 'smd', 'sms', '32x'):
        ext.emit_l(int.from_bytes(b'\x01' + e.encode(), 'big'))
    ext.label('str_no_recent')
    ext.emit_str(b'Nenhum jogo recente')
    ext.label('str_fav_title')
    ext.emit_str(b'Favoritos')
    ext.label('str_no_fav')
    ext.emit_str(b'Nenhum favorito salvo')
    ext.label('str_fav_saved')
    ext.emit_str(b'Salvo nos Favoritos!')
    ext.label('str_rand_title')
    ext.emit_str(b'Jogo Aleat\x86rio')
    ext.label('str_mm_cheats')
    ext.emit_str(b'Cheats')
    ext.label('str_mm_devinfo')
    ext.emit_str(b'Info Sistema')
    ext.label('str_mm_about')
    ext.emit_str(b'Cr\x84ditos')

    # ROM Info Screen labels
    ext.label('str_ri_title')
    ext.emit_str(b'Info da ROM (Cabe\x80alho SEGA)')
    ext.label('str_ri_us')
    ext.emit_str(b'Nome US/EU:')
    ext.label('str_ri_jp')
    ext.emit_str(b'Nome JP:')
    ext.label('str_ri_sys')
    ext.emit_str(b'Console:')
    ext.label('str_ri_cop')
    ext.emit_str(b'Copyright:')
    ext.label('str_ri_ser')
    ext.emit_str(b'Serial:')
    ext.label('str_ri_reg')
    ext.emit_str(b'Regi\x81o:')
    ext.label('str_ri_chk')
    ext.emit_str(b'Checksum:')
    ext.label('str_ri_art')
    ext.emit_str(b'Arq. Capa:')

    # System Information
    ext.label('str_sys_info')
    ext.emit_str(b'Info do Sistema')
    ext.label('str_cpld_ver')
    ext.emit_str(b'Vers\x81o CPLD:')
    ext.label('str_bios_ver')
    ext.emit_str(b'Vers\x81o BIOS:')
    ext.label('str_os_ver')
    ext.emit_str(b'Vers\x81o OS:')
    ext.label('str_mod_version')
    ext.emit_str(('PT-BR ' + MOD_VERSION).encode())
    ext.label('str_mk_mode')
    ext.emit_str(b'Modo MegaKey:')
    ext.label('str_sys_type')
    ext.emit_str(b'Tipo Sistema:')
    ext.label('str_asm_date')
    ext.emit_str(b'Data Build:')
    ext.label('str_asm_time')
    ext.emit_str(b'Hora Build:')

    # About / Credits Screen
    ext.label('str_ab_title')
    ext.emit_str(b'EverDrive-MD V3 Flashcart')
    ext.label('str_ab_dev')
    ext.emit_str(b'Desenvolvido por I. Golubovskiy')
    ext.label('str_ab_mod_hdr')
    ext.emit_str(b'Mod PT-BR, Artwork & Favoritos:')
    ext.label('str_ab_mod_2')
    ext.emit_str(b'por Antonio e the Nobre')
    ext.label('str_ab_sup_hdr')
    ext.emit_str(b'Suporte:')
    ext.label('str_ab_sup_1')
    ext.emit_str(b'biokrik@gmail.com')
    ext.label('str_ab_sup_2')
    ext.emit_str(b'http://krikzz.com')
    ext.label('str_ab_ctl_hdr')
    ext.emit_str(b'Controles:')
    ext.label('str_ab_ctl_1')
    ext.emit_str(b'ESQ/DIR - mudar p\x83gina')
    ext.label('str_ab_ctl_2')
    ext.emit_str(b'START - repetir \x86ltimo jogo')
    ext.label('str_ab_ctl_3')
    ext.emit_str(b'A - menu do arquivo + Boxart')
    ext.label('str_ab_ctl_4')
    ext.emit_str(b'B - voltar')
    ext.label('str_ab_ctl_5')
    ext.emit_str(b'C - menu principal')

    # Status & Error Messages
    ext.label('str_fat_init')
    ext.emit_str(b'Iniciando FAT...')
    ext.label('str_err_hdr')
    ext.emit_str(b'ERRO:')
    ext.label('str_err_rom_large')
    ext.emit_str(b'Arquivo ROM muito grande')
    ext.label('str_err_sd_io')
    ext.emit_str(b'Erro de leitura/escrita SD')
    ext.label('str_err_no_fat')
    ext.emit_str(b'Sistema FAT n\x81o encontrado')
    ext.label('str_err_fat')
    ext.emit_str(b'Erro no sistema FAT')
    ext.label('str_err_not_loaded')
    ext.emit_str(b'Nenhum jogo carregado')
    ext.label('str_sram_save')
    ext.emit_str(b'Salvando SRAM...')
    ext.label('str_sram_load')
    ext.emit_str(b'Carregando SRAM...')
    ext.label('str_reg_patch')
    ext.emit_str(b'Aplicando regi\x81o...')
    ext.label('str_rom_type')
    ext.emit_str(b'Tipo ROM: ')
    ext.label('str_unknown_cap')
    ext.emit_str(b'Desconhecido')
    ext.label('str_rom_reg')
    ext.emit_str(b'Regi\x81o ROM: ')
    ext.label('str_world_5')
    ext.emit_str(b'MUNDO')
    ext.label('str_unknown_up')
    ext.emit_str(b'DESCONHECIDO')
    ext.label('str_erase')
    ext.emit_str(b'Apagando... 0x')
    ext.label('str_read_file')
    ext.emit_str(b'Lendo arquivo...')
    ext.label('str_dont_turn_off')
    ext.emit_str(b'  !!!N\x87O DESLIGUE O VIDEOGAME!!!')
    ext.label('str_done')
    ext.emit_str(b'Pronto!')
    ext.label('str_usb_mode')
    ext.emit_str(b'Modo USB')
    ext.label('str_cfg_reset')
    ext.emit_str(b'Configura\x80\x82es restauradas')
    ext.label('str_press_key')
    ext.emit_str(b'Pressione qualquer bot\x81o')

    # =========================================================================
    # Block 5: optionsMenu_v2 in-place at 0xFF49B6..0xFF4B52 (412 bytes)
    # =========================================================================
    opt_asm = Asm68k(0xFF49B6)
    opt_asm.emit(0x48e7, 0x3830)                    # movem.l d2-d4/a2-a3, -(a7)
    opt_asm.emit(0x4244)                            # clr.w d4
    opt_asm.emit(0x760f)                            # moveq #15, d3

    opt_asm.label('opt_refresh')
    opt_asm.emit(0x2479, 0x00ff, 0xc47a)            # movea.l $ffc47a.l, a2
    opt_asm.emit(0x47f9, 0x00ff, 0x5926)            # lea.l $ff5926.l, a3 (edStrCopy: push dst first, src second!)

    # Option 0: Game Region (push dst first!)
    opt_asm.lea_label(0, 'str_opt_region')
    opt_asm.emit(0x4868, 0x000f)                    # pea.l $f(a0) (dst)
    opt_asm.emit(0x3012)                            # move.w (a2), d0
    opt_asm.emit(0x0c40, 0x00c0)                    # cmpi.w #$c0, d0
    opt_asm.bne_w('opt_reg_80')
    opt_asm.emit(0x4879, 0x00ff, 0x6a52)            # pea.l $ff6a52.l ("EU PAL ")
    opt_asm.bra_w('opt_reg_copy')
    opt_asm.label('opt_reg_80')
    opt_asm.emit(0x0c40, 0x0080)                    # cmpi.w #$80, d0
    opt_asm.bne_w('opt_reg_00')
    opt_asm.emit(0x4879, 0x00ff, 0x6a5a)            # pea.l $ff6a5a.l ("US NTSC")
    opt_asm.bra_w('opt_reg_copy')
    opt_asm.label('opt_reg_00')
    opt_asm.emit(0x4a40)                            # tst.w d0
    opt_asm.bne_w('opt_reg_world')
    opt_asm.emit(0x4879, 0x00ff, 0x6a62)            # pea.l $ff6a62.l ("JP NTSC")
    opt_asm.bra_w('opt_reg_copy')
    opt_asm.label('opt_reg_world')
    opt_asm.emit(0x34bc, 0x0040)                    # move.w #$40, (a2)
    opt_asm.pea_label('str_world_7')
    opt_asm.label('opt_reg_copy')
    opt_asm.emit(0x4e93)                            # jsr (a3) (edStrCopy)
    opt_asm.emit(0x508f)                            # addq.l #8, a7

    # Options 1..3: MegaKey, SRAM Backup, Reset to Game (push dst first!)
    opt_asm.emit(0x7401)                            # moveq #1, d2
    opt_asm.label('opt_bool_loop')
    opt_asm.lea_label(0, 'menu_options_5')
    opt_asm.emit(0x2002)                            # move.l d2, d0
    opt_asm.emit(0xe540)                            # lsl.w #2, d0
    opt_asm.emit(0x2070, 0x0004)                    # movea.l $4(a0, d0.w), a0
    opt_asm.emit(0x4868, 0x000f)                    # pea.l $f(a0) (dst)
    opt_asm.emit(0x2002)                            # move.l d2, d0
    opt_asm.emit(0xd040)                            # add.w d0, d0
    opt_asm.emit(0x4a32, 0x0001)                    # tst.b $1(a2, d0.w)
    opt_asm.bne_w('opt_bool_on')
    opt_asm.pea_label('str_off_7')                  # (src)
    opt_asm.bra_w('opt_bool_copy')
    opt_asm.label('opt_bool_on')
    opt_asm.pea_label('str_on_7')                   # (src)
    opt_asm.label('opt_bool_copy')
    opt_asm.emit(0x4e93)                            # jsr (a3) (edStrCopy)
    opt_asm.emit(0x508f)                            # addq.l #8, a7
    opt_asm.emit(0x5242)                            # addq.w #1, d2
    opt_asm.emit(0x0c42, 0x0003)                    # cmpi.w #3, d2
    opt_asm.bls_w('opt_bool_loop')

    # Option 4: Visual Theme (push dst first, src second!)
    opt_asm.lea_label(0, 'str_opt_theme')
    opt_asm.emit(0x4868, 0x000f)                    # pea.l $f(a0) (dst)
    opt_asm.emit(0x302a, 0x000c)                    # move.w $c(a2), d0
    opt_asm.emit(0x0240, 0x0003)                    # andi.w #3, d0
    opt_asm.emit(0xe540)                            # lsl.w #2, d0
    opt_asm.lea_label(0, 'theme_names_ptrs')
    opt_asm.emit(0x2f30, 0x0000)                    # move.l (a0, d0.w), -(a7) (src)
    opt_asm.emit(0x4e93)                            # jsr (a3) (edStrCopy)
    opt_asm.emit(0x508f)                            # addq.l #8, a7

    opt_asm.emit(0x3f04)                            # move.w d4, -(a7)
    opt_asm.emit(0x4267)                            # clr.w -(a7)
    opt_asm.emit(0x4878, 0x0005)                    # pea.l $5.w
    opt_asm.pea_label('menu_options_5')
    opt_asm.emit(0x4eb9, 0x00ff, 0x4834)            # jsr $ff4834.l (menuDraw)
    opt_asm.emit(0x3800)                            # move.w d0, d4
    opt_asm.emit(0x4fef, 0x000c)                    # lea.l $c(a7), a7
    opt_asm.emit(0x0c40, 0xffff)                    # cmpi.w #$ffff, d0
    opt_asm.beq_w('opt_exit')

    opt_asm.emit(0x4a40)                            # tst.w d0 (0 = Region)
    opt_asm.bne_w('opt_tog_chk4')
    opt_asm.emit(0x3012)                            # move.w (a2), d0
    opt_asm.emit(0x0640, 0x0040)                    # addi.w #$40, d0
    opt_asm.emit(0x0240, 0x00c0)                    # andi.w #$c0, d0
    opt_asm.emit(0x3480)                            # move.w d0, (a2)
    opt_asm.bra_w('opt_refresh')

    opt_asm.label('opt_tog_chk4')
    opt_asm.emit(0x0c40, 0x0004)                    # cmpi.w #4, d0 (4 = Theme)
    opt_asm.bne_w('opt_tog_bool')
    opt_asm.emit(0x302a, 0x000c)                    # move.w $c(a2), d0
    opt_asm.emit(0x5240)                            # addq.w #1, d0
    opt_asm.emit(0x0240, 0x0003)                    # andi.w #3, d0
    opt_asm.emit(0x3540, 0x000c)                    # move.w d0, $c(a2)
    opt_asm.jsr_label('applyTheme')
    opt_asm.bra_w('opt_refresh')

    opt_asm.label('opt_tog_bool')
    opt_asm.emit(0x3004)                            # move.w d4, d0
    opt_asm.emit(0xd040)                            # add.w d0, d0
    opt_asm.emit(0x3232, 0x0000)                    # move.w (a2, d0.w), d1
    opt_asm.emit(0x5241)                            # addq.w #1, d1
    opt_asm.emit(0x0241, 0x0001)                    # andi.w #1, d1
    opt_asm.emit(0x3581, 0x0000)                    # move.w d1, (a2, d0.w)
    opt_asm.bra_w('opt_refresh')

    opt_asm.label('opt_exit')
    opt_asm.emit(0x4cdf, 0x0c1c)                    # movem.l (a7)+, d2-d4/a2-a3
    opt_asm.emit(0x4e75)                            # rts


    # ---- (free space after optionsMenu_v2)
    # addRecentIfRom(fat_rec): loading a .rar/.txt from the browser must not enter the recents
    opt_asm.label('addRecentIfRom')
    opt_asm.emit(0x206f, 0x0004)                        # movea.l $4(a7), a0
    opt_asm.b_s(0x61, 'isRomRec')                       # bsr.s isRomRec
    opt_asm.b_s(0x66, 'ir_ret')                         # bne.s: not a ROM
    opt_asm.jmp_label('addRecentlyPlayed')

    # isRomRec(a0 = fat_rec) -> Z = 1 for a ROM: the extension after the last dot (lower case,
    # max 3 chars, packed behind a 1 marker) is in ir_exts; no dot at all counts as a ROM
    # (the OS truncates long names that cross a directory sector). Uses d0-d1/a0-a1.
    opt_asm.label('isRomRec')
    opt_asm.emit(0x41e8, 0x000e)                        # lea.l $e(a0), a0 (name)
    opt_asm.emit(0x7200)                                # moveq #0, d1
    opt_asm.label('ir_loop')
    opt_asm.emit(0x1018)                                # move.b (a0)+, d0
    opt_asm.b_s(0x67, 'ir_end')
    opt_asm.emit(0x0c00, 0x002e)                        # cmpi.b #'.', d0
    opt_asm.b_s(0x66, 'ir_char')
    opt_asm.emit(0x7201)                                # moveq #1, d1 (marker)
    opt_asm.b_s(0x60, 'ir_loop')
    opt_asm.label('ir_char')
    opt_asm.emit(0x4a81)                                # tst.l d1 (before the first dot?)
    opt_asm.b_s(0x67, 'ir_loop')
    opt_asm.emit(0xe189)                                # lsl.l #8, d1
    opt_asm.emit(0x0000, 0x0020)                        # ori.b #$20, d0 (lower case)
    opt_asm.emit(0x1200)                                # move.b d0, d1
    opt_asm.b_s(0x60, 'ir_loop')
    opt_asm.label('ir_end')
    opt_asm.emit(0x4a81)                                # tst.l d1
    opt_asm.b_s(0x67, 'ir_ret')
    opt_asm.lea_label(1, 'ir_exts')
    opt_asm.emit(0x7005)                                # moveq #5, d0
    opt_asm.label('ir_cmp')
    opt_asm.emit(0xb299)                                # cmp.l (a1)+, d1
    opt_asm.dbeq(0, 'ir_cmp')
    opt_asm.label('ir_ret')
    opt_asm.emit(0x4e75)                                # rts

    # =========================================================================
    # blkA / blkB: old English strings that every reference was moved away from
    #   0xFF6854..0xFF68D0 ("File Menu" .. "ROM file must be unzipped")
    #   0xFF6B08..0xFF6BE7 ("Assembly Date:" .. "C - main menu")
    # =========================================================================
    blkA = Asm68k(0xFF6854)
    # drawArtTiles(d5 = x, d6 = y): writes the 12x9 art tiles 0x100.. straight into the
    # name table (gPrintChar only takes 8-bit codes) with the palette-3 attribute.
    blkA.label('drawArtTiles')
    blkA.emit(0x4878, 0x0003)                       # pea.l $3.w (Pal 3)
    blkA.emit(0x4eb9, 0x00ff, 0x30a0)               # jsr $ff30a0.l (gSetPal -> $ffc476)
    blkA.emit(0x588f)                               # addq.l #4, a7
    blkA.emit(0x363c, 0x0100)                       # move.w #$100, d3
    blkA.label('dat_row')
    blkA.emit(0x2f06)                               # move.l d6, -(a7) (y)
    blkA.emit(0x2f05)                               # move.l d5, -(a7) (x)
    blkA.pea_label('str_empty')
    blkA.emit(0x4eb9, 0x00ff, 0x3556)               # jsr $ff3556.l (gPrintAt: sets the cursor)
    blkA.emit(0x4fef, 0x000c)                       # lea.l $c(a7), a7
    blkA.emit(0x7200)                               # moveq #0, d1
    blkA.emit(0x3239, 0x00ff, 0xc474)               # move.w $ffc474.l, d1 (cursor)
    blkA.emit(0x0241, 0x0fff)                       # andi.w #$fff, d1
    blkA.emit(0xd279, 0x00ff, 0xc472)               # add.w $ffc472.l, d1 (+ plane / back buffer)
    blkA.emit(0x3001)                               # move.w d1, d0
    blkA.emit(0x0240, 0x3fff)                       # andi.w #$3fff, d0
    blkA.emit(0x0040, 0x4000)                       # ori.w #$4000, d0 (VRAM write)
    blkA.emit(0x4840)                               # swap d0
    blkA.emit(0x3001)                               # move.w d1, d0
    blkA.emit(0xe558)                               # rol.w #2, d0
    blkA.emit(0x0240, 0x0003)                       # andi.w #3, d0
    blkA.emit(0x23c0, 0x00c0, 0x0004)               # move.l d0, $c00004.l
    blkA.emit(0x740b)                               # moveq #11, d2
    blkA.label('dat_col')
    blkA.emit(0x3003)                               # move.w d3, d0
    blkA.emit(0x8079, 0x00ff, 0xc476)               # or.w $ffc476.l, d0 (palette attribute)
    blkA.emit(0x33c0, 0x00c0, 0x0000)               # move.w d0, $c00000.l
    blkA.emit(0x5243)                               # addq.w #1, d3
    blkA.dbra(2, 'dat_col')
    blkA.emit(0x5246)                               # addq.w #1, d6
    blkA.emit(0x0c43, 0x016c)                       # cmpi.w #$16c, d3 (108 tiles)
    blkA.bcs_w('dat_row')
    blkA.emit(0x4e75)                               # rts

    blkB = Asm68k(0xFF6B08)
    # menuLR: replaces "move.w $ffc4a4,d0; btst #6,d0" in menuDraw. While $ffc5a0 is set
    # (file menu), LEFT/RIGHT end the menu returning $81/$82; Z = 0 means "return d3".
    blkB.label('menuLR')
    blkB.emit(0x3039, 0x00ff, 0xc4a4)               # move.w $ffc4a4.l, d0
    blkB.emit(0x4a39, 0x00ff, 0xc5a0)               # tst.b $ffc5a0.l
    blkB.beq_w('ml_a')
    blkB.emit(0x0800, 0x0002)                       # btst #2, d0 (left)
    blkB.beq_w('ml_r')
    blkB.emit(0x363c, 0x0081)                       # move.w #$81, d3
    blkB.emit(0x7001)                               # moveq #1, d0
    blkB.emit(0x4e75)                               # rts
    blkB.label('ml_r')
    blkB.emit(0x0800, 0x0003)                       # btst #3, d0 (right)
    blkB.beq_w('ml_a')
    blkB.emit(0x363c, 0x0082)                       # move.w #$82, d3
    blkB.emit(0x7001)                               # moveq #1, d0
    blkB.emit(0x4e75)                               # rts
    blkB.label('ml_a')
    blkB.emit(0x0800, 0x0006)                       # btst #6, d0 (A, as stock)
    blkB.emit(0x4e75)                               # rts

    # rfm_lr (inside romFileMenu_v2, d0 = $81/$82): previous/next file of the folder (skips
    # folders), redraw the browser page on it, then reopen the file menu for it.
    blkB.label('rfm_lr')
    blkB.emit(0x7401)                               # moveq #1, d2
    blkB.emit(0x0c40, 0x0081)                       # cmpi.w #$81, d0
    blkB.bne_w('rl_dir')
    blkB.emit(0x74ff)                               # moveq #-1, d2
    blkB.label('rl_dir')
    blkB.emit(0x2279, 0x00ff, 0xc46c)               # movea.l $ffc46c.l, a1 (dir_hdr)
    blkB.emit(0x3239, 0x00ff, 0xc5a2)               # move.w $ffc5a2.l, d1 (cursor)
    blkB.label('rl_step')
    blkB.emit(0xd242)                               # add.w d2, d1
    blkB.emit(0x6b00, 0x0000)                       # bmi.w rl_stay
    blkB.fixups.append((len(blkB.buf) - 2, 'rl_stay', 'w16'))
    blkB.emit(0xb251)                               # cmp.w (a1), d1
    blkB.bcc_w('rl_stay')
    blkB.emit(0x7000)                               # moveq #0, d0
    blkB.emit(0x3001)                               # move.w d1, d0
    blkB.emit(0xe588)                               # lsl.l #2, d0
    blkB.emit(0x41f1, 0x0800)                       # lea.l (a1, d0.l), a0
    blkB.emit(0x2068, 0x3016)                       # movea.l $3016(a0), a0
    blkB.emit(0x4a68, 0x000a)                       # tst.w $a(a0) (folder?)
    blkB.bne_w('rl_step')
    blkB.emit(0x33c1, 0x00ff, 0xc5a2)               # move.w d1, $ffc5a2.l
    blkB.emit(0x13fc, 0x0001, 0x00ff, 0xc5a1)       # move.b #1, $ffc5a1.l (moved)
    blkB.emit(0x2f0c)                               # move.l a4, -(a7)
    blkB.emit(0x2f08)                               # move.l a0, -(a7)
    blkB.emit(0x4eb9, 0x00ff, 0x2872)               # jsr $ff2872.l (fatGetRec -> a4)
    blkB.emit(0x508f)                               # addq.l #8, a7
    blkB.emit(0x4878, 0x0001)                       # pea.l $1.w (full redraw)
    blkB.emit(0x42a7)                               # clr.l -(a7)
    blkB.emit(0x3f79, 0x00ff, 0xc5a2, 0x0002)       # move.w $ffc5a2.l, $2(a7) (cursor)
    blkB.emit(0x4eb9, 0x00ff, 0x08e8)               # jsr $ff08e8.l (draw page)
    blkB.emit(0x508f)                               # addq.l #8, a7
    blkB.bra_w('rfm_restart')
    blkB.label('rl_stay')
    blkB.bra_w('rfm_draw_menu')

    # rfmFixCursor (bsr from rfm_exit): after L/R, hand the new cursor back to the browser
    # through the d4 that romFileMenu_v2 restores, and ask for a full page redraw.
    blkB.label('rfmFixCursor')
    blkB.emit(0x4a39, 0x00ff, 0xc5a1)               # tst.b $ffc5a1.l
    blkB.beq_w('rf_r')
    blkB.emit(0x4239, 0x00ff, 0xc5a1)               # clr.b $ffc5a1.l
    blkB.emit(0x3f79, 0x00ff, 0xc5a2, 0x000e)       # move.w $ffc5a2.l, $e(a7) (saved d4)
    blkB.emit(0x33fc, 0x0001, 0x00ff, 0x8008)       # move.w #1, $ff8008.l
    blkB.label('rf_r')
    blkB.emit(0x4e75)                               # rts

    # Combine all labels across all blocks and resolve fixups
    all_labels = {}
    for b in (blk1, blk2, blk3, ext, opt_asm, blkA, blkB):
        all_labels.update(b.labels)
    for b in (blk1, blk2, blk3, ext, opt_asm, blkA, blkB):
        b.resolve(all_labels)

    # Check bounds and write blocks into ROM
    assert len(blk1.buf) <= (0x0BFA - 0x0B92), f"blk1 too large: {len(blk1.buf)}"
    rom[0x0B92:0x0B92 + len(blk1.buf)] = blk1.buf
    for p in range(0x0B92 + len(blk1.buf), 0x0BFA, 2):
        struct.pack_into('>H', rom, p, 0x4E71)

    assert len(blk2.buf) <= (0x5034 - 0x4F74), f"blk2 too large: {len(blk2.buf)}"
    rom[0x4F74:0x4F74 + len(blk2.buf)] = blk2.buf
    for p in range(0x4F74 + len(blk2.buf), 0x5034, 2):
        struct.pack_into('>H', rom, p, 0x4E71)

    assert len(blk3.buf) <= (0x5194 - 0x50BC), f"blk3 too large: {len(blk3.buf)}"
    rom[0x50BC:0x50BC + len(blk3.buf)] = blk3.buf
    for p in range(0x50BC + len(blk3.buf), 0x5194, 2):
        struct.pack_into('>H', rom, p, 0x4E71)

    assert len(opt_asm.buf) <= (0x4B54 - 0x49B6), f"opt_asm too large: {len(opt_asm.buf)}"
    rom[0x49B6:0x49B6 + len(opt_asm.buf)] = opt_asm.buf
    for p in range(0x49B6 + len(opt_asm.buf), 0x4B54, 2):
        struct.pack_into('>H', rom, p, 0x4E71)

    assert rom[0x6854:0x685D] == b'File Menu' and len(blkA.buf) <= 0x68D0 - 0x6854, len(blkA.buf)
    rom[0x6854:0x6854 + len(blkA.buf)] = blkA.buf
    assert rom[0x6B07:0x6B15] == b'Assembly Date:' and len(blkB.buf) <= 0x6BE6 - 0x6B08, len(blkB.buf)
    rom[0x6B08:0x6B08 + len(blkB.buf)] = blkB.buf

    assert 0x6E48 + len(ext.buf) <= 0x8000, f"Extension exceeds 32KB limit: 0x{0x6E48 + len(ext.buf):04X}"
    rom[0x6E48:0x6E48 + len(ext.buf)] = ext.buf

    # =========================================================================
    # Patch Hooks and String Pointers in MDOS.patched.BIN
    # =========================================================================
    def patch_long(file_off, old_val, new_val):
        cur = struct.unpack_from('>I', rom, file_off)[0]
        assert cur == old_val, f"At 0x{file_off:04x}: expected 0x{old_val:08x}, got 0x{cur:08x}"
        struct.pack_into('>I', rom, file_off, new_val)

    # 0. Update OS Version byte at 0x0011 to 0x02 & show the mod version in deviceInfo (0x4C5C)
    assert rom[0x0010:0x0014] == bytes.fromhex('00010300')
    rom[0x0011] = 0x02
    # deviceInfo: the OS version number (move.w $ffc47e,d0; push; jsr (a4)) becomes the mod version
    # string at the same column: pea str_mod_version.l; jsr gPrintAt (x and y are already pushed)
    assert rom[0x4C5C:0x4C68] == bytes.fromhex('7000303900ffc47e2f004e94')
    struct.pack_into('>HIHI', rom, 0x4C5C, 0x4879, all_labels['str_mod_version'], 0x4EB9, 0xFF3556)

    # A. Hook printFolder top bar (0x0A50: movea.l $ffc46c.l, a0 -> jsr draw_top_banner.l)
    assert rom[0x0A50:0x0A56] == bytes.fromhex('207900ffc46c')
    struct.pack_into('>HI', rom, 0x0A50, 0x4EB9, all_labels['draw_top_banner'])

    # B. Hook romFileMenu (0x0B8C -> jmp romFileMenu_v2.l)
    struct.pack_into('>HI', rom, 0x0B8C, 0x4EF9, all_labels['romFileMenu_v2'])

    # B2. Hook the browser's wait-for-button loop (0x0E0C: jsr (a2); tst.w d0; beq.s 0e0a) -> browseIdle
    assert rom[0x0E0A:0x0E12] == bytes.fromhex('42474e924a4067f8')
    struct.pack_into('>HI', rom, 0x0E0C, 0x4EB9, all_labels['browseIdle'])

    # B3. menuDraw key check (0x499E: move.w $ffc4a4,d0; btst #6,d0; beq.w $ff48f2) -> menuLR
    assert rom[0x499E:0x49AC] == bytes.fromhex('303900ffc4a4080000066700ff48')
    struct.pack_into('>HIHhHH', rom, 0x499E, 0x4EB9, all_labels['menuLR'], 0x6700,
                     0xFF48F2 - (0xFF49A4 + 2), 0x4E71, 0x4E71)

    # B4. Browser page counter ("Pág. x de y") moves from the top bar to row 24, just above the
    #     file name bar (like the v1); the top bar keeps only the centred banner.
    assert rom[0x09E2:0x09E6] == bytes.fromhex('48780001')
    rom[0x09E5] = 24

    # C. Hook browser C-button Main Menu call (0x0FF0) -> call_mainMenu_from_browser
    patch_long(0x0FF2, 0x00FF50BC, all_labels['call_mainMenu_from_browser'])

    # D. Expand settings SRAM allocation from 12 ($c) to 14 ($e) bytes at 0x6252
    assert rom[0x6252:0x6256] == bytes.fromhex('4878000c')
    rom[0x6255] = 0x0E

    # E. Hook edInit SRAM allocation (0x6268: move.l d0, $ffc49e.l -> jsr init_recent_sram.l)
    assert rom[0x6268:0x626E] == bytes.fromhex('23c000ffc49e')
    struct.pack_into('>HI', rom, 0x6268, 0x4EB9, all_labels['init_recent_sram'])

    # F. Update SRAM init magic byte to 0xA2 & hook 0x63A0 -> clear_recent_sram
    assert rom[0x635E:0x6364] == bytes.fromhex('0c28ffaa0009')
    rom[0x6361] = 0xA2
    assert rom[0x636E:0x6374] == bytes.fromhex('317c00aa0008')
    rom[0x6371] = 0xA2
    patch_long(0x63A2, 0x00FF37E6, all_labels['clear_recent_sram'])

    # G. Hook end of edInit (0x63E2: jsr $ff662a.l -> jsr boot_init_vram_and_theme.l)
    patch_long(0x63E4, 0x00FF662A, all_labels['boot_init_vram_and_theme'])

    # H. Update menu pointer tables at 0xFF6DCC..0xFF6E3F
    menu_ptr_patches = [
        (0x6DCC, 0x00FF6854, 'str_file_menu'),
        (0x6DD0, 0x00FF685E, 'str_load_cheats'),
        (0x6DD4, 0x00FF686A, 'str_hex_view'),
        (0x6DD8, 0x00FF6854, 'str_file_menu'),
        (0x6DDC, 0x00FF6873, 'str_cancel'),
        (0x6DE0, 0x00FF687A, 'str_file_to_sram'),
        (0x6DE4, 0x00FF688C, 'str_sram_to_file'),
        (0x6DE8, 0x00FF686A, 'str_hex_view'),
        (0x6DEC, 0x00FF6854, 'str_file_menu'),
        (0x6DF0, 0x00FF689E, 'str_load_start'),
        (0x6DF4, 0x00FF68AD, 'str_load_only'),
        (0x6DF8, 0x00FF686A, 'str_hex_view'),
        (0x6DFC, 0x00FF6854, 'str_file_menu'),
        (0x6E00, 0x00FF68B7, 'str_unzip_rom'),
        (0x6E04, 0x00FF6913, 'str_apply_codes_q'),
        (0x6E08, 0x00FF6920, 'str_apply'),
        (0x6E0C, 0x00FF6873, 'str_cancel'),
        (0x6E10, 0x00FF6926, 'str_modify'),
        (0x6E18, 0x00FF69D2, 'str_opt_title'),
        (0x6E1C, 0x00FF69DA, 'str_opt_region'),
        (0x6E20, 0x00FF69F1, 'str_opt_megakey'),
        (0x6E24, 0x00FF6A08, 'str_opt_sram'),
        (0x6E28, 0x00FF6A1F, 'str_opt_rst'),
        (0x6E2C, 0x00FF6A36, 'str_mm_title'),
        (0x6E30, 0x00FF69D2, 'str_opt_title'),
        (0x6E34, 0x00FF6863, 'str_mm_cheats'),
        (0x6E38, 0x00FF6A40, 'str_mm_devinfo'),
        (0x6E3C, 0x00FF6A4C, 'str_mm_about'),
    ]
    for off, old_ptr, lbl in menu_ptr_patches:
        patch_long(off, old_ptr, all_labels[lbl])

    # I. Update inline code string pointers
    code_ptr_patches = [
        (0x09EC, 0x00FF68D6, 'str_page'),
        (0x0A10, 0x00FF68DC, 'str_of'),
        (0x0A66, 0x00FF68E1, 'str_no_files'),
        (0x3864, 0x00FF692D, 'str_flash_patch'),
        (0x3C5E, 0x00FF6955, 'str_raw_code'),
        (0x40DC, 0x00FF695E, 'str_gg_code'),
        (0x4402, 0x00FF6966, 'str_cheats_menu'),
        (0x4B98, 0x00FF6A82, 'str_sys_info'),
        (0x4BBA, 0x00FF6A95, 'str_cpld_ver'),
        (0x4BF4, 0x00FF6AA3, 'str_bios_ver'),
        (0x4C46, 0x00FF6AB1, 'str_os_ver'),
        (0x4C78, 0x00FF6AC0, 'str_mk_mode'),
        (0x4CC6, 0x00FF6AE0, 'str_sys_type'),
        (0x4E12, 0x00FF6B07, 'str_asm_date'),
        (0x4E7A, 0x00FF6B16, 'str_asm_time'),
        (0x53C2, 0x00FF6C16, 'str_fat_init'),
        (0x549E, 0x00FF6C2D, 'str_err_hdr'),
        (0x54C2, 0x00FF6C34, 'str_err_rom_large'),
        (0x54DA, 0x00FF6C4A, 'str_err_sd_io'),
        (0x54EC, 0x00FF6C56, 'str_err_no_fat'),
        (0x5504, 0x00FF6C6B, 'str_err_fat'),
        (0x551A, 0x00FF6C75, 'str_err_not_loaded'),
        (0x59EA, 0x00FF6C94, 'str_sram_save'),
        (0x5ABE, 0x00FF6CA7, 'str_sram_load'),
        (0x5C0A, 0x00FF6CB8, 'str_reg_patch'),
        (0x5CCC, 0x00FF6CCB, 'str_rom_type'),
        (0x5D40, 0x00FF6CF4, 'str_unknown_cap'),
        (0x5D5A, 0x00FF6CFC, 'str_rom_reg'),
        (0x5DA8, 0x00FF6D09, 'str_world_5'),
        (0x5DB0, 0x00FF6D0F, 'str_unknown_up'),
        (0x5DC8, 0x00FF6D17, 'str_erase'),
        (0x5E0E, 0x00FF6D23, 'str_read_file'),
        (0x5F58, 0x00FF6D30, 'str_dont_turn_off'),
        (0x6174, 0x00FF6D89, 'str_done'),
        (0x61E2, 0x00FF6D8F, 'str_usb_mode'),
        (0x63B6, 0x00FF6D9D, 'str_cfg_reset'),
        (0x63C8, 0x00FF6DB7, 'str_press_key'),
    ]
    for off, old_ptr, lbl in code_ptr_patches:
        patch_long(off, old_ptr, all_labels[lbl])

    # Verify disassembly of all assembled code blocks
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    for name, buf, base in [
        ('blk1_helpers', bytes(blk1.buf), 0xFF0B92),
        ('blk2_about', bytes(blk2.buf[:blk2_code_end]), 0xFF4F74),
        ('blk3_random', bytes(blk3.buf), 0xFF50BC),
        ('optionsMenu_v2', bytes(opt_asm.buf), 0xFF49B6),
        ('ext_code', bytes(ext.buf[:code_end_off]), 0xFF6E48),
        ('blkA', bytes(blkA.buf), 0xFF6854),
        ('blkB', bytes(blkB.buf), 0xFF6B08),
    ]:
        insns = list(md.disasm(buf, base))
        last_end = base
        for i in insns:
            last_end = i.address + i.size
        assert last_end == base + len(buf), (
            f"Disassembly stopped early in {name} at 0x{last_end:06X} != 0x{base + len(buf):06X}"
        )

    assert b'\x00\xa1\x30\x50' not in rom[:0x8000], "Unexpected hardware register access!"

    out_path = 'mega-genesis/MDOS.ptbr.BIN'
    with open(out_path, 'wb') as f:
        f.write(rom)

    sha = hashlib.sha256(rom).hexdigest()
    used = len(ext.buf)
    free = (0x8000 - 0x6E48) - used
    print(f"Built {out_path} ({len(rom)} bytes)")
    print(f"  blk1 (0xFF0B92):  {len(blk1.buf)} / 104 bytes")
    print(f"  blk2 (0xFF4F74):  {len(blk2.buf)} / 192 bytes")
    print(f"  blk3 (0xFF50BC):  {len(blk3.buf)} / 216 bytes")
    print(f"  opt  (0xFF49B6):  {len(opt_asm.buf)} / 414 bytes")
    print(f"  blkA (0xFF6854):  {len(blkA.buf)} / 124 bytes   blkB (0xFF6B08):  {len(blkB.buf)} / 222 bytes")
    print(f"  ext  (0xFF6E48):  0xFF6E48..0xFF{0x6E48 + used - 1:04X} ({used} bytes used, {free} bytes free)")
    print(f"  SHA-256: {sha}")
    print("  100% verified: 0 clone-check instructions, all m68k code blocks disassembled cleanly!")

if __name__ == '__main__':
    build_custom_mdos()
