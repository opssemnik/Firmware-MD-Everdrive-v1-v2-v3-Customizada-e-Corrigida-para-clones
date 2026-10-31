"""
temas/<nome>/EDMD/BANNER.ART + WALL.ART -> /EDMD/TEMAS.BIN, every theme in one file (v1 / v2 and v3).

The firmware lists the names in the menu (v1 / v2: main menu "Tema", v3: Opções -> "Tema Visual") and
loads the chosen theme's banner, wallpaper and colours straight from this file.

Layout (512-byte sectors):
  sector 0     : 'TMAS', u16 count, u16 SLOT (sectors per theme), u16 WALL (wallpaper sector inside
                 a slot), then from 0x10 one 16-byte entry per theme: the name (up to 10 characters,
                 zero padded, accents in the v3 font codes 0x80..0x87 = ç ã õ á é ú ó Ã)
  theme i      : sector 1 + i * SLOT: BANNER.ART (7 sectors, theme colours at 0xDA0)
                 sector 1 + i * SLOT + WALL: WALL.ART (up to 56 sectors)

    python make_temas.py                     # writes sd/EDMD/TEMAS.BIN
    python make_temas.py E:/EDMD/TEMAS.BIN
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SLOT, WALL = 64, 8
ORDER = [   # folder in temas/, name in the menu (the order is the theme number saved in the settings)
    ('padrao', 'PADRÃO'),
    ('rgpoa', 'RG POA'),
    ('sega16', 'SEGA 16'),
    ('outrun', 'OUTRUN'),
    ('synthwave', 'SYNTHWAVE'),
    ('maddrugamers', 'MADDRUGA'),
    ('retrochimp', 'RETROCHIMP'),
]
ACCENTS = 'çãõáéúóÃ'


def enc(name):
    b = bytes(0x80 + ACCENTS.index(c) if c in ACCENTS else ord(c) for c in name)
    assert len(b) <= 10 and all(0x20 <= c < 0x7F or 0x80 <= c <= 0x87 for c in b), name
    return b


def build():
    assert len(ORDER) <= 16                              # the v1 / v2 extension keeps 16 names
    out = bytearray(b'TMAS' + struct.pack('>HHH', len(ORDER), SLOT, WALL)).ljust(16, b'\0')
    for _, name in ORDER:
        out += enc(name).ljust(16, b'\0')
    out = out.ljust(512, b'\0')
    for folder, name in ORDER:
        d = ROOT / 'temas' / folder / 'EDMD'
        banner, wall = (d / 'BANNER.ART').read_bytes(), (d / 'WALL.ART').read_bytes()
        assert len(banner) == 7 * 512 and banner[0xDA0:0xDA4] == b'TEMA', f'{folder}: BANNER.ART without colours'
        assert len(wall) <= (SLOT - WALL) * 512 and struct.unpack('>H', wall[:2])[0] <= 800, folder
        slot = banner.ljust(WALL * 512, b'\0') + wall
        out += slot.ljust(SLOT * 512, b'\0')
    return bytes(out)


def main():
    dst = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'sd' / 'EDMD' / 'TEMAS.BIN'
    data = build()
    dst.write_bytes(data)
    print(f'{dst}: {len(ORDER)} temas, {len(data)} bytes')


if __name__ == '__main__':
    main()
