"""
Menu music of the themes (original compositions, FM only), for the Z80 player musica/z80drv.asm:
  temas/<tema>/EDMD/MUSICA.BIN  the song in the player's format (make_temas.py packs it into TEMAS.BIN)
  musica/previa/<tema>.vgm      a preview for any VGM player (made by running the real player on an
                                emulated Z80 and logging its YM2612 writes)

One song per theme, 16 bars that loop. Notation: one token per 16th note ("step"):
  C4 D#4 Bb3   a note (octave 4: A4 = 440 Hz)     .  hold      -  key off
  tokens may carry a length: "E5:4" (4 steps), "-:8"
Drum tokens: k kick, s snare, h hat, o open hat, . nothing.

    python musica/make_musica.py           (needs: pip install z80; the player: musica/build.sh in WSL)
"""
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SONG_ADDR = 0x0400
SONG_MAX = 0x1C00 - SONG_ADDR           # 13 sectors in TEMAS.BIN (the player's stack sits under 0x2000)
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


# ---------------------------------------------------------------------------------------- instruments
def op(mul=1, tl=0, ar=31, d1r=0, d2r=0, sl=0, rr=15, dt=0, rs=0, am=0):
    return dict(mul=mul, tl=tl, ar=ar, d1r=d1r, d2r=d2r, sl=sl, rr=rr, dt=dt, rs=rs, am=am)


def patch(alg, fb, s1, s3, s2, s4):
    """30 bytes in the player's register order (slots S1 S3 S2 S4 = register offsets 0 4 8 C)"""
    ops = (s1, s3, s2, s4)
    out = [o['dt'] << 4 | o['mul'] for o in ops] + [o['tl'] for o in ops]
    out += [o['rs'] << 6 | o['ar'] for o in ops] + [o['am'] << 7 | o['d1r'] for o in ops]
    out += [o['d2r'] for o in ops] + [o['sl'] << 4 | o['rr'] for o in ops] + [0, 0, 0, 0]
    out += [fb << 3 | alg, 0xC0]
    assert len(out) == 30 and all(0 <= v < 256 for v in out)
    return bytes(out)


MUTE = op(tl=127)
INSTR = {
    # alg 0 chain, feedback: round synth bass
    'bass': patch(0, 5, op(mul=1, tl=34, d1r=10, d2r=4, sl=3, rr=10), op(mul=2, tl=48, d1r=12, sl=5, rr=10),
                  op(mul=1, tl=26, d1r=9, d2r=3, sl=4, rr=10), op(mul=1, tl=10, d1r=6, d2r=2, sl=2, rr=11)),
    # slap-ish funk bass: brighter, faster decay
    'slap': patch(0, 6, op(mul=3, tl=30, d1r=16, d2r=6, sl=6, rr=12), op(mul=1, tl=40, d1r=14, sl=6, rr=12),
                  op(mul=1, tl=24, d1r=12, d2r=5, sl=5, rr=12), op(mul=1, tl=10, d1r=10, d2r=4, sl=3, rr=12)),
    # alg 4: two 2-op voices, a bright lead
    'lead': patch(4, 5, op(mul=1, tl=30, d1r=4, d2r=2, sl=2, rr=7), op(mul=2, tl=38, d1r=5, sl=3, rr=7, dt=3),
                  op(mul=1, tl=18, d1r=2, d2r=1, sl=1, rr=7), op(mul=2, tl=26, d1r=3, d2r=1, sl=2, rr=7, dt=7)),
    # softer, rounder lead (flute-ish)
    'flute': patch(4, 2, op(mul=1, tl=40, ar=24, d1r=3, sl=1, rr=6), op(mul=1, tl=44, ar=24, d1r=3, sl=1, rr=6, dt=3),
                   op(mul=1, tl=20, ar=22, d1r=1, sl=1, rr=6), op(mul=1, tl=26, ar=22, d1r=1, sl=1, rr=6, dt=7)),
    # plucked arpeggio / electric piano
    'pluck': patch(4, 4, op(mul=3, tl=36, d1r=14, d2r=6, sl=6, rr=9), op(mul=1, tl=42, d1r=12, sl=6, rr=9),
                   op(mul=1, tl=24, d1r=11, d2r=5, sl=7, rr=8), op(mul=2, tl=32, d1r=10, d2r=5, sl=7, rr=8)),
    # nylon guitar-ish pluck (warm)
    'guitar': patch(4, 3, op(mul=2, tl=34, d1r=12, d2r=5, sl=5, rr=8), op(mul=1, tl=36, d1r=10, sl=5, rr=8),
                    op(mul=1, tl=22, d1r=8, d2r=4, sl=6, rr=8), op(mul=1, tl=28, d1r=7, d2r=3, sl=6, rr=8, dt=3)),
    # clavinet for the funk
    'clav': patch(4, 6, op(mul=5, tl=34, d1r=18, d2r=8, sl=8, rr=12), op(mul=1, tl=38, d1r=16, sl=8, rr=12),
                  op(mul=1, tl=24, d1r=14, d2r=7, sl=8, rr=12), op(mul=3, tl=34, d1r=14, d2r=7, sl=8, rr=12)),
    # pad: alg 7, slow attack, detuned
    'pad': patch(7, 0, op(mul=1, tl=36, ar=12, d1r=2, sl=2, rr=5, dt=1), op(mul=2, tl=44, ar=12, d1r=2, sl=2, rr=5, dt=5),
                 op(mul=1, tl=36, ar=11, d1r=2, sl=2, rr=5, dt=6), op(mul=1, tl=40, ar=13, d1r=2, sl=2, rr=5, dt=2)),
    # brass stab for the 16-bit rock
    'brass': patch(2, 6, op(mul=1, tl=32, ar=24, d1r=6, d2r=3, sl=3, rr=8), op(mul=1, tl=40, ar=26, d1r=8, sl=4, rr=8),
                   op(mul=1, tl=30, ar=28, d1r=6, sl=3, rr=8), op(mul=1, tl=14, ar=24, d1r=4, d2r=2, sl=2, rr=8)),
    # drums: only S4 / S1 sound (alg 7), the others muted
    'kick': patch(7, 0, MUTE, MUTE, op(mul=1, tl=40, d1r=24, sl=15, rr=15), op(mul=0, tl=4, d1r=17, d2r=10, sl=12, rr=15)),
    'snare': patch(7, 7, op(mul=15, tl=10, d1r=20, d2r=12, sl=15, rr=15), MUTE, MUTE,
                   op(mul=1, tl=18, d1r=22, sl=15, rr=15)),
    'hat': patch(7, 7, op(mul=15, tl=24, d1r=26, d2r=20, sl=15, rr=15), MUTE, MUTE, MUTE),
    'ohat': patch(7, 7, op(mul=15, tl=26, d1r=16, d2r=10, sl=15, rr=12), MUTE, MUTE, MUTE),
}
DRUM = {'k': ('kick', 'C2'), 's': ('snare', 'C4'), 'h': ('hat', 'C7'), 'o': ('ohat', 'C7')}


def note_num(tok):
    n = NOTE[tok[0]]
    rest = tok[1:]
    while rest and rest[0] in '#b':
        n += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return int(rest) * 12 + n


def steps(text):
    """notation -> list of events per step: ('on', n) / ('off',) / None (hold); "|" separates bars of 16"""
    if '|' in text:
        out = []
        for k, bar in enumerate(text.split('|')):
            ev = steps(bar)
            assert len(ev) == 16, f'bar {k + 1}: {len(ev)} steps: {bar.strip()}'
            out += ev
        return out
    out = []
    for tok in text.split():
        length = 1
        if ':' in tok:
            tok, length = tok.split(':')
            length = int(length)
        if tok == '.':
            ev = None
        elif tok == '-':
            ev = ('off',)
        else:
            ev = ('on', note_num(tok))
        out += [ev] + [None] * (length - 1)
    return out


def drum_steps(text):
    out = []
    for ch in text.replace(' ', ''):
        out.append(None if ch == '.' else ('drum', ch))
    return out


# ---------------------------------------------------------------------------------------- harmony helpers
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11),
        'sus': (0, 5, 7), 'dim': (0, 3, 6)}


def chord(name, octave):
    root = name[0]
    rest = name[1:]
    acc = ''
    if rest[:1] in ('#', 'b'):
        acc, rest = rest[0], rest[1:]
    base = note_num(root + acc + str(octave))
    return [base + i for i in QUAL[rest]]


def name_of(n):
    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][n % 12] + str(n // 12)


def bass_line(chords, pattern, octave=2):
    """pattern over 16 steps: R root, O root an octave up, 5 fifth, 3 third, 7 seventh, . hold, - off"""
    toks = []
    for c in chords:
        t = chord(c, octave)
        for p in pattern.replace(' ', ''):
            toks.append({'R': name_of(t[0]), 'O': name_of(t[0] + 12), '5': name_of(t[2]), '3': name_of(t[1]),
                         '7': name_of(t[3] if len(t) > 3 else t[0] + 10), '.': '.', '-': '-'}[p])
    return ' '.join(toks)


def arp(chords, pattern, octave=4):
    """pattern over 16 steps: digits = chord tone (0 root, 1 third, 2 fifth, 3 = root + 12, 4 = third + 12)"""
    toks = []
    for c in chords:
        t = chord(c, octave)
        t = t[:3] + [t[0] + 12, t[1] + 12, t[2] + 12]
        for p in pattern.replace(' ', ''):
            toks.append(name_of(t[int(p)]) if p.isdigit() else p)
    return ' '.join(toks)


def pads(chords, tone, octave=4):
    """one long note per bar: chord tone (0 root, 1 third, 2 fifth)"""
    return ' '.join(f'{name_of(chord(c, octave)[tone])}:16' for c in chords)


# ---------------------------------------------------------------------------------------- the songs
# channel layout: 0 bass, 1 lead, 2 arpeggio, 3 pad / second voice, 4 kick + snare, 5 hats
def song_padrao():
    """PADRÃO: clean techy groove, A minor, 128 bpm"""
    ch = ['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'E'] * 2
    lead_a = ('E5:4 A5:2 B5:2 C6:4 B5:2 A5:2 | A5:4 F5:4 C5:4 F5:2 G5:2 | G5:4 E5:4 C5:4 E5:2 G5:2 | '
              'D5:4 G5:4 B5:4 D6:4 | E5:4 A5:2 B5:2 C6:4 E6:4 | D6:4 C6:2 A5:2 F5:4 A5:4 | '
              'G5:2 E5:2 C5:2 E5:2 G5:4 C6:4 | B5:8 G#5:8')
    lead_b = ('A5:2 -:2 A5:2 C6:2 E6:4 D6:2 C6:2 | C6:4 A5:4 F5:8 | E5:2 G5:2 C6:2 G5:2 E6:4 D6:4 | '
              'D6:4 B5:4 G5:8 | A5:2 C6:2 E6:2 A6:2 G6:4 E6:4 | F6:4 E6:2 C6:2 A5:8 | '
              'G5:4 C6:4 E6:4 G6:4 | E6:8 G#5:4 B5:4')
    return dict(frames=7, parts=[
        ('bass', bass_line(ch, 'R.-O R.-O R.-O R.5.')),
        ('lead', lead_a + ' | ' + lead_b),
        ('pluck', arp(ch, '0124 2410 0124 2431')),
        ('pad', pads(ch, 1)),
        ('drums', 'k...s...k.k.s...' * 16),
        ('drums', '..h...h...h...ho' * 16)])


def song_rgpoa():
    """RG POA: a milonga at sunset (3-3-2 bass), E minor, warm guitar"""
    ch = ['Em', 'Em', 'Am', 'Am', 'B7', 'B7', 'Em', 'E7', 'Am', 'Am', 'Em', 'Em', 'B7', 'B7', 'Em', 'Em']
    lead = ('B4:3 E5:3 G5:2 F#5:4 E5:4 | D5:3 E5:3 F#5:2 G5:8 | A5:3 G5:3 F#5:2 E5:4 C5:4 | '
            'E5:3 D5:3 C5:2 B4:8 | D#5:3 F#5:3 A5:2 B5:4 A5:4 | G5:3 F#5:3 E5:2 D#5:8 | '
            'E5:3 G5:3 B5:2 E6:4 D6:4 | D6:3 B5:3 G#5:2 E5:8 | '
            'C6:3 B5:3 A5:2 E5:4 A5:4 | C6:3 B5:3 A5:2 G5:8 | G5:3 F#5:3 E5:2 B4:4 E5:4 | '
            'G5:3 A5:3 B5:2 E5:8 | F#5:3 A5:3 C6:2 B5:4 A5:4 | G5:3 F#5:3 E5:2 D#5:8 | '
            'E5:3 B4:3 G4:2 E4:4 B4:4 | E5:16')
    return dict(frames=8, parts=[
        ('bass', bass_line(ch, 'R..5..R.R..5..O.')),
        ('flute', lead),
        ('guitar', arp(ch, '0.1.2.0.1.2.4.2.', 3)),
        ('pad', pads(ch, 2, 3)),
        ('drums', 'k..s..k.k..s..s.' * 16),
        ('drums', 'h.h.h.h.h.h.h.h.' * 16)])


def song_retrochimp():
    """RETROCHIMP: 70s funk with slap bass and clav, D dorian"""
    ch = ['Dm7', 'Dm7', 'G7', 'G7', 'Dm7', 'Dm7', 'Am7', 'G7'] * 2
    lead = ('- -:3 A5:2 C6:2 D6:2 C6:2 A5:2 G5:2 | A5:4 -:4 F5:2 G5:2 A5:4 | B5:2 D6:2 B5:2 G5:2 F5:4 D5:4 | '
            'F5:2 G5:2 B5:4 A5:4 G5:4 | -:2 D6:2 F6:2 E6:2 D6:2 C6:2 A5:2 G5:2 | A5:8 C6:4 D6:4 | '
            'E6:2 C6:2 A5:2 G5:2 E5:4 G5:4 | F5:4 E5:4 D5:8 | '
            'D6:2 -:2 D6:2 C6:2 D6:4 F6:4 | E6:2 D6:2 C6:2 A5:2 C6:8 | B5:2 -:2 B5:2 A5:2 G5:4 B5:4 | '
            'D6:4 C6:4 B5:4 G5:4 | A5:2 C6:2 D6:2 F6:2 G6:4 F6:4 | D6:4 C6:4 A5:8 | '
            'C6:2 A5:2 G5:2 E5:2 G5:4 A5:4 | D6:16')
    return dict(frames=7, parts=[
        ('slap', bass_line(ch, 'R.-R -.O- R.-5 -7O-')),
        ('lead', lead),
        ('clav', arp(ch, '-.21 -.2- -.21 -.42', 4)),
        ('pad', pads(ch, 1, 4)),
        ('drums', 'k..sk.k.s..k.ks.' * 16),
        ('drums', 'hhhohhhhhhhohhhh' * 16)])


def song_sega16():
    """SEGA 16: fast 16-bit rock, E major, brass + lead"""
    ch = ['E', 'C#m', 'A', 'B', 'E', 'C#m', 'F#m', 'B'] * 2
    lead = ('E5:2 E5:2 F#5:2 G#5:2 B5:4 G#5:4 | C#6:4 B5:2 G#5:2 E5:8 | A5:2 B5:2 C#6:2 E6:2 C#6:4 A5:4 | '
            'B5:8 D#6:4 F#6:4 | E6:2 D#6:2 E6:2 F#6:2 G#6:4 E6:4 | C#6:2 B5:2 C#6:2 E6:2 G#6:8 | '
            'F#6:4 E6:2 C#6:2 A5:4 C#6:4 | D#6:8 B5:8 | '
            'G#5:4 B5:4 E6:4 G#6:4 | G#6:2 F#6:2 E6:2 C#6:2 E6:8 | A6:4 G#6:2 F#6:2 E6:4 C#6:4 | '
            'D#6:4 F#6:4 B6:8 | G#6:2 F#6:2 E6:2 B5:2 G#5:4 B5:4 | C#6:4 E6:4 G#6:8 | '
            'F#6:2 G#6:2 A6:2 F#6:2 C#6:4 A5:4 | B5:4 D#6:4 F#6:4 B6:4')
    return dict(frames=5, parts=[
        ('bass', bass_line(ch, 'RRORRROR RRORR5O5')),
        ('lead', lead),
        ('brass', arp(ch, '2.-.2.-.2.-.4.3.', 4)),
        ('pluck', arp(ch, '0101210121012101', 3)),
        ('drums', 'k.s.k.s.kks.k.s.' * 16),
        ('drums', 'hhhhhhhhhhhhhhho' * 16)])


def song_outrun():
    """OUTRUN: driving synthwave, D minor, pulsing 16th bass"""
    ch = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'C', 'A'] * 2
    lead = ('D5:6 E5:2 F5:4 A5:4 | Bb5:6 A5:2 F5:8 | A5:6 G5:2 F5:4 C5:4 | E5:8 G5:8 | '
            'D5:4 F5:4 A5:4 D6:4 | D6:6 C6:2 Bb5:8 | C6:4 Bb5:4 A5:4 G5:4 | A5:8 C#6:8 | '
            'D6:6 C6:2 A5:4 F5:4 | Bb5:4 D6:4 F6:8 | F6:4 E6:2 D6:2 C6:4 A5:4 | G5:4 C6:4 E6:8 | '
            'F6:4 E6:4 D6:4 A5:4 | Bb5:4 C6:4 D6:4 F6:4 | E6:4 D6:4 C6:4 G5:4 | A5:8 E6:8')
    return dict(frames=6, parts=[
        ('bass', bass_line(ch, 'RRORRROR RRORRROR')),
        ('lead', lead),
        ('pluck', arp(ch, '0240 2402 4024 0242', 4)),
        ('pad', pads(ch, 2, 4)),
        ('drums', 'k...s...k...s...' * 15 + 'k...s...s.s.ssss'),
        ('drums', '..h...h...h...h.' * 16)])


def song_synthwave():
    """SYNTHWAVE: slow and dreamy, C minor, pads and a soft arpeggio"""
    ch = ['Cm', 'Ab', 'Eb', 'Bb', 'Cm', 'Ab', 'Fm', 'G'] * 2
    lead = ('G5:8 Eb5:4 F5:4 | Eb5:8 C5:8 | Bb4:8 Eb5:4 G5:4 | F5:16 | G5:8 Bb5:4 C6:4 | '
            'C6:8 Ab5:8 | Ab5:4 G5:4 F5:4 C5:4 | D5:16 | '
            'C6:8 Bb5:4 G5:4 | Ab5:8 Eb5:8 | G5:4 F5:4 Eb5:4 Bb4:4 | D5:8 F5:8 | Eb5:4 G5:4 C6:4 Eb6:4 | '
            'Eb6:8 C6:8 | C6:4 Ab5:4 F5:4 Ab5:4 | B5:16')
    return dict(frames=9, parts=[
        ('bass', bass_line(ch, 'R...R...R...R.O.')),
        ('flute', lead),
        ('pluck', arp(ch, '0123 4321 0123 4321', 4)),
        ('pad', pads(ch, 1, 4)),
        ('drums', 'k.......s.......' * 16),
        ('drums', '....h.......h...' * 16)])


def song_maddruga():
    """MADDRUGA: late-night arcade groove, G minor"""
    ch = ['Gm', 'Gm', 'Eb', 'F', 'Gm', 'Gm', 'Cm', 'D'] * 2
    lead = ('G5:2 -:2 G5:2 Bb5:2 D6:2 -:2 C6:2 Bb5:2 | A5:2 Bb5:2 G5:4 -:8 | G5:2 -:2 Bb5:2 C6:2 Eb6:4 D6:4 | '
            'C6:2 Bb5:2 A5:2 F5:2 A5:8 | D6:2 -:2 D6:2 C6:2 Bb5:2 -:2 A5:2 G5:2 | Bb5:2 A5:2 G5:4 D5:8 | '
            'Eb5:2 G5:2 C6:2 Eb6:2 D6:4 C6:4 | D6:4 A5:4 F#5:8 | '
            'G6:4 F6:2 D6:2 Bb5:4 G5:4 | A5:2 Bb5:2 D6:4 G6:8 | Eb6:4 D6:2 C6:2 Bb5:4 G5:4 | '
            'F5:4 A5:4 C6:8 | D6:2 -:2 D6:2 F6:2 G6:4 F6:4 | D6:4 Bb5:4 G5:8 | '
            'C6:2 Eb6:2 G6:2 Eb6:2 C6:4 Eb6:4 | D6:4 F#6:4 A6:8')
    return dict(frames=7, parts=[
        ('slap', bass_line(ch, 'R-RO -R5- R-RO -7O5')),
        ('lead', lead),
        ('pluck', arp(ch, '0.2.4.2.0.2.4.3.', 4)),
        ('pad', pads(ch, 2, 3)),
        ('drums', 'k...s..k..k.s...' * 16),
        ('drums', 'h.hhh.hhh.hhh.ho' * 16)])


SONGS = {'padrao': song_padrao, 'rgpoa': song_rgpoa, 'retrochimp': song_retrochimp, 'sega16': song_sega16,
         'outrun': song_outrun, 'synthwave': song_synthwave, 'maddrugamers': song_maddruga}


# ---------------------------------------------------------------------------------------- compiler
def compile_song(spec):
    names = list(INSTR)
    used = sorted({p for p, _ in spec['parts'] if p != 'drums'} | {d for d, _ in DRUM.values()})
    idx = {n: i for i, n in enumerate(used)}
    tracks = []
    for p, text in spec['parts']:
        ev = drum_steps(text) if p == 'drums' else steps(text)
        tracks.append((p, ev))
    n = max(len(ev) for _, ev in tracks)
    assert all(len(ev) == n for _, ev in tracks), [(p, len(ev)) for p, ev in tracks]
    body = bytearray()
    for ch, (p, _) in enumerate(tracks):
        if p != 'drums':
            body += bytes([0x90 + ch, idx[p]])
    cur = {}
    wait = 0
    loop_at = len(body)

    def flush():
        nonlocal wait
        while wait:
            w = min(wait, 127)
            body.append(w)
            wait -= w

    for s in range(n):
        evs = bytearray()
        for ch, (p, ev) in enumerate(tracks):
            e = ev[s]
            if e is None:
                continue
            if e[0] == 'off':
                evs.append(0x88 + ch)
            elif e[0] == 'on':
                evs += bytes([0x80 + ch, e[1]])
            else:
                inst, nt = DRUM[e[1]]
                if cur.get(ch) != inst:
                    evs += bytes([0x90 + ch, idx[inst]])
                    cur[ch] = inst
                evs += bytes([0x80 + ch, note_num(nt)])
        if evs:
            flush()
            body += evs
        wait += spec['frames']
    flush()
    body.append(0)
    head = 4 + 30 * len(used)
    first = SONG_ADDR + head
    out = struct.pack('<HH', first, first + loop_at) + b''.join(INSTR[u] for u in used) + body
    assert len(out) <= SONG_MAX, f'song too long: {len(out)}'
    return bytes(out), n * spec['frames']


# ---------------------------------------------------------------------------------------- the player on a Z80
def run_player(drv, song, frames):
    """the real player on an emulated Z80: its YM2612 writes per frame"""
    import z80
    m = z80.Z80Machine()
    mem = bytearray(0x10000)
    mem[0:len(drv)] = drv
    mem[SONG_ADDR:SONG_ADDR + len(song)] = song
    m.set_memory_block(0, bytes(mem))
    log, addr = [], [0, 0]

    def wr(a, v):
        if 0x4000 <= a <= 0x4003:
            if a & 1:
                log.append((frame[0], a >> 1 & 1, addr[a >> 1 & 1], v))
            else:
                addr[a >> 1 & 1] = v
        else:
            m.memory[a] = v

    def rd(a):
        return 0 if 0x4000 <= a <= 0x4003 else m.memory[a]
    m.set_read_callback(rd)
    m.set_write_callback(wr)
    m.mark_addrs(0x4000, 4, m.READ_MARK | m.WRITE_MARK)
    frame = [0]
    for f in range(frames):
        frame[0] = f
        m.ticks_to_stop = 59659             # 3.58 MHz / 60
        m.run()
        m.on_handle_active_int()
    return log


def vgm(log, frames, loop_frame=0):
    """YM2612 writes per frame -> VGM 1.50 (44100 Hz, 735 samples per frame)"""
    data = bytearray()
    loop_off = None
    last = 0
    for f in range(frames + 1):
        if f == loop_frame and loop_off is None:
            loop_off = len(data)
        for _, port, r, v in [x for x in log if x[0] == f]:
            data += bytes([0x52 + port, r, v])
        if f < frames:
            data += b'\x62'
    data.append(0x66)
    hdr = bytearray(0x40)
    hdr[0:4] = b'Vgm '
    struct.pack_into('<I', hdr, 0x04, 0x40 + len(data) - 4)
    struct.pack_into('<I', hdr, 0x08, 0x150)
    struct.pack_into('<I', hdr, 0x18, frames * 735)
    struct.pack_into('<I', hdr, 0x1C, 0x40 + loop_off - 0x1C)
    struct.pack_into('<I', hdr, 0x20, (frames - loop_frame) * 735)
    struct.pack_into('<I', hdr, 0x24, 60)
    struct.pack_into('<I', hdr, 0x2C, 7670453)
    struct.pack_into('<I', hdr, 0x34, 0x40 - 0x34)
    return bytes(hdr + data)


def build_driver():
    p = str(HERE / 'build.sh').replace('\\', '/')
    r = subprocess.run(['wsl', '-d', 'Debian', '--', 'bash', f'/mnt/{p[0].lower()}{p[2:]}'], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    return (HERE / 'z80drv.bin').read_bytes()


def main():
    drv = build_driver()
    assert len(drv) <= SONG_ADDR, len(drv)
    (HERE / 'previa').mkdir(exist_ok=True)
    only = sys.argv[1:]
    for name, fn in SONGS.items():
        if only and name not in only:
            continue
        song, loop_frames = compile_song(fn())
        (ROOT / 'temas' / name / 'EDMD' / 'MUSICA.BIN').write_bytes(song)
        start = 2                                   # the player starts on the first vblank
        log = run_player(drv, song, start + 2 * loop_frames + 2)
        keyons = sum(1 for _, p, r, v in log if p == 0 and r == 0x28 and v & 0xF0)
        (HERE / 'previa' / f'{name}.vgm').write_bytes(vgm([(f - start, p, r, v) for f, p, r, v in log
                                                         if f >= start], loop_frames * 2, loop_frames))
        print(f'{name:12} {len(song):5} bytes, loop {loop_frames / 60:5.1f} s, {keyons} notes played in 2 loops')


if __name__ == '__main__':
    main()
