"""
PNG -> /EDMD/BANNER.ART: the banner shown on top of the menus and the game list (v1 and v3).

Same layout as the box-art .ART files, so the OS loads it with the same code:
  - 32 bytes: 16 big-endian CRAM words (entries 1..14 are used, 0 and 15 belong to the OS).
    Entry 1 is always the menu highlight colour (crimson, the bar behind "[ LIMPAR RECENTES ]"),
    so the image itself gets 13 colours (14 when it uses that crimson too).
  - 108 tiles 4bpp, row-major 36 x 3 (288 x 24 px)
  - zero padding to 3584 bytes (7 sectors); optionally, at offset 0xDA0, the theme colours that come
    with the banner: 'TEMA' + 6 words (backdrop, menu bar, bar shadow, text, dim text, accent), used by
    both firmwares instead of the chosen theme

The image is cropped/resized to 288x24 when needed. Pixel art with up to 13 colours (plus that
crimson) is kept exact; anything with more colours is reduced to 13 (no dithering).

    python make_banner.py banner.png                  # writes BANNER.ART next to the PNG
    python make_banner.py logo.png E:/EDMD/BANNER.ART
    python make_banner.py logo.png E:/EDMD/BANNER.ART --cores 000,0A0,040,EEE,282,2E4   (0BGR hex)
"""
import struct
import sys
from pathlib import Path

from PIL import Image

W, H = 288, 24
HIGHLIGHT = 0x00A       # palette 2 colour 1: menu highlight bar
FILE_SIZE = 7 * 512
THEME_OFF = 0xDA0       # after the 108 tiles


def md9(r, g, b):
    q = lambda v: min(7, (v + 18) // 36)
    return (q(b) * 2 << 8) | (q(g) * 2 << 4) | (q(r) * 2)


def rgb(c):
    return ((c >> 1 & 7) * 36, (c >> 5 & 7) * 36, (c >> 9 & 7) * 36)


def pixels(im):
    raw = im.tobytes()
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]


def convert(src):
    im = Image.open(src).convert('RGB')
    if im.size != (W, H):
        scale = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
        left, top = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((left, top, left + W, top + H))
    im = Image.frombytes('RGB', im.size, bytes(v for p in pixels(im) for v in rgb(md9(*p))))
    colours = sorted({md9(*p) for p in pixels(im)} - {HIGHLIGHT})
    if len(colours) > 13:
        im = im.quantize(colors=13, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
        colours = sorted({md9(*p) for p in pixels(im)} - {HIGHLIGHT})
    index = {c: i + 2 for i, c in enumerate(colours)}
    index[HIGHLIGHT] = 1
    pal = [0] * 16
    for c, i in index.items():
        pal[i] = c
    px = im.load()
    out = bytearray(struct.pack('>16H', *pal))
    for ty in range(3):
        for tx in range(36):
            for y in range(ty * 8, ty * 8 + 8):
                row = [index[md9(*px[x, y])] for x in range(tx * 8, tx * 8 + 8)]
                out += bytes(row[i] << 4 | row[i + 1] for i in range(0, 8, 2))
    return bytes(out.ljust(FILE_SIZE, b'\0')), len(colours)


def main():
    args = sys.argv[1:]
    cores = None
    if '--cores' in args:
        i = args.index('--cores')
        cores = [int(c, 16) for c in args[i + 1].split(',')]
        assert len(cores) == 6 and all(c & ~0xEEE == 0 for c in cores), 'six 0BGR colours, even digits 0-E'
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    dst = Path(args[1]) if len(args) > 1 else src.with_name('BANNER.ART')
    data, n = convert(src)
    if cores:
        data = data[:THEME_OFF] + b'TEMA' + struct.pack('>6H', *cores) + data[THEME_OFF + 16:]
    dst.write_bytes(data)
    print(f'{dst}: {n} colours, {len(data)} bytes' + (', theme colours' if cores else ''))


if __name__ == '__main__':
    main()
