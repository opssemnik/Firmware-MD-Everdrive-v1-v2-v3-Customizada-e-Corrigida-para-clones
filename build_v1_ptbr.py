"""
Builds OS-V38-PTBR.BIN for the EverDrive-MD v1: stock OS v38 + RetroGamer POA distributor logo
+ the PT-BR mod features of MDOS.ptbr.BIN (translation, accents, banner, recent games, favourites,
random game, file menu with box art, ROM info, themes, credits).

New code lives in v1mod/ (C + asm) and is compiled inside WSL Debian with the rootless m68k
toolchain in ~/m68k/root. The OS file is mapped at cart 0x10000 and copied to RAM 0xFF0000;
the new code runs straight from flash, the stock OS keeps running from RAM.
"""
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from capstone import CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000, Cs

HERE = Path(__file__).resolve().parent
MOD = HERE / 'v1mod'
BUILD = MOD / 'build'
OS_IN = HERE / 'OS-V38.BIN'
POA_IN = HERE / 'os-v36-retrogamer-poa.bin'
MOD_VERSION = '1.19'     # same number for v1 and v3 (main menu footer, Ferramentas -> dispositivo)
DIAG = '--diag' in sys.argv     # diagnostics build: flash chip info + load timings
OUT = HERE / ('OS-V38-PTBR-DIAG.BIN' if DIAG else 'OS-V38-PTBR.BIN')

RAM = 0xFF0000          # RAM address of file offset 0
CART = 0x10000          # cart address of file offset 0
CODE_START, CODE_END = 0x10DC, 0x93DC   # RAM-resident code (font data precedes it)
SIG_OFF = 0xFFF8

GLYPHS = 'áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ'
GLYPH_BASE = 0xA0       # font tile = char + 0x4E0 -> VRAM 0xB000 (unused window table)
BANNER_BASE = 0xC0

# ---------------------------------------------------------------- strings used by the new code
C_STRINGS = {
    'S_version': f'PT-BR {MOD_VERSION}',
    'S_mm_play': 'Jogar último jogo',
    'S_mm_select': 'Selecionar jogo',
    'S_mm_recent': 'Jogos recentes',
    'S_mm_fav': 'Favoritos',
    'S_mm_random': 'Jogo aleatório',
    'S_mm_options': 'Opções',
    'S_mm_cheats': 'Cheats',
    'S_mm_tools': 'Ferramentas',
    'S_mm_theme': 'Tema: ',
    'S_thm0': 'PADRÃO',
    'S_thm1': 'RG POA',
    'S_thm2': 'SEGA 16',
    'S_thm3': 'OUTRUN',
    'S_fm_load_start': 'Carregar e jogar',
    'S_fm_load_only': 'Só carregar',
    'S_fm_cheats': 'Jogar com cheats',
    'S_flt_title': 'Filtrar por letra',
    'S_flt_af': 'A - F',
    'S_flt_gl': 'G - L',
    'S_flt_mr': 'M - R',
    'S_flt_sz': 'S - Z',
    'S_flt_num': '0 - 9 e outros',
    'S_flt_all': 'Todos (sem filtro)',
    'S_flt_none': 'Nenhum jogo com essa letra',
    'S_fm_add_fav': 'Adicionar aos favoritos',
    'S_fm_rom_info': 'Info da ROM',
    'S_back': 'Voltar',
    'S_fv_play': 'Jogar',
    'S_fv_remove': 'Remover dos favoritos',
    'S_recent_title': 'Jogos recentes',
    'S_fav_title': 'Favoritos',
    'S_no_recent': 'Nenhum jogo recente',
    'S_clear_recent': '[ LIMPAR RECENTES ]',
    'S_no_fav': 'Nenhum favorito salvo',
    'S_fav_saved': 'Salvo nos favoritos!',
    'S_fav_removed': 'Removido dos favoritos',
    'S_loaded_ok': 'Jogo carregado na memória',
    'S_not_found': 'Arquivo não encontrado no SD',
    'S_too_small': 'Arquivo pequeno demais',
    'S_no_games': 'Nenhum jogo encontrado',
    'S_rand_search': 'Sorteando um jogo...',
    'S_saving': 'Salvando...',
    'S_sel_error': 'erro na seleção: ',
    'S_prog_error': 'erro na gravação: ',
    'S_fat_error': 'erro FAT: ',
    'S_no_art': 'sem capa',
    'S_art_prefix': '/EDMD/ART/',
    'S_banner_path': '/EDMD/BANNER.ART',
    'S_wall_path': '/EDMD/WALL.ART',
    'S_ri_title': 'Info da ROM (cabeçalho SEGA)',
    'S_ri_us': 'Nome US/EU:',
    'S_ri_jp': 'Nome JP:',
    'S_ri_sys': 'Console:',
    'S_ri_cop': 'Copyright:',
    'S_ri_ser': 'Serial:',
    'S_ri_reg': 'Região:',
    'S_ri_chk': 'Checksum:',
    'S_ri_size': 'Tamanho (KB): ',
    'S_ri_art': 'Capa:',
    'S_ri_kanji': '(em japonês)',
    'S_ri_nohdr': 'Cabeçalho SEGA não encontrado',
    'S_press_key': 'Pressione um botão',
    'S_ab_title': 'EverDrive-MD flashcart',
    'S_ab_dev': 'desenvolvido por Igor Golubovskiy',
    'S_ab_mod1': 'Mod PT-BR, capas, recentes e favoritos:',
    'S_ab_mod2': 'por Antonio e the Nobre',
    'S_ab_sup': 'suporte:',
    'S_ab_url': 'http://krikzz.com',
    'S_ab_mail': 'biokrik@gmail.com',
    'S_ab_date': 'data de montagem:',
    'S_ab_dist': 'distribuído por:',
}

# ---------------------------------------------------------------- stock strings moved to flash
OS_REPOINT = {
    0xFF941C: 'Erro do OS',
    0xFF9425: 'requer firmware v3 ou mais novo',
    0xFF9446: 'pressione um botão para continuar',
    0xFF948B: 'digite o nome',
    0xFF9496: '(B)apagar, (A)escrever, (START)ok',
    0xFF950A: 'aplicando cheats...      ',
    0xFF9520: 'aplicando cheats... ',
    0xFF9531: 'pronto ',
    0xFF9537: 'Lista de códigos GG',
    0xFF9545: '(A)editar, (B)voltar, (START)aplicar',
    0xFF956F: 'Digitar códigos GG',
    0xFF957E: 'Carregar códigos GG',
    0xFF958C: 'erro ao carregar: ',
    0xFF962A: '!!! NÃO DESLIGUE O VIDEOGAME !!!',
    0xFF964B: 'copiando SRAM p/ SD...',
    0xFF965E: 'Tipo de ROM: SMS',
    0xFF966C: 'Tipo de ROM: MD',
    0xFF9679: 'apagando...',
    0xFF9682: 'copiando...',
    0xFF968A: 'copiando SRAM do SD...',
    0xFF969F: 'copiando SRAM p/ flash...',
    0xFF96B5: 'pronto!',
    0xFF96BB: 'MegaKey software...',
    0xFF96F5: 'erro na seleção: ',
    0xFF9701: 'erro na gravação: ',
    0xFF973A: 'Reset total:',
    0xFF9746: 'Modo Genny3:',
    0xFF9753: 'Backup auto SRAM:',
    0xFF9765: 'Região livre:',
    0xFF9772: '(A)alterar, (B)voltar',
    0xFF9785: 'DESL',
    0xFF9789: 'LIG',
    0xFF9791: 'salvando...',
    0xFF979D: 'iniciando FAT...',
    0xFF97AF: 'abrindo raiz...',
    0xFF97BC: 'pág: ',
    0xFF97C5: 'ERRO ao listar: ',
    0xFF97DA: 'ERRO ao abrir pasta: ',
    0xFF97F4: 'o arquivo já existe ',
    0xFF9808: 'pressione um botão',
    0xFF9816: 'Salvar no arquivo',
    0xFF9823: 'Salvar em novo arquivo',
    0xFF9834: 'Carregar do SD',
    0xFF9841: 'erro ao salvar: ',
    0xFF984E: 'Versão do OS: ',
    0xFF985B: 'Versão firmware: ',
    0xFF986E: 'MegaKey: ',
    0xFF988A: 'Sistema arq.: ',
    0xFF98A4: 'Região console: ',
    0xFF98DF: 'NÃO',
    0xFF9905: 'DESCONHECIDO',
    0xFF990D: 'Itens na pasta: ',
    0xFF9918: 'Tecla SMS: ',
    0xFF9922: 'pressionada',
    0xFF992E: 'solta      ',
    0xFF99D0: 'calibrando timer...',
    0xFF99EF: 'iniciando SD...',
    0xFF99FB: 'ERRO: ',
    0xFF9A03: 'testando...',
    0xFF9A0E: 'tempo 1/10 s: ',
    0xFF9A1E: 'veloc. kb/s: ',
}

# Instructions that use a string address as data, not as text: they keep the stock pointer.
# 0xFF40F8: lea $ff950a,a1 starts a stock checksum over the string table 0xFF950A..0xFF9609.
NOT_STRING_REFS = {0xFF40F8}
CHECKSUMMED = (0x950A, 0x960A)

# ---------------------------------------------------------------- translated in place (RAM copy)
# Shown by the toolbox / OS update tool, which must stay readable while the OS flash is rewritten.
OS_INPLACE = {
    0xFF970E: '(A/START)ok, (B)voltar',
    0xFF9A98: 'dispositivo',
    0xFF9AA4: 'backup da SRAM',
    0xFF9AB3: 'gravar OS',
    0xFF9ABD: 'sobre',
    0xFF9AC3: 'teste veloc.SD',
    0xFF9A2B: 'Atualizar o OS',
    0xFF9A3A: 'tem certeza?',
    0xFF9A48: 'A(sim) B(não)',
    0xFF9A56: 'gravando...',
    0xFF9A62: 'lendo OS...',
    0xFF9A70: 'verif. buff...',
    0xFF9A7F: 'verif. flash...',
    0xFF9A8F: 'sucesso!',
    0xFF9AD2: 'falha no OS: ',
    0xFF9AE1: '(cima/baixo)página, (B)voltar',
}

ACUTE, GRAVE, CIRC, TILDE = (0x0C, 0x18), (0x30, 0x18), (0x18, 0x24), (0x34, 0x4C)
CEDILLA = (0x18, 0x30)


def enc(s):
    out = bytearray()
    for ch in s:
        if ch in GLYPHS:
            out.append(GLYPH_BASE + GLYPHS.index(ch))
        else:
            assert 0x20 <= ord(ch) < 0x7F, f'unsupported char {ch!r} in {s!r}'
            out.append(ord(ch))
    return bytes(out)


def font_rows(img, ch):
    off = 0x17C + (ord(ch) - 0x20) * 32
    rows = []
    for r in range(8):
        v = 0
        for b in img[off + r * 4: off + r * 4 + 4]:
            v = (v << 2) | ((b >> 4) != 0) << 1 | ((b & 15) != 0)
        rows.append(v)
    return rows


def build_glyphs(img):
    accent = {'á': ACUTE, 'à': GRAVE, 'â': CIRC, 'ã': TILDE, 'é': ACUTE, 'ê': CIRC, 'í': ACUTE,
              'ó': ACUTE, 'ô': CIRC, 'õ': TILDE, 'ú': ACUTE}
    out = []
    for g in GLYPHS:
        base = 'aaaaeeiooouc'['áàâãéêíóôõúç'.index(g.lower())]
        if g == 'ç':
            r = font_rows(img, 'c')
            rows = [0] + r[2:7] + list(CEDILLA)
        elif g == 'Ç':
            r = font_rows(img, 'C')
            rows = r[1:7] + list(CEDILLA)
        elif g.islower():
            r = font_rows(img, base)
            rows = list(accent[g]) + r[2:8]
        else:
            r = font_rows(img, base.upper())[1:7]
            drop = next((i for i in range(1, 5) if r[i] == r[i + 1]), 1)
            body = r[:drop] + r[drop + 1:]
            rows = list(accent[g.lower()]) + body + [0]
        assert len(rows) == 8
        out.append(rows)
    return out


def build_banner(img, text=' RETROGAMER POA '):
    """Banner bar in the OS 8x8 font: 1 = crimson bar, 2 = gold letters, 3 = shadow (2bpp tiles)."""
    w = len(text) * 8
    px = [[1] * w for _ in range(8)]
    for y in (0, 7):
        px[y][0] = px[y][w - 1] = 0                     # rounded ends
    for i, ch in enumerate(text):
        rows = font_rows(img, ch)
        for y in range(8):
            for x in range(8):
                if rows[y] >> (7 - x) & 1:
                    px[y][i * 8 + x] = 2
                    if y < 7 and x < 7 and not rows[y + 1] >> (6 - x) & 1:
                        px[y + 1][i * 8 + x + 1] = 3
    out = bytearray()
    for t in range(len(text)):
        for y in range(8):
            row = px[y][t * 8:t * 8 + 8]
            out.append(row[0] << 6 | row[1] << 4 | row[2] << 2 | row[3])
            out.append(row[4] << 6 | row[5] << 4 | row[6] << 2 | row[7])
    return bytes(out)


def preview(glyphs):
    for i in range(0, len(glyphs), 12):
        grp = glyphs[i:i + 12]
        print('    ' + '  '.join(f'{GLYPHS[i + j]:<8}' for j in range(len(grp))))
        for r in range(8):
            print('    ' + '  '.join(''.join('#' if g[r] >> (7 - b) & 1 else '.' for b in range(8)) for g in grp))


def c_bytes(b):
    return ', '.join(f'0x{x:02x}' for x in b)


def gen_sources(glyphs, banner):
    """gen.h / gen.c: glyph + banner data and all strings, spread over the free flash regions."""
    strings = {name: enc(t) + b'\0' for name, t in C_STRINGS.items()}
    strings['S_banner'] = bytes(range(BANNER_BASE, BANNER_BASE + len(banner) // 16)) + b'\0'
    for addr, t in OS_REPOINT.items():
        strings[f'O_{addr:06X}'] = enc(t) + b'\0'
    room = {'.strc': 0xA00, '.strb': 0x7A0 - 8 * len(glyphs) - len(banner) - 4}
    h = ['#ifndef GEN_H', '#define GEN_H', f'#define NGLYPH {len(glyphs)}',
         f'#define GLYPH_TILE 0x{GLYPH_BASE + 0x4E0:x}', f'#define BANNER_TILE 0x{BANNER_BASE + 0x4E0:x}',
         f'#define NBANNER {len(banner) // 16}',
         'extern const unsigned char glyph1bpp[];', 'extern const unsigned char banner2bpp[];']
    c = ['#include "gen.h"',
         f'const unsigned char glyph1bpp[] __attribute__((section(".strb"))) = {{{c_bytes(sum(glyphs, []))}}};',
         f'const unsigned char banner2bpp[] __attribute__((section(".strb"))) = {{{c_bytes(banner)}}};']
    for name, data in sorted(strings.items(), key=lambda kv: -len(kv[1])):
        sec = next((s for s, left in room.items() if left >= len(data) + 1), '.rodata.gen')
        if sec in room:
            room[sec] -= len(data) + 1
        h.append(f'extern const char {name}[];')
        c.append(f'const char {name}[] __attribute__((section("{sec}"))) = {{{c_bytes(data)}}};')
    h.append('#endif')
    BUILD.mkdir(exist_ok=True)
    (BUILD / 'gen.h').write_text('\n'.join(h) + '\n')
    (BUILD / 'gen.c').write_text('\n'.join(c) + '\n')


def wsl_path(p):
    p = str(p).replace('\\', '/')
    return f'/mnt/{p[0].lower()}{p[2:]}'


def compile_mod(build_id):
    r = subprocess.run(['wsl', '-d', 'Debian', '--', 'bash', wsl_path(MOD / 'build.sh'), str(build_id),
                        '-DDIAG' if DIAG else ''],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        sys.exit('compile failed')
    syms = {}
    for ln in (BUILD / 'mod.sym').read_text().splitlines():
        parts = ln.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    secs = {}
    for ln in (BUILD / 'mod.sections').read_text().splitlines():
        m = re.match(r'\s*\d+\s+(\.\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)', ln)
        if m:   # Size VMA LMA -> (lma, size, vma)
            secs[m.group(1)] = (int(m.group(4), 16), int(m.group(2), 16), int(m.group(3), 16))
    return syms, secs


def main():
    rom = bytearray(OS_IN.read_bytes())
    poa = POA_IN.read_bytes()
    assert len(rom) == len(poa) == 0x10000
    stock = bytes(rom)

    # 1. RetroGamer POA distributor block (header, strings, palette, logo) replaces PiKaTu's
    assert rom[0xC000:0xC004] == poa[0xC000:0xC004] == b'EDHD'
    rom[0xC000:0x10000] = poa[0xC000:0x10000]
    for lo, hi in ((0xC220, 0xCC20), (0xDB20, 0xE400), (0xE400, 0x10000)):
        assert not any(rom[lo:hi]), f'region {lo:04X}-{hi:04X} is not blank'

    # 2. glyphs + banner + generated sources
    glyphs = build_glyphs(stock)
    print('Accented glyphs (from the v1 font):')
    preview(glyphs)
    banner = build_banner(stock)
    gen_sources(glyphs, banner)

    src = b''.join((MOD / f).read_bytes() for f in ('os.h', 'mod.c', 'hooks.S', 'link.ld'))
    src += (BUILD / 'gen.c').read_bytes()
    src += Path(__file__).read_bytes() + (b'DIAG' if DIAG else b'')
    build_id = zlib.crc32(src) & 0x7FFFFFFF | 1

    # 3. compile + place
    syms, secs = compile_mod(build_id)
    assert secs.get('.data', (0, 0, 0))[1] == 0, '.data must be empty (nothing copies it)'
    placed = []
    for name in ('.text', '.ramstub', '.strb', '.strc', '.diag'):
        if name not in secs or not secs[name][1]:
            assert name == '.diag' and not DIAG, f'missing section {name}'
            continue
        lma, size, vma = secs[name]
        data = (BUILD / f'{name[1:]}.bin').read_bytes()
        assert len(data) == size
        off = lma - CART
        assert 0 <= off and off + size <= SIG_OFF
        rom[off:off + size] = data
        placed.append((name, lma, size))
    rom[SIG_OFF:SIG_OFF + 8] = b'PTBR' + struct.pack('>I', build_id)
    lst = (BUILD / 'mod.lst').read_text()
    bad = re.findall(r'\b(extbl|mulsl|mulul|divsl|divul|divsll|divull|bf[a-z]+|cas2?|chk2|cmp2|rtd|pack|unpk)\b', lst)
    assert not bad, f'non-68000 instructions emitted: {set(bad)}'
    # read-modify-write instructions on the VDP ports read them first: a data port read while the
    # VDP is set up for writing hangs the real console (the v3 1.14/1.15 black screen)
    rmw = re.findall(r'\b(?:clr|tst|not|negx?|bset|bclr|bchg|tas|addq|subq|or|and|eor)[bwl]?\b[^\n]*\bc0000[0-7]\b', lst)
    assert not rmw, f'read-modify-write on a VDP port: {rmw}'

    # 4. hooks into the RAM-resident OS
    def patch(ram, old, new):
        off = ram - RAM
        assert rom[off:off + len(old)] == old, f'{ram:06X}: expected {old.hex()} got {rom[off:off + len(old)].hex()}'
        rom[off:off + len(new)] = new

    jsr = lambda t: struct.pack('>HI', 0x4EB9, t)
    patch(0xFF1220, jsr(0xFF1C58), jsr(syms['myInit']))                 # boot init
    patch(0xFF1350, jsr(0xFF528E), jsr(syms['ramMain']))                # main menu
    patch(0xFF594A, jsr(0xFF7FB2), jsr(syms['ramMenuClear']))           # menu clear -> banner/overlay
    patch(0xFF5C7E, bytes.fromhex('4feffe002f02'), struct.pack('>HI', 0x4EF9, syms['ramSave']))
    patch(0xFF6640, bytes.fromhex('4a68000a670000d0'), jsr(syms['ramAHook']) + b'\x4e\x71')
    patch(0xFF5AF4, bytes.fromhex('303900ffe30c0200ffd0'), jsr(syms['ramMenuLR']) + b'\x4e\x71' * 2)  # menu L/R
    # Mod version instead of "OS v38": a plain string print (ff90a4) where the OS printed str + number
    pea_l = lambda a: struct.pack('>HI', 0x4879, a)
    patch(0xFF59A4, bytes.fromhex('48780026487900ff97254eb900ff7ca4'),                  # main menu footer
          pea_l(syms['S_version']) + bytes.fromhex('4878c000') + jsr(0xFF90A4))
    patch(0xFF6FC2, bytes.fromhex('70264e714e714e712f00487900ff951f47f900ff7ca44e93'),  # dispositivo
          pea_l(syms['S_version']) + pea_l(0xC000) + bytes.fromhex('47f900ff7ca4') + jsr(0xFF90A4))
    patch(0xFF660E, bytes.fromhex('303900ffe30c6604424560f4'), jsr(syms['ramIdle']) + b'\x4e\x71' * 3)  # input wait
    # Browser layout: banner rows 0-2, a blank row, list rows 4-24 (stock 2-22), a blank row, page
    # counter on row 26 (stock 23), file name bar on row 27 only (stock 24-25, two lines): the name is
    # one line of up to 38 characters (stock 36 + a second line for long names)
    for ram, old, new in ((0xFF657E, '48780002', '48780004'),                    # first list row
                          (0xFF6258, '48780002', '48780001'), (0xFF625C, '48780024', '48780026'),
                          (0xFF6260, '48780018', '4878001b'),                    # name clear: row 27, 38 wide
                          (0xFF6276, '48780024', '48780026'), (0xFF627A, '48780018', '4878001b'),  # name
                          (0xFF62DA, '6334', '6034'),                            # no second name line
                          (0xFF64DC, '48780002', '48780001'), (0xFF64E4, '48780018', '4878001b'),  # bar
                          (0xFF64FC, '48780017', '4878001a'), (0xFF653A, '2ebc00000017', '2ebc0000001a'),
                          (0xFF6554, '48780017', '4878001a')):                   # page counter row 26
        patch(ram, bytes.fromhex(old), bytes.fromhex(new))
    patch(0xFF64A8, bytes.fromhex('13fc000100ffe306'), jsr(syms['ramBrowserBanner']) + b'\x4e\x71')
    # footer: "pág: x / y" in gold (the three prints push d4 = palette 2, set by ramPagePal, instead
    # of 0) and the file name bar in the banner crimson (tile 1, palette 2) instead of grey
    for ram in (0xFF6504, 0xFF6544, 0xFF655C):
        patch(ram, bytes.fromhex('42a7'), bytes.fromhex('2f04'))       # clr.l -(sp) -> move.l d4,-(sp)
    patch(0xFF64EA, bytes.fromhex('48780002'), bytes.fromhex('48784001'))
    patch(0xFF64F4, bytes.fromhex('47f900ff8ed0'), jsr(syms['ramPagePal']))
    patch(0xFF693E, bytes.fromhex('303900ffe30c'), jsr(syms['ramBrowserC']))       # C: letter filter
    patch(0xFF3FEC, bytes.fromhex('6100fd2e588f'), jsr(syms['ramCheatApply']))       # GG codes: START
    patch(0xFF5642, bytes.fromhex('303900a13002080000016' '7f4'), jsr(syms['ramEraseWait']) + bytes.fromhex('4e71') * 3)  # erase wait
    disp = syms['ramAbout'] - (0xFF7C0A + 2)
    assert -0x8000 <= disp < 0x8000
    patch(0xFF7C0A, bytes.fromhex('6100f736'), struct.pack('>Hh', 0x6100, disp))
    for ram in (0xFF5A60, 0xFF5A80):                                    # menu centre operands used by mod.c
        patch(ram, bytes.fromhex('48780014'), bytes.fromhex('48780014'))
    if DIAG:    # timing probes at the entry of: status print, flash erase, flash write, checksum copy
        jmp = lambda t, pad: struct.pack('>HI', 0x4EF9, t) + b'Nq' * pad
        patch(0xFF7F7A, bytes.fromhex('103900ffe306'), jmp(syms['ramDStatus'], 0))
        patch(0xFF5592, bytes.fromhex('48e73020246f0010'), jmp(syms['ramDErase'], 1))
        patch(0xFF57D0, bytes.fromhex('48e73820242f0018'), jmp(syms['ramDWrite'], 1))
        patch(0xFF4094, bytes.fromhex('4fefffe448e73c30'), jmp(syms['ramDCheck'], 1))

    # 5. strings: repoint references in the code, translate the RAM-resident ones in place
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    md.skipdata = True
    insns = list(md.disasm(stock[CODE_START:CODE_END], RAM + CODE_START))
    nrefs = 0
    for addr, text in OS_REPOINT.items():
        new = syms[f'O_{addr:06X}']
        hits = 0
        for i in insns:
            if i.address in NOT_STRING_REFS:
                continue
            for k in range(2, i.size - 3, 2):
                if struct.unpack_from('>I', i.bytes, k)[0] == addr:
                    patch(i.address + k, struct.pack('>I', addr), struct.pack('>I', new))
                    hits += 1
        assert hits, f'no reference to {addr:06X}'
        nrefs += hits
    for addr, text in OS_INPLACE.items():
        off = addr - RAM
        old_len = stock.index(b'\0', off) - off
        b = enc(text)
        assert len(b) <= old_len, f'{text!r} longer than {old_len}'
        rom[off:off + old_len] = b + b'\0' * (old_len - len(b))

    # 6. sanity checks
    assert rom[0x9B16:0xC000] == stock[0x9B16:0xC000]       # OS bss image untouched (must stay zero)
    assert rom[slice(*CHECKSUMMED)] == stock[slice(*CHECKSUMMED)]   # stock checksum input unchanged
    assert rom[0x40F8:0x40FE] == stock[0x40F8:0x40FE]
    assert not any(rom[0xE2C0:0xE400])                      # OS variables at 0xFFE302.. start zeroed
    diff_code = sum(1 for i in range(CODE_END) if rom[i] != stock[i])
    OUT.write_bytes(rom)

    print(f'\nBuilt {OUT.name} ({len(rom)} bytes), build id {build_id:08X}')
    for name, lma, size in placed:
        print(f'  {name:9s} cart {lma:05X}..{lma + size - 1:05X}  {size:5d} bytes')
    print(f'  free: ROMA {0x1FFF8 - max(secs[s][0] + secs[s][1] for s in (".text", ".ramstub"))} B, '
          f'ROMB {0x1DB20 + 0x7A0 - (secs[".strb"][0] + secs[".strb"][1])} B, '
          f'ROMC {0x1C220 + 0xA00 - (secs[".strc"][0] + secs[".strc"][1])} B')
    bss = syms['bssEnd'] - syms['bssStart']
    print(f'  RAM: stubs {secs[".ramstub"][2]:06X} ({secs[".ramstub"][1]} B), bss {syms["bssStart"]:06X}..{syms["bssEnd"]:06X} ({bss} B)')
    print(f'  {nrefs} string references repointed, {len(OS_INPLACE)} strings translated in place, '
          f'{diff_code} bytes changed in the OS code/data area')


if __name__ == '__main__':
    main()
