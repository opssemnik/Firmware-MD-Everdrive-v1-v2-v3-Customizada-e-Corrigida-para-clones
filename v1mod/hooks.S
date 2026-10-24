/*
 * Hook glue. The patched call sites of the RAM-resident OS (patch table, see extMain) jump to these
 * stubs, copied to RAM by myInit, which enter the C code in the flash extension. The extension block
 * is only ever rewritten by the loader at boot, so it is always there (also while "gravar OS" rewrites
 * the OS image).
 */

    .section .ramstub, "ax"

    .globl  ramMenuClear
ramMenuClear:                   /* osMenu screen clear (was jsr $ff7fb2) */
    jmp     myMenuClear

    .globl  ramSave
ramSave:                        /* settings save entry (stock prologue overwritten by jmp) */
    jmp     mySaveSettings

    .globl  ramAbout
ramAbout:                       /* toolbox "about" (was bsr.w $ff7342) */
    jmp     myAbout

    .globl  ramAHook
ramAHook:                       /* browser, A pressed: jsr from $ff6640, a0 = entry */
    jmp     aHook

    .globl  ramIdle
ramIdle:                        /* browser waiting for input (was a PAD polling loop at $ff660e) */
    jmp     browseIdle

    .globl  ramCheatApply
ramCheatApply:                  /* GG code list, START: apply (was bsr.w $ff3d1c; addq.l #4,sp at $ff3fec) */
    move.l  4(%sp), -(%sp)
    jsr     0xFF3D1C            /* stock: patch the codes into the loaded game */
    addq.l  #4, %sp
    movea.l (%sp)+, %a0
    addq.l  #4, %sp             /* the displaced addq: drop the caller's argument */
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

/* The browser's locals (sp right after its button checks): folder clusters per depth d7 at $ac(sp),
 * cursor per depth at $2c(sp) - what A on a folder saves before d7 goes up, and B reads back. */
    .globl  ramBrowserC
ramBrowserC:                    /* browser, after the UP/DOWN/RIGHT checks (was move.w $ffe30c,d0 at $ff693e) */
    move.w  (0xFFE30C).l, %d0
    btst    #5, %d0             /* C: search in every folder */
    beq.s   1f
    tst.b   gBrowseMode         /* "Selecionar jogo" only, not the SRAM tools browser */
    beq.s   1f
    movem.l %d1-%d7/%a0-%a6, -(%sp)
    jsr     browserSearch
    movem.l (%sp)+, %d1-%d7/%a0-%a6
    addq.l  #4, %sp             /* leave the button checks */
    tst.l   %d0                 /* 0: cancelled */
    beq.s   3f
    subq.l  #2, %d0
    bcs.s   2f                  /* 1: another list, same level */
    bne.s   4f                  /* 3: back up to the folder the search started in */
    cmpi.w  #62, %d7            /* 2: results, entered like a subfolder of the folder */
    bcc.s   2f
    move.w  %d7, %d0
    add.w   %d0, %d0
    lea     0x2C(%sp), %a0
    move.w  %d3, (%a0, %d0.w)   /* B comes back to the same cursor */
    add.w   %d0, %d0
    lea     0xAC(%sp), %a0
    movea.l (0xFFCC7C).l, %a1
    move.l  2(%a1), (%a0, %d0.w)
    addq.w  #1, %d7
2:  moveq   #0, %d3             /* new list: cursor on its first entry */
3:  jmp     0xFF64B4            /* redraw the page (not $ff6478: it would forget the folder depth) */
4:  tst.w   %d7
    beq.s   2b
    subq.w  #1, %d7
    move.w  %d7, %d0
    add.w   %d0, %d0
    lea     0x2C(%sp), %a0
    move.w  (%a0, %d0.w), %d3   /* the cursor it had */
    bra.s   3b
1:  move.w  (0xFFE30C).l, %d0
    rts

    .globl  ramPagePal
ramPagePal:                     /* browser, before the page counter (was lea $ff8ed0,a3 at $ff64f4): every */
    lea     0xFF8ED0, %a3       /* page redraw passes here; d4 = palette 2 (gold) is pushed as the colour */
    movem.l %d0-%d1/%a0-%a1, -(%sp)     /* of the three "pág: x / y" prints; the search tag goes next to it */
    jsr     drawFilterTag
    movem.l (%sp)+, %d0-%d1/%a0-%a1
    move.l  #0x4000, %d4
    rts

    .globl  ramBrowserBanner
ramBrowserBanner:               /* browser full redraw (was move.b #1,$ffe306 at $ff64a8) */
    move.b  #1, (0xFFE306).l
    jmp     browserBanner

#ifdef DIAG
/* timing probes: entry of the status print, flash erase, flash write and checksum copy */
    .globl  ramDStatus
ramDStatus:
    jmp     dStatus

    .globl  ramDErase
ramDErase:
    jmp     dErase

    .globl  ramDWrite
ramDWrite:
    jmp     dWrite

    .globl  ramDCheck
ramDCheck:
    jmp     dCheck

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


/* the table of patches to the RAM-resident OS (see extMain), filled in by the build */
    .section .patch, "a"
    .globl  patchTab
    .balign 4
patchTab:
    .space  0x1000                  /* PATCH_MAX */

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
