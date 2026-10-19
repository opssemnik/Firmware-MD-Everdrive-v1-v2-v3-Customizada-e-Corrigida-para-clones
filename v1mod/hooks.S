/*
 * RAM guard stubs + browser hook.
 *
 * Every patched call site in the RAM-resident OS jumps to a stub in RAM first. The stub checks
 * the build signature at the end of the OS flash image (0x1FFF8) and only then enters the new
 * code in flash; otherwise it runs the stock routine. This keeps the OS usable while the
 * "update OS" tool has the flash half-written (it returns to the toolbox on errors).
 */

#define SIG_ADDR 0x1FFF8
#define SIG_MAGIC 0x50544252    /* 'PTBR' */

.macro CHECK fail
    cmpi.l  #SIG_MAGIC, (SIG_ADDR).l
    bne.s   \fail
    cmpi.l  #BUILD_ID, (SIG_ADDR + 4).l
    bne.s   \fail
.endm

    .section .ramstub, "ax"

    .globl  ramMain
ramMain:                        /* main menu (was jsr $ff528e) */
    CHECK   1f
    jmp     myMainMenu
1:  jmp     0xFF528E

    .globl  ramMenuClear
ramMenuClear:                   /* osMenu screen clear (was jsr $ff7fb2) */
    CHECK   1f
    jmp     myMenuClear
1:  jmp     0xFF7FB2

    .globl  ramSave
ramSave:                        /* settings save entry (stock prologue overwritten by jmp) */
    CHECK   1f
    jmp     mySaveSettings
1:  lea     -0x200(%sp), %sp
    move.l  %d2, -(%sp)
    jmp     0xFF5C84

    .globl  ramAbout
ramAbout:                       /* toolbox "about" (was bsr.w $ff7342) */
    CHECK   1f
    jmp     myAbout
1:  jmp     0xFF7342

    .globl  ramAHook
ramAHook:                       /* browser, A pressed: jsr from $ff6640, a0 = entry */
    CHECK   1f
    jmp     aHook
1:  tst.w   10(%a0)             /* stock: file -> continue at $ff6716 */
    bne.s   2f
    addq.l  #4, %sp
    jmp     0xFF6716
2:  rts                         /* directory -> back to $ff6646 */

    .globl  ramIdle
ramIdle:                        /* browser waiting for input (was a PAD polling loop at $ff660e) */
    CHECK   1f
    jmp     browseIdle
1:  tst.w   (0xFFE30C).l        /* stock: spin until a button, resetting the repeat counter */
    bne.s   2f
    clr.w   %d5
    bra.s   1b
2:  rts

    .globl  ramCheatApply
ramCheatApply:                  /* GG code list, START: apply (was bsr.w $ff3d1c; addq.l #4,sp at $ff3fec) */
    move.l  4(%sp), -(%sp)
    jsr     0xFF3D1C            /* stock: patch the codes into the loaded game */
    addq.l  #4, %sp
    movea.l (%sp)+, %a0
    addq.l  #4, %sp             /* the displaced addq: drop the caller's argument */
    CHECK   1f
    tst.b   gCheatPlay          /* opened by "Jogar com cheats": play now */
    beq.s   1f
    clr.l   -(%sp)
    jsr     0xFF4F32            /* osStartGame(0) */
    addq.l  #4, %sp
1:  jmp     (%a0)

/* Flash erase wait (was a busy loop at $ff5642 in ff5592, which runs from RAM: the flash is unreadable
 * meanwhile, so this must stay in RAM too). For the game loader's erase (return address $ff4d54) a
 * progress bar fills the two rows under "apagando..." (where the copy bar goes next), timed at
 * ~7.4 ms per KB (measured on the cart: 512 KB 3.8 s, 2 MB 15.2 s). VInt is off: frames are counted
 * on the VDP VBlank flag. */
    .globl  ramEraseWait
ramEraseWait:
    cmpi.l  #0xFF4D54, 16(%sp)  /* ff5592's return address (after its 12-byte movem + ours) */
    beq.s   2f
1:  move.w  (0xA13002).l, %d0
    btst    #1, %d0
    beq.s   1b
    rts
2:  movem.l %d2-%d7, -(%sp)
    moveq   #0, %d4
    move.w  0x1A+24(%sp), %d4   /* ff5592's size argument (KB) */
    mulu.w  #7, %d4
    lsr.l   #4, %d4             /* expected frames (60 Hz) */
    bne.s   3f
    moveq   #1, %d4
3:  moveq   #0, %d2             /* frames so far */
    moveq   #0, %d5             /* last VBlank flag */
    moveq   #0, %d6             /* filled cells */
    moveq   #0, %d3
    move.b  (0xFFE306).l, %d3   /* status row under "apagando..." */
    bsr.s   .Lbar
.Lpoll:
    move.w  (0xA13002).l, %d0
    btst    #1, %d0
    bne.s   .Lend
    move.w  (0xC00004).l, %d0
    andi.w  #8, %d0             /* VBlank */
    cmp.w   %d5, %d0
    beq.s   .Lpoll
    move.w  %d0, %d5
    beq.s   .Lpoll              /* count rising edges only */
    addq.l  #1, %d2
    move.l  %d2, %d0
    cmp.l   %d4, %d0
    bcs.s   4f
    moveq   #37, %d0            /* longer than expected: wait on the last cell */
    bra.s   5f
4:  mulu.w  #38, %d0
    divu.w  %d4, %d0
5:  cmp.w   %d6, %d0
    beq.s   .Lpoll
    move.w  %d0, %d6
    bsr.s   .Lbar
    bra.s   .Lpoll
.Lend:
    moveq   #38, %d6
    bsr.s   .Lbar
    movem.l (%sp)+, %d2-%d7
    rts
/* the bar like the copy one: plane B rows d3, d3+1, cols 1-38; d6 cells of tile 3, the rest tile 2 */
.Lbar:
    move.w  %d3, %d1
    moveq   #1, %d7
6:  move.w  %d1, %d0
    lsl.w   #7, %d0             /* row * 128 */
    addi.w  #0x2002, %d0        /* plane B 0xE000 (bits 13-0) + column 1 */
    swap    %d0
    move.w  #3, %d0             /* address bits 15-14 */
    ori.l   #0x40000000, %d0    /* VRAM write */
    move.l  %d0, (0xC00004).l
    move.w  %d6, %d0
    bra.s   8f
7:  move.w  #3, (0xC00000).l
8:  dbra    %d0, 7b
    moveq   #38, %d0
    sub.w   %d6, %d0
    bra.s   10f
9:  move.w  #2, (0xC00000).l
10: dbra    %d0, 9b
    addq.w  #1, %d1
    dbra    %d7, 6b
    rts

    .globl  ramBrowserBanner
ramBrowserBanner:               /* browser full redraw (was move.b #1,$ffe306 at $ff64a8) */
    move.b  #1, (0xFFE306).l
    CHECK   1f
    jmp     browserBanner
1:  rts

#ifdef DIAG
/* timing probes: entry of the status print, flash erase, flash write and checksum copy.
 * Fallbacks run the displaced stock instructions and continue in the stock routine. */
    .globl  ramDStatus
ramDStatus:
    CHECK   1f
    jmp     dStatus
1:  move.b  (0xFFE306).l, %d0
    jmp     0xFF7F80

    .globl  ramDErase
ramDErase:
    CHECK   1f
    jmp     dErase
1:  movem.l %d2-%d3/%a2, -(%sp)
    movea.l 0x10(%sp), %a2
    jmp     0xFF559A

    .globl  ramDWrite
ramDWrite:
    CHECK   1f
    jmp     dWrite
1:  movem.l %d2-%d4/%a2, -(%sp)
    move.l  0x18(%sp), %d2
    jmp     0xFF57D8

    .globl  ramDCheck
ramDCheck:
    CHECK   1f
    jmp     dCheck
1:  lea     -0x1c(%sp), %sp
    movem.l %d2-%d5/%a2-%a3, -(%sp)
    jmp     0xFF409C

/* ramFlashProbe(u16 *out): out[0..3] = autoselect IDs (words 0, 1, 0xE, 0xF),
 * out[4..51] = CFI words 0x10..0x3F. Runs from RAM: the flash array is unreadable meanwhile. */
    .globl  ramFlashProbe
ramFlashProbe:
    movea.l 4(%sp), %a1
    move.w  %sr, -(%sp)
    ori.w   #0x0700, %sr
    jsr     0xFF9288                /* VInt off */
    move.w  #0xAA, (0xAAA).w
    move.w  #0x55, (0x554).w
    move.w  #0x90, (0xAAA).w
    move.w  (0x0000).w, (%a1)+
    move.w  (0x0002).w, (%a1)+
    move.w  (0x001C).w, (%a1)+
    move.w  (0x001E).w, (%a1)+
    move.w  #0xF0, (0x0000).w       /* back to read array */
    move.w  #0x98, (0x00AA).w       /* CFI query */
    lea     (0x0020).w, %a0
    moveq   #47, %d0
2:  move.w  (%a0)+, (%a1)+
    dbra    %d0, 2b
    move.w  #0xF0, (0x0000).w
    move.w  #0xFF, (0x0000).w       /* Intel-style chips return to read array with 0xFF */
    move.w  #0xF0, (0x0000).w
    jsr     0xFF9292                /* VInt on */
    move.w  (%sp)+, %sr
    rts
#endif

/* osMenu key check (was "move.w $ffe30c,d0; andi.b #$d0,d0" at $ff5af4). While gMenuLR is set,
 * LEFT/RIGHT end the menu returning $81/$82 (after the button is released). RAM-only code. */
    .globl  ramMenuLR
ramMenuLR:
    move.w  (0xFFE30C).l, %d0
    tst.b   gMenuLR
    beq.s   1f
    btst    #2, %d0
    bne.s   2f
    btst    #3, %d0
    beq.s   1f
    move.b  #0x82, %d4
    bra.s   3f
2:  move.b  #0x81, %d4
3:  tst.w   (0xFFE30C).l
    bne.s   3b
    addq.l  #4, %sp
    jmp     0xFF5B3A                /* osMenu exit: returns d4 */
1:  andi.b  #0xD0, %d0
    rts

    .globl  ramToolbox
ramToolbox:                     /* toolbox; never return into a rewritten flash */
    jsr     0xFF7B68
    cmpi.l  #SIG_MAGIC, (SIG_ADDR).l
    bne.w   ramToolbox
    cmpi.l  #BUILD_ID, (SIG_ADDR + 4).l
    bne.w   ramToolbox
    rts


    .text

/* A on a browser entry. Directories keep the stock path; files open the PT-BR file menu
 * when the browser was opened from "Selecionar jogo" (gBrowseMode) in normal mode. */
aHook:
    tst.w   10(%a0)
    bne.s   .Ldir
    tst.b   gBrowseMode
    beq.s   .Lstock
    tst.b   0x2F(%sp)           /* browser flag local ($2b(a7) + our return address) */
    bne.s   .Lstock
    movem.l %d0-%d7/%a0-%a6, -(%sp)
    move.l  %d3, -(%sp)         /* cursor index */
    jsr     fileMenuFromBrowser
    addq.l  #4, %sp
    move.l  %d0, 12(%sp)        /* returned index becomes the browser cursor (saved d3) */
    movem.l (%sp)+, %d0-%d7/%a0-%a6
    addq.l  #4, %sp
    jmp     0xFF64B4            /* browser redraw loop (page cache was invalidated) */
.Lstock:
    addq.l  #4, %sp
    jmp     0xFF6716
.Ldir:
    rts

#ifdef DIAG
/* timing probe bodies (entered from the RAM stubs above): log the event, then run the stock code */
dStatus:                            /* ff7f7a(msg) */
    clr.l   -(%sp)
    move.l  8(%sp), -(%sp)
    pea     (1).w
    jsr     diagEvent
    lea     12(%sp), %sp
    move.b  (0xFFE306).l, %d0
    jmp     0xFF7F80

dErase:                             /* ff5592(addr, size, wait) */
    move.l  8(%sp), -(%sp)
    move.l  8(%sp), -(%sp)
    pea     (2).w
    jsr     diagEvent
    lea     12(%sp), %sp
    movem.l %d2-%d3/%a2, -(%sp)
    movea.l 0x10(%sp), %a2
    jmp     0xFF559A

dWrite:                             /* ff57d0(src, addr, sectors) */
    move.l  12(%sp), -(%sp)
    move.l  12(%sp), -(%sp)
    pea     (3).w
    jsr     diagEvent
    lea     12(%sp), %sp
    movem.l %d2-%d4/%a2, -(%sp)
    move.l  0x18(%sp), %d2
    jmp     0xFF57D8

dCheck:                             /* ff4094(x) */
    clr.l   -(%sp)
    clr.l   -(%sp)
    pea     (4).w
    jsr     diagEvent
    lea     12(%sp), %sp
    lea     -0x1c(%sp), %sp
    movem.l %d2-%d5/%a2-%a3, -(%sp)
    jmp     0xFF409C
#endif

/* Browser idle wait. d3 = cursor index, d5 = key repeat counter (cleared while idle, as stock). */
browseIdle:
    tst.w   (0xFFE30C).l
    bne.s   1f
    clr.w   %d5
    movem.l %d0-%d7/%a0-%a6, -(%sp)
    move.l  %d3, -(%sp)
    jsr     browserIdle
    addq.l  #4, %sp
    movem.l (%sp)+, %d0-%d7/%a0-%a6
1:  rts
