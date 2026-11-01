; Menu music player for the EverDrive-MD PT-BR mod (v1 / v2 and v3): runs on the Z80 from its own 8 KB
; RAM, plays the theme's song through the YM2612 (FM only: the Z80 never touches the 68000 bus, so the
; OS keeps reading the SD card / writing the flash while it plays). One step per vblank (the VDP
; interrupts the Z80 every frame).
;
; Z80 RAM: 0x0000 this player, 0x0400 the song (make_musica.py):
;   +0 word  first command          +2 word  loop point (address of a command)
;   +4       instruments, 30 bytes each: registers 30 34 38 3C, 40.., 50.., 60.., 70.., 80.., 90.., B0, B4
;   then the commands:
;     00          go to the loop point
;     01..7F      wait that many frames
;     80+ch n     note n (octave * 12 + semitone, octave = YM block) on channel ch (0-5)
;     88+ch       key off channel ch
;     90+ch i     instrument i on channel ch
;     A0 r v      YM part I register r = v        A8 r v   part II

SONG:   equ 0x0400

        org 0
        di
        ld sp, 0x2000
        im 1
        jr start

        defs 0x38 - $, 0
        ei                      ; vblank: just wakes the halt up
        ret

start:  ld a, 0x22              ; LFO off, channel 3 normal, DAC off
        ld c, 0
        call wpart1
        ld a, 0x27
        call wpart1
        ld a, 0x2b
        call wpart1
        ld b, 5
offall: call keyoff
        dec b
        jp p, offall
        ld hl, (SONG)
        ld (pos), hl
        xor a
        ld (wcnt), a
        ei

frame:  halt
        ld a, (wcnt)
        or a
        jr z, run
        dec a
        ld (wcnt), a
        jr frame

run:    ld hl, (pos)
next:   ld a, (hl)
        inc hl
        or a
        jr nz, notend
        ld hl, (SONG + 2)
        jr next
notend: bit 7, a
        jr nz, cmd
        dec a                   ; wait a frames: this one is the first
        ld (wcnt), a
        ld (pos), hl
        jr frame

cmd:    ld c, a
        and 7
        ld b, a                 ; b = channel
        ld a, c
        and 0xf8
        cp 0x80
        jr z, note
        cp 0x88
        jr z, koff
        cp 0x90
        jr z, inst
        ld e, a
        ld a, (hl)              ; raw write: register, value
        inc hl
        ld c, (hl)
        inc hl
        push hl
        bit 3, e
        jr nz, raw2
        call wpart1
        pop hl
        jr next
raw2:   call wpart2
        pop hl
        jr next

koff:   push hl
        call keyoff
        pop hl
        jr next

note:   ld e, (hl)              ; note number
        inc hl
        push hl
        call keyoff
        ld d, 0                 ; d = octave, e = semitone
ndiv:   ld a, e
        cp 12
        jr c, nfreq
        sub 12
        ld e, a
        inc d
        jr ndiv
nfreq:  ld hl, ftab
        ld a, e
        add a, a
        add a, l                ; ftab does not cross a 256-byte page
        ld l, a
        ld e, (hl)              ; F-number low
        inc hl
        ld a, d
        add a, a
        add a, a
        add a, a
        or (hl)                 ; block << 3 | F-number high
        ld c, a
        ld a, 0xa4
        call wch
        ld c, e
        ld a, 0xa0
        call wch
        call keyon
        pop hl
        jp next

inst:   ld a, (hl)              ; instrument number
        inc hl
        push hl
        ld l, a
        ld h, 0
        add hl, hl
        ld d, h
        ld e, l                 ; de = 2i
        add hl, hl
        add hl, hl
        add hl, hl
        add hl, hl              ; hl = 32i
        or a
        sbc hl, de              ; hl = 30i
        ld de, SONG + 4
        add hl, de
        ex de, hl               ; de = the instrument
        ld hl, iregs
        ld a, 30
iloop:  push af
        ld a, (de)
        ld c, a
        ld a, (hl)
        push hl
        push de
        call wch
        pop de
        pop hl
        inc hl
        inc de
        pop af
        dec a
        jr nz, iloop
        pop hl
        jp next

; wch: register a (+ channel offset) = c on channel b (0-2 part I, 3-5 part II)
wch:    push af
        ld a, b
        cp 3
        jr nc, wch2
        pop af
        add a, b
        jr wpart1
wch2:   pop af
        add a, b
        sub 3
        jr wpart2

wpart1: push af
w1:     ld a, (0x4000)
        rlca
        jr c, w1
        pop af
        ld (0x4000), a
        ld a, c
        ld (0x4001), a
        ret

wpart2: push af
w2:     ld a, (0x4000)
        rlca
        jr c, w2
        pop af
        ld (0x4002), a
        ld a, c
        ld (0x4003), a
        ret

chcode: ld a, b                 ; key on/off register code: 0 1 2 4 5 6
        cp 3
        ret c
        inc a
        ret

keyoff: call chcode
        ld c, a
        ld a, 0x28
        jr wpart1

keyon:  call chcode
        or 0xf0
        ld c, a
        ld a, 0x28
        jr wpart1

iregs:  defb 0x30, 0x34, 0x38, 0x3c, 0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x58, 0x5c
        defb 0x60, 0x64, 0x68, 0x6c, 0x70, 0x74, 0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c
        defb 0x90, 0x94, 0x98, 0x9c, 0xb0, 0xb4

pos:    defw 0
wcnt:   defb 0

        defs 0x300 - $, 0
ftab:   defw 644, 682, 723, 766, 811, 859, 910, 965, 1022, 1083, 1147, 1215   ; C..B, A = 440 Hz at block 4
end:
