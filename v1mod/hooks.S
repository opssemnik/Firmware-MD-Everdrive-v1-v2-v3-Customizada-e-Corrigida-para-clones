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
    movem.l (%sp)+, %d0-%d7/%a0-%a6
    addq.l  #4, %sp
    jmp     0xFF64B4            /* browser redraw loop (page cache was invalidated) */
.Lstock:
    addq.l  #4, %sp
    jmp     0xFF6716
.Ldir:
    rts

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
