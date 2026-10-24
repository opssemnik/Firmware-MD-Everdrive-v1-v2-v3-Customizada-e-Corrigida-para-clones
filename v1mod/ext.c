/*
 * Flash extension (included at the end of mod.c): code that no longer fits in the OS image. It is linked
 * at cart 0x40000 (a flash block the OS never uses), shipped as /EDMD/V1EXT.BIN and copied into the
 * flash by extInstall the first time it is needed after an OS update. The base OS enters it only through
 * extSearch, after checking the header (same build id), so nothing here may be inlined into the base:
 * every function is EXT_CODE, every constant EXT_RO.
 */
#define EXT_CODE __attribute__((section(".ext.text"), noinline))
#define EXT_RO __attribute__((section(".ext.ro")))

const u32 extHdr[2] __attribute__((section(".exthdr"), used)) = {EXT_MAGIC, BUILD_ID};

/* ---------------------------------------------------------------- search in every folder */

#define SR_MAX 512                      /* the browser's directory table holds 512 entries */

static u8 gSrFull;                      /* the results (or the folder stack) did not fit: list cut */

/* on-screen keyboard: 4 rows of 10 keys, then ESPACO / APAGAR / BUSCAR */
static const char kbKeys[] EXT_RO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&";
static const u8 kbBtnX[3] EXT_RO = {0, 4, 7};
#define KB_LEN 20
#define KB_X 5
#define KB_Y 9

EXT_CODE static void kbDraw(const char *q, int n, int cx, int cy)
{
    static const char *const btn[3] EXT_RO = {SX_space, SX_del, SX_ok};
    char b[KB_LEN + 4];
    int i, x, y;

    b[0] = '>';
    b[1] = ' ';
    for (i = 0; i < KB_LEN + 1; i++)
        b[i + 2] = i < n ? q[i] : i == n ? '_' : ' ';
    b[KB_LEN + 3] = 0;
    osPrint(PLANE_A, b, PAL0, 8, 6);
    for (y = 0; y < 4; y++)
        for (x = 0; x < 10; x++) {
            int sel = x == cx && y == cy;
            b[0] = sel ? '[' : ' ';
            b[1] = kbKeys[y * 10 + x];
            b[2] = sel ? ']' : ' ';
            b[3] = 0;
            osPrint(PLANE_A, b, sel ? PAL2 : PAL0, KB_X + x * 3, KB_Y + y * 2);
        }
    for (i = 0; i < 3; i++) {           /* (no string literals here: they would land in the base .rodata) */
        int sel = cy == 4 && cx * 3 / 10 == i;
        u32 attr = sel ? PAL2 : PAL0;
        char *p = b;
        *p++ = sel ? '[' : ' ';
        p = scpy(p, btn[i]);
        *p++ = sel ? ']' : ' ';
        *p = 0;
        osPrint(PLANE_A, b, attr, KB_X + kbBtnX[i] * 3, KB_Y + 8);
    }
}

/* types the search text into q (upper case, words split by single spaces); returns its length, 0 = cancel */
EXT_CODE static int kbInput(char *q)
{
    int n = 0, cx = 0, cy = 0;
    u16 k;

    clearWithBanner();
    center(SX_kb_title, PAL2, 3);
    center(SX_kb_help, PAL1, 26);
    for (;;) {
        kbDraw(q, n, cx, cy);
        while (PAD)
            ;
        while (!(k = PAD))
            ;
        if (k & BTN_UP)
            cy = cy ? cy - 1 : 4;
        else if (k & BTN_DOWN)
            cy = cy < 4 ? cy + 1 : 0;
        else if (k & (BTN_LEFT | BTN_RIGHT)) {
            int d = k & BTN_LEFT ? -1 : 1;
            if (cy == 4)                /* the 3 buttons: ESPACO 0-3, APAGAR 4-6, BUSCAR 7-9 */
                cx = kbBtnX[(cx * 3 / 10 + 3 + d) % 3];
            else
                cx = (cx + 10 + d) % 10;
        } else if (k & BTN_START) {
            if (n)
                break;
        } else if (k & BTN_B) {
            if (!n)
                return 0;
            n--;
        } else if (k & BTN_A) {
            char c = cy < 4 ? kbKeys[cy * 10 + cx] : cx * 3 / 10 == 0 ? ' ' : 0;
            if (cy == 4 && cx * 3 / 10 == 1) {
                if (n)
                    n--;
            } else if (cy == 4 && cx * 3 / 10 == 2) {
                if (n)
                    break;
            } else if (n < KB_LEN && (c != ' ' || (n && q[n - 1] != ' '))) {
                q[n++] = c;
            }
        }
    }
    while (n && q[n - 1] == ' ')
        n--;
    q[n] = 0;
    while (PAD)
        ;
    return n;
}

/* every word of q (upper case) appears somewhere in name, in any order, ignoring case */
EXT_CODE static int nameHas(const char *name, const char *q)
{
    while (*q) {
        const char *te = q, *s;
        int ok = 0;
        while (*te && *te != ' ')
            te++;
        for (s = name; *s && !ok; s++) {
            const char *a = s, *b = q;
            while (b < te && *a && lower(*a) == lower(*b))
                a++, b++;
            ok = b == te;
        }
        if (!ok)
            return 0;
        q = *te ? te + 1 : te;
    }
    return 1;
}

/* cluster of the folder entry e, 0 for ".", ".." and /EDMD (covers, firmware: not games) */
EXT_CODE static u32 subdirCluster(const DirEnt *e)
{
    static const char edmd[11] EXT_RO = "EDMD       ";
    const u8 *d;
    int i;

    if (e->idx >= 16 || osLoadSector(e->dirsec))
        return 0;
    d = SECBUF + (e->idx << 5);
    if (d[0] == '.')
        return 0;
    for (i = 0; i < 11 && d[i] == (u8)edmd[i]; i++)
        ;
    if (i == 11)
        return 0;
    return (u32)d[0x15] << 24 | (u32)d[0x14] << 16 | (u32)d[0x1b] << 8 | d[0x1a];
}

/* files of e's folder that match: letter ('A'..'Z', '#' = others) by the table's sort key (no SD
 * reads), or the words of q in the long name (reads it; ROM files only) */
EXT_CODE static int srMatch(DirEnt *e, char letter, const char *q)
{
    char c;
    if (q)
        return !osMakeRec(e, &gTmp) && gTmp.name[0] != '.' && isRom(gTmp.name) && nameHas(gTmp.name, q);
    c = e->key[0];
    if (c >= 'a' && c <= 'z')
        c -= 32;
    return letter == '#' ? c < 'A' || c > 'Z' : c == letter;
}

/* walks every folder of the card from the root (depth first). Matching entries are copied to the
 * browser page cache (RECCACHE: 512 x 12 bytes from its start), the folders still to visit are kept at
 * its end, growing down. Returns the number of results, -1 when stopped with B. */
EXT_CODE static int srWalk(char letter, const char *q)
{
    DirEnt *res = (DirEnt *)RECCACHE;
    u32 *top = (u32 *)(RECCACHE + SCRATCH_SIZE), *stk = top;
    int n = 0, folders = 0;

    gSrFull = 0;
    *--stk = 0;                         /* the root */
    while (stk < top) {
        int i, cnt;
        if (PAD & BTN_B)
            return -1;
        if (osOpenDir(*stk++))
            continue;
        osPrintNum(SX_folders, ++folders, PAL0, 12, 12);
        cnt = DIR_COUNT();
        for (i = 0; i < cnt; i++) {
            DirEnt *e = DIR_ENT(i);
            if (e->isdir) {
                u32 c = subdirCluster(e);
                if (!c)
                    continue;
                if ((u8 *)(stk - 1) < (u8 *)(res + n + 1)) {
                    gSrFull = 1;        /* no room left for one more folder: skip it */
                    continue;
                }
                *--stk = c;
            } else if (srMatch(e, letter, q)) {
                if (n == SR_MAX || (u8 *)(res + n + 1) > (u8 *)stk) {
                    gSrFull = 1;
                    return n;
                }
                res[n++] = *e;
                osPrintNum(SX_found, n, PAL2, 12, 14);
            }
        }
    }
    return n;
}

/* the results become the browser's directory table (sorted like a folder), shown as a folder of its own
 * ("[*]" next to the page counter); B or "Todos" in the C menu go back to the real folders */
EXT_CODE static void srShow(int n, u32 cluster)
{
    DirEnt *tab = (DirEnt *)(DIRHDR + 0x12);
    int i, j;

    memcpy(tab, RECCACHE, n * sizeof(DirEnt));
    for (i = 0; i < n; i++) {           /* insertion sort of the pointers by the 4-letter key */
        DirEnt *e = &tab[i];
        u32 k = *(const u32 *)e->key;
        for (j = i; j > 0 && *(const u32 *)DIR_ENT(j - 1)->key > k; j--)
            DIR_ENT(j) = DIR_ENT(j - 1);
        DIR_ENT(j) = e;
    }
    *(u16 *)DIRHDR = n;
    DIR_CLUSTER() = cluster;
    gFilter = '*';
    gFilterCount = n;
    gFilterCluster = cluster;
}

/* C menu -> "Buscar em todas as pastas": by first letter or by words of the name. Returns 1 when the
 * browser list changed. */
EXT_CODE u32 srchMain(void)
{
    static const char *const modes[] EXT_RO = {SX_by_name, S_flt_af, S_flt_gl, S_flt_mr, S_flt_sz, S_flt_num};
    static char letters[8][2];
    const char *items[8];
    char q[KB_LEN + 1], letter = 0;
    u32 cluster = DIR_CLUSTER();
    int r, n, i;

    gTitle = SX_title;
    gOverlay = overlayTitle;
    r = menu(modes, 6, 0);
    if (r >= 1 && r <= 4) {             /* the letters of the group */
        n = r == 4 ? 8 : 6;
        for (i = 0; i < n; i++) {
            letters[i][0] = 'A' + (r - 1) * 6 + i;
            items[i] = letters[i];
        }
        letter = 'A' + (r - 1) * 6;
        r = menu(items, n, 0);
        letter += r;
    } else if (r == 5) {
        letter = '#';
    }
    gOverlay = 0;
    if ((r & 0x40) || (!letter && !kbInput(q)))
        return 0;
    clearWithBanner();
    center(SX_searching, PAL2, 9);
    center(SX_stop, PAL1, 26);
    n = srWalk(letter, letter ? 0 : q);
    while (PAD)
        ;
    if (n <= 0) {
        osOpenDir(cluster);             /* the walk replaced the browser's table: the folder again */
        DIR_CLUSTER() = cluster;
        gFilter = 0;
        if (!n)
            info(S_no_games);
        return 1;
    }
    srShow(n, cluster);
    if (gSrFull)
        info(SX_full);
    return 1;
}
