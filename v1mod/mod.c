/*
 * EverDrive-MD v1 (OS v38) PT-BR mod - new features.
 * Runs from the OS flash image (cart 0x1Cxxx-0x1Fxxx); only ever entered while the
 * OS flash is in read mode. Stock RAM routines do all flash erase/program work.
 */
#include "os.h"
#include "gen.h"

/* ---- persistent lists: stored in the settings flash block (0x30000, erased as a whole) ---- */
#define FLASH_BLOCK 0x30000
#define FLASH_SECTORS 6                 /* 0x30000..0x30BFF */
#define LIST_MAGIC 0x52474C31           /* 'RGL1' */
#define LIST_MAX 8
#define HDR_OFF 0x200
#define REC_OFF 0x210
#define FAV_OFF 0x610

typedef struct {
    u32 magic;
    u16 theme;
    u16 count[2];                       /* [0] recent, [1] favourites */
    u16 pad[3];
} ListHdr;

typedef struct {
    u32 cluster;
    u32 size;
    u32 dirsec;
    u16 idx;
    char name[114];
} ListEnt;                              /* 128 bytes */

#define FLASH_HDR ((const ListHdr *)(FLASH_BLOCK + HDR_OFF))
#define SCR_HDR ((ListHdr *)(SCRATCH + HDR_OFF))
#define LIST_AT(base, l) ((ListEnt *)((u8 *)(base) + ((l) ? FAV_OFF : REC_OFF)))

/* ---- RAM state (.bss in free RAM above the OS variables) ---- */
static Rec gCur;
static Rec gTmp;
static void (*gOverlay)(void);
static const char *gTitle;
static u8 gMainSel;
static u8 gTheme;
static u8 gArtOk;
static u8 gHdrOk;
static u8 gDirLoaded;
u8 gBrowseMode;                         /* read by the browser A-button hook */
u8 gMenuLR;                             /* osMenu returns $81/$82 on LEFT/RIGHT (ramMenuLR) */
u8 gCheatPlay;                          /* "Jogar com cheats": start the game right after applying */
static u32 gRand;
static char gArtName[24];
static char gArtPath[40];
static char gThemeItem[24];
static char gItemBuf[LIST_MAX][38];
static const char *gItems[LIST_MAX + 2];
static u8 gSector0[512] __attribute__((aligned(4)));   /* SD/OS routines access it by words */
static u8 gArtBuf[512] __attribute__((aligned(4)));
static u32 gArtHash;
static u8 gArtCache;                    /* 0 none, 1 = art of gArtHash is in VRAM, 2 = it has no art */
/* code that does not fit in ROMA goes with the strings in the blank POA logo rows (ROMB) */
#define ROMB_CODE __attribute__((section(".strb.text")))
#define ROMC_CODE __attribute__((section(".strc.text")))

static u8 gBanner;                      /* 0 not tried yet, 1 no image, 2 /EDMD/BANNER.ART loaded */
static u16 gBannerPal[14];
#define BANNER_IMG_TILE 0x170           /* VRAM 0x2E00: the 36x3 image banner (same place as on the v3) */
#define WALL_TILE 0x1DC                 /* VRAM 0x3B80..0x9FFF: up to 800 wallpaper tiles (as on the v3) */
#define WALL_MAP 0x0100                 /* VRAM copy of the wallpaper's 40x28 plane B names (2240 bytes) */
#define WALL_MAX 800
static u8 gWall;                        /* 1 = /EDMD/WALL.ART loaded */
#define VDP_DATA (*(volatile u16 *)0xC00000)
#define VDP_CTRL (*(volatile u32 *)0xC00004)
#define PREV_TOP 10                      /* cover box: rows 10..18 (middle of the list), cols 27..38 */

#define PREVIEW_DELAY 19                /* frames resting on a ROM before its cover loads (~0.32 s) */

extern void ramToolbox(void);           /* RAM trampoline (hooks.S) */
extern const u8 ramStubStart[], ramStubEnd[];
extern u8 ramStubRam[];
extern u8 bssStart[], bssEnd[];

/* ---------------------------------------------------------------- helpers */

void *memcpy(void *d, const void *s, unsigned long n)
{
    u8 *dd = d;
    const u8 *ss = s;
    while (n--)
        *dd++ = *ss++;
    return d;
}

void *memset(void *d, int v, unsigned long n)
{
    u8 *dd = d;
    while (n--)
        *dd++ = (u8)v;
    return d;
}

static int slen(const char *s)
{
    int n = 0;
    while (s[n])
        n++;
    return n;
}

static char *scpy(char *d, const char *s)
{
    while ((*d = *s++))
        d++;
    return d;
}

static u8 lower(u8 c)
{
    return (c >= 'A' && c <= 'Z') ? c + 32 : c;
}

static void waitKey(void)
{
    while (PAD)
        ;
    while (!PAD)
        ;
    while (PAD)
        ;
}

static u16 rnd(void)
{
    gRand = gRand * 1103515245UL + 12345UL + HVCOUNT + VBCOUNT;
    return (u16)(gRand >> 16);
}

static u16 umod(u16 a, u16 b)
{
    return b ? (u16)((unsigned long)a % b) : 0;
}

static void center(const char *s, u32 attr, u32 y)
{
    osPrintAl(PLANE_A, s, attr, 20, y, ALIGN_CENTER);
}

/* copy name without extension, truncated to max chars (adds ".." when cut) */
static void shortName(char *d, const char *name, int max)
{
    int n = slen(name), i;
    for (i = n - 1; i > 0; i--)
        if (name[i] == '.') {
            n = i;
            break;
        }
    if (n > max) {
        memcpy(d, name, max - 2);
        d[max - 2] = '.';
        d[max - 1] = '.';
        d[max] = 0;
    } else {
        memcpy(d, name, n);
        d[n] = 0;
    }
}

static void hex(char *d, u32 v, int digits)
{
    while (digits--) {
        u8 c = (v >> (digits * 4)) & 15;
        *d++ = c < 10 ? '0' + c : 'A' + c - 10;
    }
    *d = 0;
}

/* ---------------------------------------------------------------- theme / screen */

static const u16 themes[4][6] = {
    /*  bg     bar1   bar2   text   dim    accent */
    {0x000, 0xAAA, 0x444, 0xFFF, 0x444, 0x2AA},     /* PADRAO */
    {0x002, 0x00A, 0x006, 0x0EE, 0x048, 0x0AE},     /* RG POA */
    {0x200, 0xA40, 0x620, 0xEEE, 0xA86, 0x0CE},     /* SEGA 16 */
    {0x202, 0xA0A, 0x606, 0xEE0, 0xA4A, 0xE4E},     /* OUTRUN */
};

static void applyTheme(void)
{
    const u16 *c = themes[gTheme & 3];
    osSetColor(0, 0, c[0]);
    osSetColor(0, 1, c[1]);
    osSetColor(0, 2, c[2]);
    osSetColor(0, 15, c[3]);
    osSetColor(1, 15, c[4]);
    osSetColor(2, 15, c[5]);
    osSetColor(2, 1, 0x008);            /* banner bar: crimson */
    osSetColor(2, 2, 0x0CE);            /* banner letters: gold */
    osSetColor(2, 3, 0x002);            /* banner letter shadow */
    if (gBanner == 2) {                 /* image banner: palette 2 colours 1..14 */
        int i;
        for (i = 0; i < 14; i++)
            osSetColor(2, i + 1, gBannerPal[i]);
    }
}

static int readArtFile(u16 tile, u16 *pal, int abortable);

/* /EDMD/BANNER.ART: same layout as a box-art file, 36x3 tiles (288x24 px) */
ROMB_CODE static void loadBanner(void)
{
    if (osFind(S_banner_path, &gTmp, 0) || gTmp.isdir || osOpen(&gTmp, 0)
        || !readArtFile(BANNER_IMG_TILE, gBannerPal, 0))
        return;
    gBanner = 2;
    applyTheme();
}

/* /EDMD/WALL.ART (make_wallpaper.py): word 0 = tile count, palette 1 colours 1..14, the 40x28
 * plane B names (palette and tile numbers already in place) -> VRAM WALL_MAP, then the tiles.
 * After the 32-byte header everything is 32-byte blocks, so it streams with osLoadTiles. */
ROMB_CODE static void loadWallpaper(void)
{
    u32 b = 0, n = 0;
    int s, i;

    if (osFind(S_wall_path, &gTmp, 0) || gTmp.isdir || osOpen(&gTmp, 0))
        return;
    for (s = 0;; s++) {
        if (osRead(gArtBuf, 1))
            return;
        if (!s) {
            n = ((u16 *)gArtBuf)[0];
            if (n > WALL_MAX)
                return;
            for (i = 1; i < 15; i++)
                osSetColor(1, i, ((u16 *)gArtBuf)[i]);
        }
        for (i = s ? 0 : 1; i < 16; i++, b++) {
            if (b >= 70 + n) {
                gWall = 1;
                return;
            }
            osLoadTiles(gArtBuf + i * 32, b < 70 ? WALL_MAP / 32 + b : WALL_TILE + b - 70, 1, 0);
        }
    }
}

/* first banner/wallpaper use: mount the card (once) and load both images */
ROMB_CODE __attribute__((noinline)) static void loadImagesOnce(void)
{
    gBanner = 1;
    if (!FAT_READY) {
        if (osFatInit())
            return;
        FAT_READY = 1;
    }
    loadBanner();
    loadWallpaper();
}

static void loadImages(void)
{
    u32 keep = DIR_CLUSTER();
    loadImagesOnce();
    DIR_CLUSTER() = keep;
}

/* the wallpaper on plane B: its names are copied from the VRAM copy, row by row */
ROMB_CODE static void drawWallpaper(void)
{
    u16 row[40], sr;
    int y, x;

    if (!gBanner)
        loadImages();
    if (!gWall)
        return;
    asm volatile("move.w %%sr, %0\n\tmove.w #0x2700, %%sr" : "=d"(sr));     /* no VInt meanwhile */
    for (y = 0; y < 28; y++) {
        u32 src = WALL_MAP + y * 80, dst = PLANE_B + y * 128;
        VDP_CTRL = ((src & 0x3FFF) << 16) | (src >> 14);                 /* VRAM read */
        for (x = 0; x < 40; x++)
            row[x] = VDP_DATA;
        VDP_CTRL = 0x40000000 | ((dst & 0x3FFF) << 16) | (dst >> 14);    /* VRAM write */
        for (x = 0; x < 40; x++)
            VDP_DATA = row[x];
    }
    asm volatile("move.w %0, %%sr" : : "d"(sr));
}

/* RETROGAMER POA on top: the image banner (rows 0-2) or the built-in one (row 1) */
ROMB_CODE static void drawBanner(u32 plane)
{
    if (!gBanner)
        loadImages();
    if (gBanner == 2)
        osFillSeq(plane, PAL2 | BANNER_IMG_TILE, 2, 0, 36, 3);
    else
        osPrintAl(plane, S_banner, PAL2, 20, 1, ALIGN_CENTER);
}

/* browser full redraw (ramBrowserBanner): its list starts on row 4 (a blank row under the banner). Plane B,
 * because entering a folder clears rows 0-24 of plane A only. */
static char gFilter;                    /* browser letter filter: 'A'..'Z', '#' (others), 0 = none */
static u16 gFilterCount;                /* the filtered folder, to notice when the browser reloads it */
static u32 gFilterCluster;

/* "[M]" next to the page counter while a filter is on (blank otherwise) and the button help on row 3;
 * ramPagePal calls it before every page counter print (folder changes clear rows 0-24 of plane A) */
ROMB_CODE void drawFilterTag(void)
{
    char t[4] = {' ', ' ', ' ', 0};
    if (gFilter && (DIR_CLUSTER() != gFilterCluster || DIR_COUNT() != gFilterCount))
        gFilter = 0;                    /* another folder, or this one read again: unfiltered */
    if (gFilter) {
        t[0] = '[';
        t[1] = gFilter;
        t[2] = ']';
    }
    osPrint(PLANE_A, t, PAL2, 18, 26);
    if (gBrowseMode)                    /* the help line under the banner ("Selecionar jogo" only) */
        osPrintAl(PLANE_A, S_help, PAL2, 20, 3, ALIGN_CENTER);
}

void browserBanner(void)
{
    drawWallpaper();
    drawBanner(PLANE_B);
}

static void overlayTitle(void);
static u32 filterApply(char letter);
static u8 menu(const char *const *items, u32 n, u32 sel);
static void info(const char *msg);
static u32 extSearch(void);

/* browser, C (ramBrowserC): pick a letter; only the files starting with it stay in the list (folders
 * always do). The browser's directory table is reordered in place and its count shortened; another
 * letter or "Todos" reads the folder again first. Returns 1 when the list changed (the cursor goes to
 * the top), 0 when cancelled; the browser redraws the page either way. */
ROMC_CODE u32 browserFilter(void)
{
    static const char *const groups[] = {S_flt_af, S_flt_gl, S_flt_mr, S_flt_sz, S_flt_num, S_flt_all, S_flt_search};
    static char letters[8][2];
    const char *items[8];
    char letter = 0;
    u32 changed = 0;
    u8 r;
    int n, i;

    gTitle = S_flt_title;
    gOverlay = overlayTitle;
    r = menu(groups, 7, 0);
    if (r < 4) {
        n = r == 3 ? 8 : 6;
        for (i = 0; i < n; i++) {
            letters[i][0] = 'A' + r * 6 + i;
            items[i] = letters[i];
        }
        letter = 'A' + r * 6;
        r = menu(items, n, 0);
        letter += r;
    } else if (r == 4) {
        letter = '#';
    }
    gOverlay = 0;
    if (r == 6)                         /* every folder: the search lives in the flash extension */
        changed = extSearch();
    else if (!(r & 0x40))               /* B: back to the list as it was */
        changed = filterApply(letter);
    osClear();                          /* the browser then redraws only the list and the footer */
    drawWallpaper();
    drawBanner(PLANE_B);
    PAGE_CACHE = 0xFFFF;
    return changed;
}

/* the whole folder again, then (unless "Todos") only the files starting with letter */
__attribute__((noinline)) static u32 filterApply(char letter)
{
    int n, i, j;

    if (osOpenDir(DIR_CLUSTER()))
        return 1;
    gFilter = letter;
    if (!letter)
        return 1;
    n = DIR_COUNT();
    for (i = j = 0; i < n; i++) {       /* the table keeps the first letters of each name: no SD reads */
        DirEnt *e = DIR_ENT(i);
        char c = e->key[0];
        if (c >= 'a' && c <= 'z')
            c -= 32;
        if (e->isdir || (letter == '#' ? c < 'A' || c > 'Z' : c == letter))
            DIR_ENT(j++) = e;
    }
    if (!j) {                           /* nothing with that letter: say so, keep the whole folder */
        gFilter = 0;
        osOpenDir(DIR_CLUSTER());
        info(S_flt_none);
        return 1;
    }
    *(u16 *)DIRHDR = j;
    gFilterCount = j;
    gFilterCluster = DIR_CLUSTER();
    return 1;
}

/* called by osMenu instead of its screen clear (through the RAM guard) */
void myMenuClear(void)
{
    osClear();
    drawWallpaper();
    drawBanner(PLANE_A);
    if (gOverlay)
        gOverlay();
}

static void clearWithBanner(void)
{
    void (*o)(void) = gOverlay;
    gOverlay = 0;
    myMenuClear();
    gOverlay = o;
}

static u8 gHiRow;                       /* row of a highlighted menu item (0 = none) */

static void overlayTitle(void)
{
    center(gTitle, PAL2, 3);
    if (gHiRow)                         /* bar in palette 2 colour 1, the banner crimson */
        osFill(PLANE_B, PAL2 | 1, 0, gHiRow, 40, 1);
}

static u8 menu(const char *const *items, u32 n, u32 sel)
{
    return osMenu(items, n, 2, sel, 0);
}

static void info(const char *msg)
{
    menu(&msg, 1, 0);
}

static void uploadExtraTiles(void)
{
    u8 buf[32] __attribute__((aligned(4)));
    int t, r, i;

    for (t = 0; t < NGLYPH; t++) {
        for (r = 0; r < 8; r++) {
            u8 b = glyph1bpp[t * 8 + r];
            for (i = 0; i < 4; i++) {
                u8 v = 0;
                if (b & (0x80 >> (i * 2)))
                    v |= 0xF0;
                if (b & (0x40 >> (i * 2)))
                    v |= 0x0F;
                buf[r * 4 + i] = v;
            }
        }
        osLoadTiles(buf, GLYPH_TILE + t, 1, 0);
    }
    for (t = 0; t < NBANNER; t++) {
        for (r = 0; r < 8; r++)
            for (i = 0; i < 4; i++) {
                u8 b = banner2bpp[t * 16 + r * 2 + (i >> 1)];
                u8 sh = (i & 1) ? 0 : 4;
                buf[r * 4 + i] = (((b >> (sh + 2)) & 3) << 4) | ((b >> sh) & 3);
            }
        osLoadTiles(buf, BANNER_TILE + t, 1, 0);
    }
}

/* ---------------------------------------------------------------- flash lists */

static int flashValid(void)
{
    return FLASH_HDR->magic == LIST_MAGIC;
}

static void scratchLoad(void)
{
    memcpy(SCRATCH, (const void *)FLASH_BLOCK, FLASH_SECTORS * 512);
    memcpy(SCRATCH, SETTINGS, 8);
    if (SCR_HDR->magic != LIST_MAGIC) {
        memset(SCRATCH + HDR_OFF, 0, FLASH_SECTORS * 512 - HDR_OFF);
        SCR_HDR->magic = LIST_MAGIC;
    }
    SCR_HDR->theme = gTheme;
}

static void scratchCommit(void)
{
    osFlashErase(FLASH_BLOCK, 0x80, 1);
    osFlashWrite(SCRATCH, FLASH_BLOCK, FLASH_SECTORS);
    PAGE_CACHE = 0xFFFF;
}

/* replacement for the stock settings save (keeps the lists alive) */
void mySaveSettings(void)
{
    scratchLoad();
    scratchCommit();
    osReadSettings();
}

static int sameEnt(const ListEnt *e, const Rec *r)
{
    return e->cluster == r->cluster && e->size == r->size && e->dirsec == r->dirsec && e->idx == r->idx;
}

/* insert r at the top of list l; returns 0 when nothing had to change */
static int listAdd(int l, const Rec *r)
{
    ListEnt *list;
    int n, i, found = -1;

    if (flashValid()) {
        const ListEnt *fl = LIST_AT(FLASH_BLOCK, l);
        if (FLASH_HDR->count[l] && sameEnt(&fl[0], r))
            return 0;
    }
    scratchLoad();
    list = LIST_AT(SCRATCH, l);
    n = SCR_HDR->count[l];
    if (n > LIST_MAX)
        n = LIST_MAX;
    for (i = 0; i < n; i++)
        if (sameEnt(&list[i], r))
            found = i;
    if (found < 0) {
        found = n < LIST_MAX ? n : LIST_MAX - 1;
        if (n < LIST_MAX)
            n++;
    }
    for (i = found; i > 0; i--)
        memcpy(&list[i], &list[i - 1], sizeof(ListEnt));
    memcpy(&list[0], r, 14);
    memcpy(list[0].name, r->name, sizeof(list[0].name) - 1);
    list[0].name[sizeof(list[0].name) - 1] = 0;
    SCR_HDR->count[l] = n;
    scratchCommit();
    return 1;
}

ROMB_CODE static void listClear(int l)
{
    scratchLoad();
    SCR_HDR->count[l] = 0;
    scratchCommit();
}

ROMB_CODE static void listRemove(int l, int idx)
{
    ListEnt *list;
    int n, i;

    scratchLoad();
    list = LIST_AT(SCRATCH, l);
    n = SCR_HDR->count[l];
    if (idx >= n)
        return;
    for (i = idx; i < n - 1; i++)
        memcpy(&list[i], &list[i + 1], sizeof(ListEnt));
    SCR_HDR->count[l] = n - 1;
    scratchCommit();
}

/* ---------------------------------------------------------------- FAT / launch */

static int fatEnsure(void)
{
    u8 e;
    if (FAT_READY)
        return 1;
    e = osFatInit();
    if (e) {
        osError(S_fat_error, e);
        return 0;
    }
    FAT_READY = 1;
    return 1;
}

/* the stored entry still describes the same file on the card? */
static int entryValid(const ListEnt *le)
{
    u8 *d;
    u32 off = ((u32)le->idx << 5);
    if (off >= 512 || osLoadSector(le->dirsec))
        return 0;
    d = SECBUF + off;
    if (d[0] == 0 || d[0] == 0xE5)
        return 0;
    return le->cluster == ((u32)d[0x15] << 24 | (u32)d[0x14] << 16 | (u32)d[0x1b] << 8 | d[0x1a]) &&
           le->size == ((u32)d[0x1f] << 24 | (u32)d[0x1e] << 16 | (u32)d[0x1d] << 8 | d[0x1c]);
}


#ifdef DIAG
#define gFlashMode() (*(volatile u8 *)0xFFCC89)
/* ======================= diagnostics build: load timings + flash chip info ======================
 * The vblank counter stops while the OS programs the flash (VInt is disabled), so the Z80 is used
 * as an independent stopwatch: a 56 T-state loop incrementing a 32-bit counter in its RAM. */
#define DSEC __attribute__((section(".diag"), noinline))
#define DSRO __attribute__((section(".diagro")))
#define Z80_BUSREQ (*(volatile u16 *)0xA11100)
#define Z80_RESET (*(volatile u16 *)0xA11200)
#define Z80_RAM ((volatile u8 *)0xA00000)
#define DMAX 19

enum { EV_STATUS = 1, EV_ERASE, EV_WRITE, EV_CHECK, EV_START, EV_LOADED, EV_LIST };

typedef struct {
    u32 t, a, b;
    u16 type, n;
} DiagEv;

static DiagEv gEv[DMAX];
static u8 gNev, gRec;
static u16 gFlash[52] __attribute__((aligned(4)));
static char gLastName[40];
static u32 gLastSize;

extern void ramFlashProbe(u16 *out);

static const u8 z80timer[] DSRO = {
    0xF3, 0x31, 0x00, 0x20,             /* di ; ld sp,0x2000 */
    0x21, 0x00, 0x00, 0x22, 0x00, 0x1F, 0x22, 0x02, 0x1F,   /* counter = 0 */
    0x2A, 0x00, 0x1F, 0x23, 0x22, 0x00, 0x1F,               /* loop: ld hl,(lo) ; inc hl ; ld (lo),hl */
    0x7C, 0xB5, 0xC2, 0x0D, 0x00,                           /* ld a,h ; or l ; jp nz,loop (56 T) */
    0x2A, 0x02, 0x1F, 0x23, 0x22, 0x02, 0x1F, 0xC3, 0x0D, 0x00,  /* hi++ ; jp loop */
};

static const char DS_menu[] DSRO = "Diagnostico";
static const char DS_title[] DSRO = "Diagnostico (versao de teste)";
static const char DS_times[] DSRO = "Tempos do ultimo carregamento";
static const char DS_none[] DSRO = "Nenhum jogo carregado ainda";
static const char DS_start[] DSRO = "inicio";
static const char DS_loaded[] DSRO = "fim do carregamento";
static const char DS_list[] DSRO = "lista de recentes";
static const char DS_erase[] DSRO = "apagar";
static const char DS_write[] DSRO = "gravar";
static const char DS_check[] DSRO = "rotina ff4094";
static const char DS_total[] DSRO = "TOTAL (ms): ";
static const char DS_ms[] DSRO = "ms";
static const char DS_kbs[] DSRO = "copia (KB/s): ";
static const char DS_kb[] DSRO = "KB: ";
static const char DS_x[] DSRO = "x";
static const char DS_empty[] DSRO = "";
static const char DS_play[] DSRO = "Pressione um botao para continuar";
static const char DS_keys[] DSRO = "A: tempos   B: voltar";
static const char DS_manuf[] DSRO = "Fabricante: ";
static const char DS_dev[] DSRO = "Dispositivo: ";
static const char DS_size[] DSRO = "Tamanho (KB): ";
static const char DS_buf[] DSRO = "Buffer de escrita (bytes): ";
static const char DS_tword[] DSRO = "Gravar palavra tip. (us): ";
static const char DS_tbuf[] DSRO = "Gravar buffer tip. (us): ";
static const char DS_terase[] DSRO = "Apagar bloco tip. (ms): ";
static const char DS_regions[] DSRO = "Regioes de bloco: ";
static const char DS_region[] DSRO = "  blocos de (KB): ";
static const char DS_nocfi[] DSRO = "CFI: sem resposta do chip";
static const char DS_mode[] DSRO = "Gravacao do OS: ";
static const char DS_mode1[] DSRO = "duplo (0x50)";
static const char DS_mode2[] DSRO = "palavra (0xA0)";
static const char DS_ntsc[] DSRO = "Regiao: NTSC 60Hz";
static const char DS_pal[] DSRO = "Regiao: PAL 50Hz";
static const char DS_raw[] DSRO = "CFI bruto 10-3F:";
static const char DS_names[] DSRO = "\x01" "AMD/Spansion\0" "\x04" "Fujitsu\0" "\x1F" "Atmel\0" "\x20" "ST/Micron\0"
                                    "\x37" "AMIC\0" "\x89" "Intel\0" "\xBF" "SST\0" "\xC2" "Macronix\0"
                                    "\xC8" "GigaDevice\0" "\xDA" "Winbond\0" "\xEC" "Samsung\0" "\x1C" "EON\0";

DSEC static void z80Wait(void)
{
    Z80_BUSREQ = 0x100;
    while (Z80_BUSREQ & 0x100)
        ;
}

DSEC static void z80Start(void)
{
    volatile int d;
    unsigned i;
    Z80_BUSREQ = 0x100;
    Z80_RESET = 0x100;
    while (Z80_BUSREQ & 0x100)
        ;
    for (i = 0; i < sizeof(z80timer); i++)
        Z80_RAM[i] = z80timer[i];
    Z80_RESET = 0;
    Z80_BUSREQ = 0;
    for (d = 0; d < 32; d++)
        ;
    Z80_RESET = 0x100;
}

DSEC static void z80Stop(void)
{
    z80Wait();
    Z80_RESET = 0;                      /* back to reset, as at power-on */
    Z80_BUSREQ = 0;
}

DSEC static u32 z80Now(void)
{
    u32 v;
    z80Wait();
    v = Z80_RAM[0x1F00] | (u32)Z80_RAM[0x1F01] << 8 | (u32)Z80_RAM[0x1F02] << 16 | (u32)Z80_RAM[0x1F03] << 24;
    Z80_BUSREQ = 0;
    return v;
}

DSEC static u32 toMs(u32 c)
{
    u32 r = (*(volatile u8 *)0xA10001 & 0x40) ? 63337 : 63920;     /* Z80 clock / 56 */
    return (c / r) * 1000 + (c % r) * 1000 / r;
}

/* called by the probes in hooks.S (and by launch) */
DSEC void diagEvent(u32 type, u32 a, u32 b)
{
    DiagEv *e;
    if (!gRec)
        return;
    if (gNev && type == EV_WRITE && gEv[gNev - 1].type == EV_WRITE) {
        gEv[gNev - 1].n++;
        return;
    }
    if (gNev >= DMAX)
        return;
    e = &gEv[gNev++];
    e->t = z80Now();
    e->type = type;
    e->a = a;
    e->b = b;
    e->n = 1;
}

DSEC static void diagBegin(void)
{
    gNev = 0;
    gRec = 1;
    shortName(gLastName, gCur.name, 38);
    gLastSize = gCur.size;
    z80Start();
    diagEvent(EV_START, 0, 0);
}

DSEC static void diagRow(const DiagEv *e, u32 ms, u32 y)
{
    char h[8];
    switch (e->type) {
    case EV_STATUS: osPrintN(PLANE_A, (const char *)e->a, PAL0, 1, y, 26); break;
    case EV_START: osPrint(PLANE_A, DS_start, PAL1, 1, y); break;
    case EV_LOADED: osPrint(PLANE_A, DS_loaded, PAL1, 1, y); break;
    case EV_LIST: osPrint(PLANE_A, DS_list, PAL1, 1, y); break;
    case EV_CHECK: osPrint(PLANE_A, DS_check, PAL2, 1, y); break;
    default:
        osPrint(PLANE_A, e->type == EV_ERASE ? DS_erase : DS_write, PAL2, 1, y);
        hex(h, e->a, 6);
        osPrint(PLANE_A, h, PAL0, 8, y);
        if (e->type == EV_ERASE)
            osPrintNum(DS_empty, (e->b & 0xFFFF) >> 1, PAL0, 15, y);    /* 512-byte sectors -> KB */
        else
            osPrintNum(DS_x, e->n, PAL0, 15, y);
    }
    osPrintNum(DS_empty, ms, PAL0, 29, y);
    osPrint(PLANE_A, DS_ms, PAL1, 36, y);
}

DSEC static void diagTimes(void)
{
    int i;
    u32 copyMs = 0;
    clearWithBanner();
    osPrint(PLANE_A, DS_times, PAL2, 1, 3);
    if (gNev < 2) {
        osPrint(PLANE_A, DS_none, PAL0, 1, 5);
    } else {
        osPrintN(PLANE_A, gLastName, PAL0, 1, 4, 30);
        osPrintNum(DS_kb, gLastSize >> 10, PAL1, 31, 4);
        for (i = 0; i < gNev - 1 && i < 18; i++) {
            u32 ms = toMs(gEv[i + 1].t - gEv[i].t);
            diagRow(&gEv[i], ms, 6 + i);
            if (gEv[i].type == EV_STATUS && (const char *)gEv[i].a == O_FF9682)  /* "copiando..." */
                copyMs = ms;
        }
        osPrintNum(DS_total, toMs(gEv[gNev - 1].t - gEv[0].t), PAL2, 1, 24);
        if (copyMs)
            osPrintNum(DS_kbs, (gLastSize >> 10) * 1000 / copyMs, PAL2, 20, 24);
    }
    center(DS_play, PAL1, 26);
    waitKey();
}

DSEC static u8 cfi(int k)
{
    return gFlash[4 + k - 0x10] & 0xFF;
}

DSEC static void diagChip(void)
{
    char h[24];
    const char *nm;
    int i, r, y = 12;
    for (;;) {
        clearWithBanner();
        osPrint(PLANE_A, DS_title, PAL2, 1, 3);
        ramFlashProbe(gFlash);
        hex(h, gFlash[0], 4);
        osPrint(PLANE_A, DS_manuf, PAL1, 1, 5);
        osPrint(PLANE_A, h, PAL0, 13, 5);
        for (nm = DS_names; *nm; nm += slen(nm + 1) + 2)
            if ((u8)*nm == (gFlash[0] & 0xFF))
                osPrint(PLANE_A, nm + 1, PAL0, 18, 5);
        osPrint(PLANE_A, DS_dev, PAL1, 1, 6);
        for (i = 1; i < 4; i++) {
            hex(h, gFlash[i], 4);
            osPrint(PLANE_A, h, PAL0, 9 + i * 5, 6);
        }
        osPrint(PLANE_A, gFlashMode() == 1 ? DS_mode1 : DS_mode2, PAL0, 18, 7);
        osPrint(PLANE_A, DS_mode, PAL1, 1, 7);
        osPrint(PLANE_A, (*(volatile u8 *)0xA10001 & 0x40) ? DS_pal : DS_ntsc, PAL1, 1, 8);
        if (cfi(0x10) == 'Q' && cfi(0x11) == 'R' && cfi(0x12) == 'Y') {
            osPrintNum(DS_size, 1UL << (cfi(0x27) - 10), PAL0, 1, 10);
            osPrintNum(DS_buf, cfi(0x2A) ? 1UL << cfi(0x2A) : 0, PAL0, 1, 11);
            osPrintNum(DS_tword, cfi(0x1F) ? 1UL << cfi(0x1F) : 0, PAL0, 1, 12);
            osPrintNum(DS_tbuf, cfi(0x20) ? 1UL << cfi(0x20) : 0, PAL0, 1, 13);
            osPrintNum(DS_terase, cfi(0x21) ? 1UL << cfi(0x21) : 0, PAL0, 1, 14);
            osPrintNum(DS_regions, cfi(0x2C), PAL0, 1, 15);
            for (r = 0, y = 16; r < cfi(0x2C) && r < 4; r++, y++) {
                u32 n = ((u32)cfi(0x2E + 4 * r) << 8 | cfi(0x2D + 4 * r)) + 1;
                u32 kb = (((u32)cfi(0x30 + 4 * r) << 8 | cfi(0x2F + 4 * r)) * 256) >> 10;
                osPrintNum(DS_empty, n, PAL0, 2, y);
                osPrint(PLANE_A, DS_x, PAL1, 7, y);
                osPrintNum(DS_region, kb, PAL0, 8, y);
            }
        } else {
            osPrint(PLANE_A, DS_nocfi, PAL0, 1, 10);
            y = 12;
        }
        osPrint(PLANE_A, DS_raw, PAL1, 1, 20);
        for (i = 0; i < 48; i++) {          /* 12 bytes per row: "xx xx xx ..." */
            hex(h, cfi(0x10 + i), 2);
            osPrint(PLANE_A, h, PAL0, 1 + (i % 12) * 3, 21 + i / 12);
        }
        center(DS_keys, PAL1, 26);
        while (PAD)
            ;
        while (!PAD)
            ;
        if (PAD & BTN_A) {
            while (PAD)
                ;
            diagTimes();
            continue;
        }
        while (PAD)
            ;
        return;
    }
}
#endif

static int isRom(const char *name);

/* load (and optionally start) gCur; returns only when not started */
static u8 launch(int start)
{
    u8 e;
    if (gCur.size < 38 * 512) {         /* stock loader divides the sector count by 38 */
        info(S_too_small);
        return 1;
    }
#ifdef DIAG
    diagBegin();
#endif
    e = osLoadGame(&gCur);
#ifdef DIAG
    diagEvent(EV_LOADED, 0, 0);
#endif
    if (e) {
#ifdef DIAG
        gRec = 0;
        z80Stop();
#endif
        osError(S_prog_error, e);
        return e;
    }
    if (isRom(gCur.name))               /* a .rar/.txt loaded by mistake stays out of the recents */
        listAdd(0, &gCur);
#ifdef DIAG
    diagEvent(EV_LIST, 0, 0);
    gRec = 0;
    z80Stop();
    diagTimes();
#endif
    if (start)
        osStartGame(0);
    return 0;
}

static int isRom(const char *name)
{
    static const char exts[] = "bin\0md\0gen\0smd\0sms\0" "32x\0";
    const char *dot = 0, *e;
    for (; *name; name++)
        if (*name == '.')
            dot = name + 1;
    if (!dot)       /* the OS truncates long names that cross a directory sector: no extension left */
        return 1;
    for (e = exts; *e; e += slen(e) + 1) {
        const char *a = dot, *b = e;
        while (*a && lower(*a) == *b)
            a++, b++;
        if (!*a && !*b)
            return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------- game selection */

static void selectGame(void)
{
    Rec *r = 0;
    u8 e;

    gBrowseMode = 1;
    e = osBrowser(&r, 0);
    gBrowseMode = 0;
    gDirLoaded = 1;
    osFill(PLANE_A, 0, 0, 0, 40, 25);
    if (e) {
        osError(S_sel_error, e);
        return;
    }
    if (!r)
        return;
    memcpy(&gCur, r, sizeof(Rec));
    launch(1);
}

static void listMenu(int l)
{
    u8 sel = 0;
    for (;;) {
        const ListEnt *list = LIST_AT(FLASH_BLOCK, l);
        int n = flashValid() ? FLASH_HDR->count[l] : 0, i;
        u8 r;

        if (n > LIST_MAX)
            n = LIST_MAX;
        gTitle = l ? S_fav_title : S_recent_title;
        gOverlay = overlayTitle;
        if (!n) {
            info(l ? S_no_fav : S_no_recent);
            gOverlay = 0;
            return;
        }
        for (i = 0; i < n; i++) {
            shortName(gItemBuf[i], list[i].name, 34);
            gItems[i] = gItemBuf[i];
        }
        if (!l)
            gItems[n] = S_clear_recent;     /* last item of the recents: empty the list */
        if (sel >= n)
            sel = n - 1;
        if (!l)                             /* osMenu centres the items on row 12 */
            gHiRow = 12 + n;                /* n games + "[ LIMPAR RECENTES ]": last row 11 + count */
        r = menu(gItems, n + !l, sel);
        gHiRow = 0;
        gOverlay = 0;
        if (r & 0x40)
            return;
        if (!l && r == n) {
            listClear(0);
            continue;                       /* now shows "Nenhum jogo recente" */
        }
        sel = r;
        if (l) {
            static const char *const sub[] = {S_fv_play, S_fv_remove, S_back};
            u8 s;
            gTitle = gItemBuf[r];
            gOverlay = overlayTitle;
            s = menu(sub, 3, 0);
            gOverlay = 0;
            if (s == 1) {
                listRemove(1, r);
                info(S_fav_removed);
            }
            if (s != 0)
                continue;
        }
        if (!fatEnsure())
            return;
        if (!entryValid(&list[r])) {
            info(S_not_found);
            continue;
        }
        memset(&gCur, 0, sizeof(Rec));
        memcpy(&gCur, &list[r], 14);
        memcpy(gCur.name, list[r].name, sizeof(list[r].name));
        launch(1);
    }
}

/* scan the loaded directory from a random start for a ROM file (into gCur) */
static int pickRom(void)
{
    u16 n = DIR_COUNT(), s = umod(rnd(), n), i;
    for (i = 0; i < n; i++) {
        DirEnt *e = DIR_ENT(umod(s + i, n));
        if (e->isdir)
            continue;
        if (!osMakeRec(e, &gCur) && isRom(gCur.name))
            return 1;
    }
    return 0;
}

static int pickSubdir(void)
{
    u16 n = DIR_COUNT(), s = umod(rnd(), n), i;
    for (i = 0; i < n; i++) {
        DirEnt *e = DIR_ENT(umod(s + i, n));
        if (!e->isdir || osMakeRec(e, &gTmp))
            continue;
        if (gTmp.name[0] == '.')
            continue;
        if (lower(gTmp.name[0]) == 'e' && lower(gTmp.name[1]) == 'd' && lower(gTmp.name[2]) == 'm' &&
            lower(gTmp.name[3]) == 'd' && !gTmp.name[4])
            continue;
        return !osOpenDir(gTmp.cluster);
    }
    return 0;
}

static void randomGame(void)
{
    int attempt, depth;
    if (!fatEnsure())
        return;
    clearWithBanner();
    center(S_rand_search, PAL0, 12);
    for (attempt = 0; attempt < 6; attempt++) {
        if ((attempt || !gDirLoaded) && osOpenDir(0))
            break;
        gDirLoaded = 1;
        for (depth = 0; depth < 6 && DIR_COUNT(); depth++) {
            if (pickRom()) {
                launch(1);
                return;
            }
            if (!pickSubdir())
                break;
        }
    }
    info(S_no_games);
}

/* ---------------------------------------------------------------- file menu (A on a file) */

static int readSector0(Rec *r, void *dst)
{
    return !osOpen(r, 0) && !osRead(dst, 1);
}

/*
 * Loads gCur's header into gSector0 and its box art (palette 3, tiles 0x80..) into the VDP.
 * The .ART file is streamed sector by sector through gArtBuf so the browser page cache survives.
 * abortable: give up as soon as a button is pressed (returns 0, nothing cached).
 */
ROMB_CODE static int readArtFile(u16 tile, u16 *pal, int abortable)
{
    int s, i;
    for (s = 0; s < 7; s++) {           /* 32-byte palette, then 108 tiles: 16 slots per sector */
        int first = s ? 0 : 1, t = s * 16 + first - 1, n = 16 - first;
        if ((abortable && PAD) || osRead(gArtBuf, 1))
            return 0;
        if (!s)
            for (i = 0; i < 14; i++)
                pal[i] = ((u16 *)gArtBuf)[i + 1];
        if (t + n > 108)
            n = 108 - t;
        if (n > 0)
            osLoadTiles(gArtBuf + first * 32, tile + t, n, 0);
    }
    return 1;
}

__attribute__((noinline)) static int loadArtFile(int abortable)
{
    u32 h = 0;
    u16 pal[14];
    int i;
    char *p;

    gArtOk = gHdrOk = 0;
    gArtName[0] = 0;
    if (!readSector0(&gCur, gSector0))
        return 1;
    gHdrOk = 1;
    for (i = 0; i < 256; i++)
        h = ((h << 5) | (h >> 27)) ^ ((u16 *)gSector0)[i];
    hex(gArtName, h, 8);
    scpy(gArtName + 8, ".ART");
    if (gArtCache && gArtHash == h) {
        gArtOk = gArtCache == 1;
        return 1;
    }
    gArtCache = 0;
    if (abortable && PAD)
        return 0;
    p = scpy(gArtPath, S_art_prefix);
    scpy(p, gArtName);
    if (osFind(gArtPath, &gTmp, 0) || gTmp.isdir || osOpen(&gTmp, 0)) {
        gArtHash = h;
        gArtCache = 2;
        return 1;
    }
    if (!readArtFile(0x80, pal, abortable))
        return 0;
    for (i = 0; i < 14; i++)
        osSetColor(3, i + 1, pal[i]);
    gArtHash = h;
    gArtCache = 1;
    gArtOk = 1;
    return 1;
}

/* osFind walks the card's folders and leaves the "current folder" of the browser's directory table
 * (DIRHDR+2) on the last one it opened - /EDMD/ART. The browser reads it back (the parent it returns
 * to with B, the folder the letter filter reloads), so every lookup of ours puts it back. */
static int loadArt(int abortable)
{
    u32 keep = DIR_CLUSTER();
    int r = loadArtFile(abortable);
    DIR_CLUSTER() = keep;
    return r;
}

/* draw the cover of the browser entry idx next to the list; returns 1 when drawn */
static int preview(u16 idx)
{
    u16 slot = umod(idx, 21);
    if (idx >= DIR_COUNT() || DIR_ENT(idx)->isdir)
        return 0;
    memcpy(&gCur, RECCACHE + slot * 0x110, sizeof(Rec));
    if (gCur.isdir || !isRom(gCur.name) || !loadArt(1) || !gArtOk || PAD)
        return 0;
    osFill(PLANE_A, 0, 26, PREV_TOP, 13, 9);
    osFillSeq(PLANE_A, PAL3 | 0x80, 27, PREV_TOP, 12, 9);
    return 1;
}

/* browser input wait (hooked): show the cover once the cursor rests on a ROM, clear it on input */
void browserIdle(u32 idx)
{
    u32 t0 = VBCOUNT;
    u8 tried = 0, drawn = 0;
    while (!PAD) {
        if (!gBrowseMode || tried || VBCOUNT - t0 < PREVIEW_DELAY)
            continue;
        tried = 1;
        drawn = preview((u16)idx);
    }
    if (drawn)
        osFill(PLANE_A, 0, 26, PREV_TOP, 13, 9);
}

static void overlayFile(void)
{
    center(gTitle, PAL2, 4);            /* a blank row under the banner */
    if (gArtOk)
        osFillSeq(PLANE_B, PAL3 | 0x80, 26, 8, 12, 9);
    else
        osPrint(PLANE_A, S_no_art, PAL1, 28, 12);
}

static void hdrField(const char *label, u32 y, u32 off, int len, u32 x)
{
    char b[50];
    const u8 *s = gSector0 + off, *e = s + len;
    int i = 0, kanji = 0;
    if (label)
        osPrint(PLANE_A, label, PAL2, 2, y);
    while (s < e) {
        u8 c = *s++;
        if (((c >= 0x81 && c <= 0x9F) || (c >= 0xE0 && c <= 0xEF)) && s < e) {
            u8 d = *s++;                /* Shift-JIS: keep full-width space/digits/letters */
            c = c == 0x81 && d == 0x40 ? ' ' :
                c == 0x82 && d >= 0x4F && d <= 0x58 ? d - 0x4F + '0' :
                c == 0x82 && d >= 0x60 && d <= 0x79 ? d - 0x60 + 'A' :
                c == 0x82 && d >= 0x81 && d <= 0x9A ? d - 0x81 + 'a' : 0;
            if (!c) {
                kanji = 1;
                continue;
            }
        }
        b[i++] = (c < 0x20 || c > 0x7E) ? ' ' : c;
    }
    while (i && b[i - 1] == ' ')
        i--;
    b[i] = 0;
    if (!i && !label)
        return;
    osPrint(PLANE_A, i || !kanji ? b : S_ri_kanji, i ? PAL0 : PAL1, x, y);
}

ROMB_CODE __attribute__((noinline)) static void romInfo(void)
{
    char b[16];
    clearWithBanner();
    center(S_ri_title, PAL2, 4);
    if (!gHdrOk || gSector0[0x100] != 'S' || gSector0[0x101] != 'E') {
        center(S_ri_nohdr, PAL0, 9);
    } else {
        hdrField(S_ri_us, 6, 0x150, 24, 14);
        hdrField(0, 7, 0x150 + 24, 24, 14);
        hdrField(S_ri_jp, 9, 0x120, 24, 14);
        hdrField(0, 10, 0x120 + 24, 24, 14);
        hdrField(S_ri_sys, 12, 0x100, 16, 14);
        hdrField(S_ri_cop, 14, 0x110, 16, 14);
        hdrField(S_ri_ser, 16, 0x180, 14, 14);
        hdrField(S_ri_reg, 18, 0x1F0, 16, 14);
        osPrint(PLANE_A, S_ri_chk, PAL2, 2, 20);
        hex(b, (u16)(gSector0[0x18E] << 8 | gSector0[0x18F]), 4);
        osPrint(PLANE_A, b, PAL0, 14, 20);
    }
    osPrintNum(S_ri_size, gCur.size >> 10, PAL2, 2, 22);
    osPrint(PLANE_A, S_ri_art, PAL2, 2, 24);
    osPrint(PLANE_A, gArtOk ? gArtName : S_no_art, gArtOk ? PAL0 : PAL1, 14, 24);
    center(S_press_key, PAL1, 26);
    waitKey();
}

/* next/previous ROM file of the loaded folder from idx (dir = -1/+1) into gCur; -1 when none */
static int neighbourRom(int idx, int dir)
{
    int n = DIR_COUNT();
    for (idx += dir; idx >= 0 && idx < n; idx += dir) {
        DirEnt *e = DIR_ENT(idx);
        if (!e->isdir && !osMakeRec(e, &gTmp) && isRom(gTmp.name)) {
            memcpy(&gCur, &gTmp, sizeof(Rec));
            return idx;
        }
    }
    return -1;
}

/* entered from the browser hook when A is pressed on a file; idx = cursor index.
 * LEFT/RIGHT switch to the previous/next game; the returned index becomes the browser cursor. */
u32 fileMenuFromBrowser(u32 idx)
{
    static const char *const items[] = {S_fm_load_start, S_fm_load_only, S_fm_cheats, S_fm_add_fav, S_fm_rom_info,
                                        S_back};
    u8 sel = 0, r;
    char title[40];

    idx &= 0xFFFF;
    memcpy(&gCur, RECCACHE + umod(idx, 21) * 0x110, sizeof(Rec));
    loadArt(0);
    shortName(title, gCur.name, 38);
    for (;;) {
        gTitle = title;
        gOverlay = overlayFile;
        MENU_CENTER_A = MENU_CENTER_B = 12;
        gMenuLR = 1;
        r = menu(items, 6, sel);
        gMenuLR = 0;
        MENU_CENTER_A = MENU_CENTER_B = 20;
        gOverlay = 0;
        if (r == 0x81 || r == 0x82) {
            int i = neighbourRom(idx, r == 0x81 ? -1 : 1);
            if (i >= 0) {
                idx = i;
                loadArt(0);
                shortName(title, gCur.name, 38);
            }
            continue;
        }
        if (r & 0x40)
            break;
        sel = r;
        if (r == 0) {
            launch(1);
            break;
        }
        if (r == 1) {
            if (!launch(0))
                info(S_loaded_ok);
            break;
        }
        if (r == 2) {                   /* load, the stock GG code menu ("aplicar" patches it), play */
            if (!launch(0)) {
                gCheatPlay = 1;         /* START (aplicar) in the code list starts the game (ramCheatApply) */
                osCheats();
                gCheatPlay = 0;
                osStartGame(0);
            }
            break;
        }
        if (r == 3) {
            listAdd(1, &gCur);
            info(S_fav_saved);
        } else if (r == 4) {
            romInfo();
        } else {
            break;
        }
    }
    osClear();
    drawWallpaper();
    drawBanner(PLANE_B);                /* the browser only redraws the list (plane A) */
    PAGE_CACHE = 0xFFFF;
    return idx;
}

/* ---------------------------------------------------------------- flash extension (ext.c) */

/* Code that does not fit in the OS image lives in flash block 0x40000 (never used by the OS), copied
 * there from /EDMD/V1EXT.BIN. The installer runs from RAM, in the stock main menu's place (0xFF528E,
 * replaced by myMainMenu): the OS copies it there at boot with the rest of the image. Its strings take
 * the stock main menu's ones (.deadstr, 0xFF96C8). */
#define DEAD_CODE __attribute__((section(".dead.text"), noinline))
#define EXT_ADDR 0x40000
#define EXT_MAGIC 0x50544258            /* 'PTBX', then the build id */

u32 srchMain(void);

__attribute__((noinline)) static int extHdrOk(const u32 *h)
{
    return h[0] == EXT_MAGIC && h[1] == BUILD_ID;
}

/* /EDMD/V1EXT.BIN of this build -> flash 0x40000. Its first sector (the header) is written last, so a cut
 * install never looks complete. */
DEAD_CODE static int extInstall(void)
{
    u32 keep = DIR_CLUSTER(), n, s;

    if (!osFind(S_ext_path, &gTmp, 0) && !osOpen(&gTmp, 0) && !osRead(gSector0, 1) && extHdrOk((u32 *)gSector0)) {
        n = (gTmp.size + 511) >> 9;
        osPrint(PLANE_A, S_ext_install, PAL2, 1, 26);
        osFlashErase(EXT_ADDR, 0x80, 1);
        for (s = 1; s < n && !osRead(gArtBuf, 1); s++)
            osFlashWrite(gArtBuf, EXT_ADDR + (s << 9), 1);
        if (s == n)
            osFlashWrite(gSector0, EXT_ADDR, 1);
    }
    DIR_CLUSTER() = keep;
    if (extHdrOk((const u32 *)EXT_ADDR))
        return 1;
    info(S_ext_missing);
    return 0;
}

/* browser C menu, "Buscar em todas as pastas" */
static u32 extSearch(void)
{
    if (!extHdrOk((const u32 *)EXT_ADDR) && !extInstall())
        return 0;
    return srchMain();
}

/* ---------------------------------------------------------------- about / theme / main */

void myAbout(void)
{
    gArtCache = 0;                      /* the logo replaces the cached cover tiles/palette */
    clearWithBanner();
    center(S_ab_title, PAL0, 3);
    center(S_ab_dev, PAL1, 4);
    center(S_ab_mod1, PAL2, 6);
    center(S_ab_mod2, PAL0, 7);
    center(S_ab_sup, PAL1, 9);
    center(S_ab_url, PAL0, 10);
    center(S_ab_mail, PAL0, 11);
    if (*(const u32 *)0x1C000 == 0x45444844) {     /* 'EDHD' distributor block */
        center(S_ab_date, PAL1, 13);
        center((const char *)0x1C004, PAL0, 14);
        center(S_ab_dist, PAL1, 16);
        center((const char *)0x1C024, PAL0, 17);
        center((const char *)0x1C04C, PAL0, 18);
#ifndef DIAG    /* the diagnostics build reuses the logo rows for its code */
        osLoadTiles((const void *)0x1CC20, 0x80, 120, 0);
        osSetPal(3, (const void *)0x1C200);
        osFillSeq(PLANE_A, PAL3 | 0x80, 0, 20, 40, 3);
#endif
    }
    center(S_press_key, PAL1, 26);
    waitKey();
    osSetColor(3, 15, 0xF00);
}

static void cycleTheme(void)
{
    gTheme = (gTheme + 1) & 3;
    applyTheme();
    center(S_saving, PAL1, 23);
    scratchLoad();
    scratchCommit();
}

void myMainMenu(void)
{
    static const char *const thm[] = {S_thm0, S_thm1, S_thm2, S_thm3};
    static const char *const items[8] = {S_mm_play, S_mm_select, S_mm_recent, S_mm_fav, S_mm_random,
                                         S_mm_options, S_mm_cheats, S_mm_tools};
    for (;;) {
        u8 r;
        memcpy(gItems, items, sizeof(items));
        scpy(scpy(gThemeItem, S_mm_theme), thm[gTheme & 3]);
        gItems[8] = gThemeItem;
#ifdef DIAG
        gItems[9] = DS_menu;
        r = osMenu(gItems, 10, 2, gMainSel, 1);
        if (r == 9) {
            gMainSel = r;
            diagChip();
            continue;
        }
#else
        r = osMenu(gItems, 9, 2, gMainSel, 1);
#endif
        if (r >= 9)
            continue;
        gMainSel = r;
        switch (r) {
        case 0: osStartGame(0); break;
        case 1: selectGame(); break;
        case 2: listMenu(0); break;
        case 3: listMenu(1); break;
        case 4: randomGame(); break;
        case 5: osOptions(); break;
        case 6: osCheats(); break;
        case 7: ramToolbox(); break;
        case 8: cycleTheme(); break;
        }
    }
}

/* boot hook (replaces the call to the FAT pointer init during OS init) */
void myInit(void)
{
    osFatPtrInit();
    memset(bssStart, 0, bssEnd - bssStart);
    memcpy(ramStubRam, ramStubStart, ramStubEnd - ramStubStart);
    gRand = VBCOUNT ^ HVCOUNT;
    if (flashValid())
        gTheme = FLASH_HDR->theme & 3;
    uploadExtraTiles();
    applyTheme();
}

#include "ext.c"
