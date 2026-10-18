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
static u32 gRand;
static char gArtName[24];
static char gArtPath[40];
static char gThemeItem[24];
static char gItemBuf[LIST_MAX][38];
static const char *gItems[LIST_MAX + 1];
static u8 gSector0[512] __attribute__((aligned(4)));   /* SD/OS routines access it by words */
static u8 gArtBuf[512] __attribute__((aligned(4)));
static u32 gArtHash;
static u8 gArtCache;                    /* 0 none, 1 = art of gArtHash is in VRAM, 2 = it has no art */
static u8 gPrevTop;

#define PREVIEW_DELAY 24                /* frames resting on a ROM before its cover loads (~0.4 s) */

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
}

/* called by osMenu instead of its screen clear (through the RAM guard) */
void myMenuClear(void)
{
    osClear();
    center(S_banner, PAL2, 1);
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

static void overlayTitle(void)
{
    center(gTitle, PAL2, 3);
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

static void listRemove(int l, int idx)
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

/* load (and optionally start) gCur; returns only when not started */
static u8 launch(int start)
{
    u8 e;
    if (gCur.size < 38 * 512) {         /* stock loader divides the sector count by 38 */
        info(S_too_small);
        return 1;
    }
    e = osLoadGame(&gCur);
    if (e) {
        osError(S_prog_error, e);
        return e;
    }
    listAdd(0, &gCur);
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
    if (!dot)
        return 0;
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
        if (sel >= n)
            sel = n - 1;
        r = menu(gItems, n, sel);
        gOverlay = 0;
        if (r & 0x40)
            return;
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
static int loadArt(int abortable)
{
    u32 h = 0;
    int i, s;
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
    for (s = 0; s < 7; s++) {           /* 32-byte palette, then 108 tiles: 16 slots per sector */
        int first = s ? 0 : 1, t = s * 16 + first - 1, n = 16 - first;
        if ((abortable && PAD) || osRead(gArtBuf, 1))
            return 0;
        if (!s)
            for (i = 1; i < 15; i++)
                osSetColor(3, i, ((u16 *)gArtBuf)[i]);
        if (t + n > 108)
            n = 108 - t;
        if (n > 0)
            osLoadTiles(gArtBuf + first * 32, 0x80 + t, n, 0);
    }
    gArtHash = h;
    gArtCache = 1;
    gArtOk = 1;
    return 1;
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
    gPrevTop = slot < 10 ? 12 : 2;      /* list rows are 2..22; keep the cursor row visible */
    osFill(PLANE_A, 0, 26, gPrevTop, 13, 9);
    osFillSeq(PLANE_A, PAL3 | 0x80, 27, gPrevTop, 12, 9);
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
        osFill(PLANE_A, 0, 26, gPrevTop, 13, 9);
}

static void overlayFile(void)
{
    center(gTitle, PAL2, 3);
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

static void romInfo(void)
{
    char b[16];
    clearWithBanner();
    center(S_ri_title, PAL2, 3);
    if (!gHdrOk || gSector0[0x100] != 'S' || gSector0[0x101] != 'E') {
        center(S_ri_nohdr, PAL0, 8);
    } else {
        hdrField(S_ri_us, 5, 0x150, 24, 14);
        hdrField(0, 6, 0x150 + 24, 24, 14);
        hdrField(S_ri_jp, 8, 0x120, 24, 14);
        hdrField(0, 9, 0x120 + 24, 24, 14);
        hdrField(S_ri_sys, 11, 0x100, 16, 14);
        hdrField(S_ri_cop, 13, 0x110, 16, 14);
        hdrField(S_ri_ser, 15, 0x180, 14, 14);
        hdrField(S_ri_reg, 17, 0x1F0, 16, 14);
        osPrint(PLANE_A, S_ri_chk, PAL2, 2, 19);
        hex(b, (u16)(gSector0[0x18E] << 8 | gSector0[0x18F]), 4);
        osPrint(PLANE_A, b, PAL0, 14, 19);
    }
    osPrintNum(S_ri_size, gCur.size >> 10, PAL2, 2, 21);
    osPrint(PLANE_A, S_ri_art, PAL2, 2, 23);
    osPrint(PLANE_A, gArtOk ? gArtName : S_no_art, gArtOk ? PAL0 : PAL1, 14, 23);
    center(S_press_key, PAL1, 26);
    waitKey();
}

/* entered from the browser hook when A is pressed on a file; idx = cursor index */
void fileMenuFromBrowser(u32 idx)
{
    static const char *const items[] = {S_fm_load_start, S_fm_load_only, S_fm_add_fav, S_fm_rom_info, S_back};
    u8 sel = 0, r;
    char title[40];

    memcpy(&gCur, RECCACHE + umod(idx, 21) * 0x110, sizeof(Rec));
    loadArt(0);
    shortName(title, gCur.name, 38);
    for (;;) {
        gTitle = title;
        gOverlay = overlayFile;
        MENU_CENTER_A = MENU_CENTER_B = 12;
        r = menu(items, 5, sel);
        MENU_CENTER_A = MENU_CENTER_B = 20;
        gOverlay = 0;
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
        if (r == 2) {
            listAdd(1, &gCur);
            info(S_fav_saved);
        } else if (r == 3) {
            romInfo();
        } else {
            break;
        }
    }
    osClear();
    PAGE_CACHE = 0xFFFF;
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
        osLoadTiles((const void *)0x1CC20, 0x80, 120, 0);
        osSetPal(3, (const void *)0x1C200);
        osFillSeq(PLANE_A, PAL3 | 0x80, 0, 20, 40, 3);
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
        r = osMenu(gItems, 9, 2, gMainSel, 1);
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
