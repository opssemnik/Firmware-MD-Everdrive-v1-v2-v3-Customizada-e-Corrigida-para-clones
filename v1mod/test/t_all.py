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

step = sys.argv[1]
# A: browse USA, favourite Columns, start Blockout
m = new()
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('a', after=120); m.press('down'); m.press('down'); m.press('a', after=200)
for _ in range(4): m.press('down')
m.press('a', after=150)
if step == 'info': show(m, 'rom info'); m.screen('shot_rominfo.png'); sys.exit()
m.press('b', after=60); m.press('up'); m.press('a', after=200); m.press('a', after=60)
m.press('down'); m.press('down'); m.press('a', after=200); m.press('up'); m.press('start', after=600)
print('A:', m.stopped, lists(m)); F = flash(m)

if step in ('all', 'recent'):
    m = new(F); m.press('down'); m.press('down'); m.press('a', after=200)
    show(m, 'recent list'); m.screen('shot_recent.png')
    m.press('a', after=900); print('recent play ->', m.stopped, '|', ' / '.join(l.strip() for l in m.text().splitlines() if l.strip())[:120])
if step in ('all', 'clear'):
    m = new(F); m.press('down'); m.press('down'); m.press('a', after=200)
    m.press('down'); show(m, 'recent list, cursor on Limpar recentes'); m.screen('v1_recent_clear.png')
    m.press('a', after=900); show(m, 'after Limpar recentes'); print('lists:', lists(m))
if step in ('all', 'fav'):
    m = new(F); [m.press('down') for _ in range(3)]; m.press('a', after=200)
    show(m, 'fav list'); m.press('a', after=150); show(m, 'fav submenu'); m.screen('shot_favsub.png')
    m.press('down'); m.press('a', after=300); show(m, 'after remove'); m.press('a', after=200); show(m, 'fav list again')
    print('lists:', lists(m))
if step in ('all', 'random'):
    m = new(F); [m.press('down') for _ in range(4)]; m.press('a', after=1500)
    print('random ->', m.stopped, lists(m).get('recent'))
if step in ('all', 'tools'):
    m = new(F); [m.press('down') for _ in range(7)]; m.press('a', after=200)
    show(m, 'toolbox'); m.screen('shot_toolbox.png')
    [m.press('down') for _ in range(4)]; m.press('a', after=200); show(m, 'about'); m.screen('shot_about.png')
    m.press('a', after=100); m.press('b', after=150); show(m, 'back to main')
if step in ('all', 'options'):
    m = new(F); [m.press('down') for _ in range(5)]; m.press('a', after=200)
    show(m, 'options'); m.screen('shot_options.png')
    m.press('a', after=60); m.press('b', after=400); print('options saved:', lists(m))
if step in ('all', 'theme'):
    m = new(F); [m.press('down') for _ in range(8)]; m.press('a', after=300)
    show(m, 'theme 1'); m.screen('shot_theme1.png'); print('theme saved:', lists(m))
    m2 = new(flash(m)); show(m2, 'after reboot'); m2.screen('shot_theme1_reboot.png')
    print('cram pal0:', [hex(c) for c in m2.cram[:3]], hex(m2.cram[15]))
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
