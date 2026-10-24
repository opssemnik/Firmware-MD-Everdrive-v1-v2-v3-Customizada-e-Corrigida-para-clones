/*
 * EverDrive-MD v1 OS v38 - interface to the stock OS (code runs from RAM at 0xFF0000).
 * All addresses were taken from the OS-V38.BIN disassembly; the OS is GCC-compiled with
 * the standard m68k ABI (args pushed as longs, result in d0, d0-d1/a0-a1 clobbered).
 */
#ifndef OS_H
#define OS_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;

/* FAT file record built by the browser (0x110 bytes) */
typedef struct {
    u32 cluster;        /* +0x00 first cluster */
    u32 size;           /* +0x04 file size in bytes */
    u32 dirsec;         /* +0x08 LBA of the directory sector holding the entry */
    u16 idx;            /* +0x0C entry index inside that sector */
    char name[256];     /* +0x0E long file name */
    u16 isdir;          /* +0x10E */
} Rec;

/* Directory entry as stored in the browser's directory table (12 bytes) */
typedef struct {
    u32 dirsec;
    char key[4];        /* first 4 characters of the name, lower case (the browser sorts by it) */
    u16 idx;
    u16 isdir;
} DirEnt;

#define PLANE_A 0xC000
#define PLANE_B 0xE000
#define PAL0 0x0000
#define PAL1 0x2000
#define PAL2 0x4000
#define PAL3 0x6000
#define ALIGN_CENTER 2

/* ---- video / text ---- */
#define osClear      ((void (*)(void))0xFF7FB2)
#define osFill       ((void (*)(u32 plane, u32 tile, u32 x, u32 y, u32 w, u32 h))0xFF8ED0)
#define osFillSeq    ((void (*)(u32 plane, u32 tile, u32 x, u32 y, u32 w, u32 h))0xFF8F66)
#define osPrint      ((void (*)(u32 plane, const char *s, u32 attr, u32 x, u32 y))0xFF90A4)
#define osPrintN     ((void (*)(u32 plane, const char *s, u32 attr, u32 x, u32 y, u32 max))0xFF9152)
#define osPrintAl    ((void (*)(u32 plane, const char *s, u32 attr, u32 x, u32 y, u32 align))0xFF920E)
#define osPrintNum   ((void (*)(const char *s, u32 num, u32 attr, u32 x, u32 y))0xFF7CA4)
#define osLoadTiles  ((void (*)(const void *src, u32 tile, u32 count, u32 dma))0xFF8DAA)
#define osSetPal     ((void (*)(u32 pal, const void *src))0xFF8A3C)
#define osSetColor   ((void (*)(u32 pal, u32 idx, u32 color))0xFF89FC)

/* ---- UI ---- */
#define osMenu       ((u8 (*)(const char *const *items, u32 count, u32 spacing, u32 sel, u32 main))0xFF5908)
#define osError      ((void (*)(const char *msg, u32 code))0xFF7F1A)
#define osStatus     ((void (*)(const char *msg))0xFF7F7A)
#define osBrowser    ((u8 (*)(Rec **out, u32 flag))0xFF6322)
#define osOptions    ((void (*)(void))0xFF5CE6)
#define osCheats     ((void (*)(void))0xFF3FF8)
#define osReadSettings ((void (*)(void))0xFF5B9E)
#define osToolbox    ((void (*)(void))0xFF7B68)
#define osMainMenu   ((void (*)(void))0xFF528E)     /* stock, run by the loader without an extension */
#define osReadPad    ((u32 (*)(u32 port))0xFF843C)   /* reads the pad itself: BTN_* bits */

/* ---- game ---- */
#define osLoadGame   ((u8 (*)(Rec *r))0xFF4C06)
#define osStartGame  ((void (*)(u32 now))0xFF4F32)

/* ---- FAT ---- */
#define osFatPtrInit ((void (*)(void))0xFF1C58)
#define osFatInit    ((u8 (*)(void))0xFF1F98)
#define osOpenDir    ((u8 (*)(u32 cluster))0xFF259C)
#define osMakeRec    ((u8 (*)(DirEnt *e, Rec *r))0xFF3188)
#define osFind       ((u8 (*)(const char *path, Rec *r, u32 dirs))0xFF324E)
#define osOpen       ((u8 (*)(Rec *r, u32 wrsize))0xFF2F20)
#define osRead       ((u8 (*)(void *dst, u32 sectors))0xFF2C1C)
#define osLoadSector ((u8 (*)(u32 lba))0xFF1F5E)

/* ---- flash ---- */
#define osFlashErase ((void (*)(u32 addr, u32 size, u32 wait))0xFF5592)
#define osFlashWrite ((void (*)(const void *src, u32 addr, u32 sectors))0xFF57D0)

/* ---- OS variables ---- */
#define PAD        (*(volatile u16 *)0xFFE30C)
#define VBCOUNT    (*(volatile u32 *)0xFFE308)
#define FAT_READY  (*(volatile u16 *)0xFFE304)
#define PAGE_CACHE (*(volatile u16 *)0xFFE302)
#define DIRHDR     (*(u8 **)0xFFCC7C)
#define SECBUF     (*(u8 **)0xFFCC74)
#define SETTINGS   ((u8 *)0xFFCC8A)
#define RECCACHE   ((u8 *)0xFFCCB2)     /* browser page cache, 21 * 0x110 bytes */
#define HVCOUNT    (*(volatile u16 *)0xC00008)

#define DIR_COUNT()   (*(u16 *)DIRHDR)
#define DIR_CLUSTER() (*(u32 *)(DIRHDR + 2))
#define DIR_ENT(i)    (((DirEnt **)(DIRHDR + 0x1812))[i])

/* menu centring column inside osMenu (immediate operands of two "pea $14.w") */
#define MENU_CENTER_A (*(u16 *)0xFF5A62)
#define MENU_CENTER_B (*(u16 *)0xFF5A82)

/* scratch: the browser page cache, free whenever it is reloaded afterwards */
#define SCRATCH RECCACHE
#define SCRATCH_SIZE (21 * 0x110)

/* flash extension (/EDMD/V1EXT.BIN -> cart 0x40000): header shared by the loader and the extension */
typedef struct {
    u32 magic;          /* EXT_MAGIC */
    u32 abi;            /* EXT_ABI: what the loader expects of the extension */
    u32 id;             /* build id of the extension */
    u32 size;           /* bytes (set by the build) */
    u32 (*main)(void);  /* patches the OS and runs the main menu; returns only on failure */
} ExtHdr;
#define EXT_ADDR 0x40000
#define EXT_HDR ((const ExtHdr *)EXT_ADDR)
#define EXT_MAGIC 0x50544258            /* 'PTBX' */
#define EXT_ABI 1
#define PATCH_MAX 0x1000

#define BTN_UP 0x01
#define BTN_DOWN 0x02
#define BTN_LEFT 0x04
#define BTN_RIGHT 0x08
#define BTN_B 0x10
#define BTN_C 0x20
#define BTN_A 0x40
#define BTN_START 0x80

#endif
