/*
 * EverDrive-MD v3 PT-BR: search in every folder (main menu -> "Buscar em Todas as Pastas").
 * Overlay page 2: linked at 0xFFC800 and stored in MDOS.BIN at file offset 0x8E00, ovlEnter loads it on
 * demand (d0 = 0x100). By first letter (the directory table's sort key, no SD reads) or by words of the
 * name typed on an on-screen keyboard. The overlay has no RAM of its own: locals only; the results wait
 * in free VRAM (0xA000..0xAFFF) while the folders are read, then become the browser's directory table.
 *
 * Returns what call_mainMenu_from_browser does with the browser's folder levels: 0 cancelled (back to the
 * menu), 1 another list on the same level, 2 results from a folder (one level down, like a subfolder: B
 * goes back to the folder), 3 nothing found from the results (back up to the folder they came from).
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;

typedef struct {
    u32 dirsec;
    char key[4];        /* first 4 characters of the name, lower case (the browser sorts by it) */
    u16 idx;
    u16 isdir;
} DirEnt;

typedef struct {
    u32 cluster, size, dirsec;
    u16 idx;
    char name[256];
    u16 isdir;
} Rec;

/* ---- MDOS routines (RAM-resident OS) and the mod's resident code (addresses from the build) */
#define osOpenDir    ((u8 (*)(u32 cluster))0xFF1C8C)        /* via dirOpenHook */
#define fatGetRec    ((u8 (*)(DirEnt *e, Rec *r))0xFF2872)
#define loadSector   ((u8 (*)(u32 lba))0xFF15A4)
#define menuDraw     ((u16 (*)(const char *const *menu, u32 count, u32 sel))0xFF4834)
#define gSetPal      ((void (*)(u32 pal))0xFF30A0)
#define gPrintAt     ((void (*)(const char *s, u32 x, u32 y))0xFF3556)
#define gPrintCenter ((void (*)(const char *s, u32 y))0xFF35FE)
#define gRepaint     ((void (*)(void))0xFF33B6)               /* the screen is double buffered */
#define padRead      ((u16 (*)(void))0xFF620A)                /* waits one vblank */
#define clsBanner    ((void (*)(void))CLS_BANNER)

#define DIRHDR       (*(u8 **)0xFFC46C)
#define DIR_COUNT()  (*(u16 *)DIRHDR)
#define DIR_CLUSTER() (*(u32 *)(DIRHDR + 2))
#define DIR_PARENT() (*(u32 *)(DIRHDR + 0x12))
#define DIR_TAB      ((DirEnt *)(DIRHDR + 0x16))
#define DIR_ENT(i)   (((DirEnt **)(DIRHDR + 0x3016))[i])
#define DIR_ROOT()   (*(u16 *)(DIRHDR + 0x4016))              /* the browser's B does nothing when set */
#define SECBUF       (*(u8 **)0xFFC464)
#define BROWSE_CLUSTER (*(u32 *)0xFFC5B0)                     /* the browser's folder (dirOpenHook) */
#define TAG          ((char *)0xFFC5A8)                       /* "[*]" next to the page counter */
#define REC          ((Rec *)0xFFD600)                        /* scratch record (as the old letter filter) */
#define STACK_TOP    ((u32 *)0xFFDC00)                        /* folders still to read: 0xFFD800..0xFFDBFF */
#define STACK_BOTTOM ((u32 *)0xFFD800)

#define VDP_DATA (*(volatile u16 *)0xC00000)
#define VDP_CTRL (*(volatile u32 *)0xC00004)
#define VRES 0xA000                                           /* results: 8 bytes each, 512 */
#define SR_MAX 512

#define BTN_UP 0x01
#define BTN_DOWN 0x02
#define BTN_LEFT 0x04
#define BTN_RIGHT 0x08
#define BTN_B 0x10
#define BTN_A 0x40
#define BTN_START 0x80

/* font: 0x80 ç, 0x81 ã, 0x82 õ, 0x83 á, 0x84 é, 0x85 ú, 0x86 ó, 0x87 Ã */
static const char S_title[] = "Buscar em Todas as Pastas";
static const char S_by_name[] = "Por Nome (digitar)";
static const char S_af[] = "A - F", S_gl[] = "G - L", S_mr[] = "M - R", S_sz[] = "S - Z", S_num[] = "0 - 9 e Outros";
static const char S_kb_title[] = "Buscar por Nome";
static const char S_kb_help[] = "A: digitar  B: apagar  START: buscar";
static const char S_space[] = "Espa\x80o", S_del[] = "Apagar", S_ok[] = "Buscar";
static const char S_searching[] = "Buscando em Todas as Pastas...";
static const char S_stop[] = "B: parar";
static const char S_folders[] = "Pastas lidas: ";
static const char S_found[] = "Encontrados:  ";
static const char S_none[] = "Nenhum Jogo Encontrado";
static const char S_full[] = "Muitos Resultados: s\x86 os 512 Primeiros";
static const char kbKeys[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'&";
static const u8 kbBtnX[3] = {0, 4, 7};
#define KB_LEN 20
#define KB_X 5
#define KB_Y 9

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

/* libgcc's integer helpers (MDOS has its own, at unknown places) */
u32 __udivsi3(u32 a, u32 b)
{
    u32 q = 0, bit = 1;
    while (b < a && !(b & 0x80000000)) {
        b <<= 1;
        bit <<= 1;
    }
    while (bit) {
        if (a >= b) {
            a -= b;
            q |= bit;
        }
        b >>= 1;
        bit >>= 1;
    }
    return q;
}

u32 __umodsi3(u32 a, u32 b)
{
    return a - __udivsi3(a, b) * b;
}

long __divsi3(long a, long b)
{
    long q = __udivsi3(a < 0 ? -a : a, b < 0 ? -b : b);
    return (a < 0) != (b < 0) ? -q : q;
}

long __modsi3(long a, long b)
{
    return a - __divsi3(a, b) * b;
}

u32 __mulsi3(u32 a, u32 b)
{
    u32 r = 0;
    while (b) {
        if (b & 1)
            r += a;
        a <<= 1;
        b >>= 1;
    }
    return r;
}

static char lower(char c)
{
    return c >= 'A' && c <= 'Z' ? c + 32 : c;
}

static char *scpy(char *d, const char *s)
{
    while ((*d = *s++))
        d++;
    return d;
}

static void waitRelease(void)
{
    while (padRead())
        ;
}

/* one line of the search screens */
static void line(const char *s, u32 pal, u32 x, u32 y)
{
    gSetPal(pal);
    gPrintAt(s, x, y);
}

static void lineNum(const char *label, u32 n, u32 y)
{
    char b[24], *p = scpy(b, label), d[6];
    int i = 0;
    do
        d[i++] = '0' + n % 10;
    while ((n /= 10) && i < 5);
    while (i)
        *p++ = d[--i];
    *p++ = ' ';
    *p = 0;
    line(b, 0, 12, y);
}

static u16 menu(const char *const *m, u32 n)
{
    u16 r = menuDraw(m, n, 0);
    waitRelease();
    return r;
}

/* ---------------------------------------------------------------- on-screen keyboard */

static void kbDraw(const char *q, int n, int cx, int cy)
{
    static const char *const btn[3] = {S_space, S_del, S_ok};
    char b[KB_LEN + 4];
    int i, x, y;

    b[0] = '>';
    b[1] = ' ';
    for (i = 0; i < KB_LEN + 1; i++)
        b[i + 2] = i < n ? q[i] : i == n ? '_' : ' ';
    b[KB_LEN + 3] = 0;
    line(b, 0, 8, 6);
    for (y = 0; y < 4; y++)
        for (x = 0; x < 10; x++) {
            int sel = x == cx && y == cy;
            b[0] = sel ? '[' : ' ';
            b[1] = kbKeys[y * 10 + x];
            b[2] = sel ? ']' : ' ';
            b[3] = 0;
            line(b, sel, KB_X + x * 3, KB_Y + y * 2);
        }
    for (i = 0; i < 3; i++) {
        int sel = cy == 4 && cx * 3 / 10 == i;
        char *p = b;
        *p++ = sel ? '[' : ' ';
        p = scpy(p, btn[i]);
        *p++ = sel ? ']' : ' ';
        *p = 0;
        line(b, sel, KB_X + kbBtnX[i] * 3, KB_Y + 8);
    }
    gRepaint();
}

/* types the search text into q (upper case, words split by single spaces); its length, 0 = cancel */
static int kbInput(char *q)
{
    int n = 0, cx = 0, cy = 0;
    u16 k;

    clsBanner();
    gSetPal(1);
    gPrintCenter(S_kb_title, 3);
    line(S_kb_help, 0, 2, 26);
    for (;;) {
        kbDraw(q, n, cx, cy);
        waitRelease();
        while (!(k = padRead()))
            ;
        if (k & BTN_UP)
            cy = cy ? cy - 1 : 4;
        else if (k & BTN_DOWN)
            cy = cy < 4 ? cy + 1 : 0;
        else if (k & (BTN_LEFT | BTN_RIGHT)) {
            int d = k & BTN_LEFT ? -1 : 1;
            if (cy == 4)                /* the 3 buttons: Espaço 0-3, Apagar 4-6, Buscar 7-9 */
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
    waitRelease();
    return n;
}

/* ---------------------------------------------------------------- matching */

static int isRom(const char *name)
{
    static const char exts[] = "bin\0md\0gen\0smd\0sms\0" "32x\0";
    const char *dot = 0, *e;
    for (; *name; name++)
        if (*name == '.')
            dot = name + 1;
    if (!dot)       /* long names that cross a directory sector lose their extension */
        return 1;
    for (e = exts; *e;) {
        const char *a = dot, *b = e;
        while (*a && lower(*a) == *b)
            a++, b++;
        if (!*a && !*b)
            return 1;
        while (*e++)
            ;
    }
    return 0;
}

/* every word of q (upper case) appears somewhere in name, in any order, ignoring case */
static int nameHas(const char *name, const char *q)
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
static u32 subdirCluster(const DirEnt *e)
{
    static const char edmd[11] = "EDMD       ";
    const u8 *d;
    int i;

    if (e->idx >= 16 || loadSector(e->dirsec))
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

static int srMatch(DirEnt *e, char letter, const char *q)
{
    char c;
    if (q)
        return !fatGetRec(e, REC) && REC->name[0] != '.' && isRom(REC->name) && nameHas(REC->name, q);
    c = e->key[0];
    if (c >= 'a' && c <= 'z')
        c -= 32;
    return letter == '#' ? c < 'A' || c > 'Z' : c == letter;
}

/* ---------------------------------------------------------------- results in VRAM */

static void vramAt(u32 addr, u32 write)
{
    VDP_CTRL = (write ? 0x40000000 : 0) | ((addr & 0x3FFF) << 16) | (addr >> 14);
}

static u16 irqOff(void)
{
    u16 sr;
    asm volatile("move.w %%sr, %0\n\tmove.w #0x2700, %%sr" : "=d"(sr));
    return sr;
}

static void irqOn(u16 sr)
{
    asm volatile("move.w %0, %%sr" : : "d"(sr));
}

/* result i: idx << 28 | directory sector, then the 4 key letters */
static void resPut(int i, const DirEnt *e)
{
    u32 a = (u32)e->idx << 28 | e->dirsec;
    const u16 *k = (const u16 *)e->key;
    u16 sr = irqOff();
    vramAt(VRES + i * 8, 1);
    VDP_DATA = a >> 16;
    VDP_DATA = a;
    VDP_DATA = k[0];
    VDP_DATA = k[1];
    irqOn(sr);
}

static void resGet(int i, DirEnt *e)
{
    u32 a;
    u16 *k = (u16 *)e->key;
    u16 sr = irqOff();
    vramAt(VRES + i * 8, 0);
    a = (u32)VDP_DATA << 16;
    a |= VDP_DATA;
    k[0] = VDP_DATA;
    k[1] = VDP_DATA;
    irqOn(sr);
    e->dirsec = a & 0x0FFFFFFF;
    e->idx = a >> 28;
    e->isdir = 0;
}

/* walks every folder of the card from the root (depth first); -1 when stopped with B */
static int srWalk(char letter, const char *q, u8 *full)
{
    u32 *stk = STACK_TOP;
    int n = 0, folders = 0;

    *--stk = 0;                         /* the root */
    while (stk < STACK_TOP) {
        int i, cnt;
        if (padRead() & BTN_B)
            return -1;
        if (osOpenDir(*stk++))
            continue;
        lineNum(S_folders, ++folders, 12);
        gRepaint();
        cnt = DIR_COUNT();
        for (i = 0; i < cnt; i++) {
            DirEnt *e = DIR_ENT(i);
            if (e->isdir) {
                u32 c = subdirCluster(e);
                if (!c)
                    continue;
                if (stk == STACK_BOTTOM) {
                    *full = 1;          /* too many folders waiting: skip this one */
                    continue;
                }
                *--stk = c;
            } else if (srMatch(e, letter, q)) {
                if (n == SR_MAX) {
                    *full = 1;
                    return n;
                }
                resPut(n++, e);
                lineNum(S_found, n, 14);
            }
        }
    }
    return n;
}

/* the results become the browser's directory table (sorted like a folder), a level under the folder */
static void srShow(int n, u32 cluster)
{
    DirEnt *tab = DIR_TAB;
    int i, j;

    for (i = 0; i < n; i++) {
        DirEnt *e = &tab[i];
        u32 k;
        resGet(i, e);
        k = *(const u32 *)e->key;       /* insertion sort of the pointers by the 4-letter key */
        for (j = i; j > 0 && *(const u32 *)DIR_ENT(j - 1)->key > k; j--)
            DIR_ENT(j) = DIR_ENT(j - 1);
        DIR_ENT(j) = e;
    }
    *(u16 *)DIRHDR = n;
    DIR_CLUSTER() = cluster;
    DIR_PARENT() = cluster;             /* B: back to the folder */
    DIR_ROOT() = 0;
    BROWSE_CLUSTER = cluster;
    TAG[0] = '[';
    TAG[1] = '*';
    TAG[2] = ']';
    TAG[3] = 0;
}

static void message(const char *s)
{
    const char *m[2] = {S_title, s};
    menu(m, 1);
}

__attribute__((section(".entry"))) u32 searchMain(void)
{
    static const char *const modes[] = {S_title, S_by_name, S_af, S_gl, S_mr, S_sz, S_num};
    const char *items[9];
    char letters[8][2], q[KB_LEN + 1], letter = 0;
    u32 cluster = BROWSE_CLUSTER;
    int in = TAG[0] == '[' && TAG[1] == '*';
    int n, i;
    u16 r;
    u8 full = 0;

    waitRelease();
    r = menu(modes, 6);
    if (r >= 1 && r <= 4) {             /* the letters of the group */
        n = r == 4 ? 8 : 6;
        items[0] = S_title;
        for (i = 0; i < n; i++) {
            letters[i][0] = 'A' + (r - 1) * 6 + i;
            letters[i][1] = 0;
            items[i + 1] = letters[i];
        }
        letter = 'A' + (r - 1) * 6;
        r = menu(items, n);
        letter += r;
    } else if (r == 5) {
        letter = '#';
    }
    if (r == 0xFFFF || (!letter && !kbInput(q)))
        return 0;
    clsBanner();
    gSetPal(1);
    gPrintCenter(S_searching, 9);
    line(S_stop, 0, 16, 26);
    gRepaint();
    n = srWalk(letter, letter ? 0 : q, &full);
    waitRelease();
    if (n <= 0) {
        osOpenDir(cluster);             /* the walk replaced the browser's table: the folder again */
        if (!n)
            message(S_none);
        return in ? 3 : 1;
    }
    srShow(n, cluster);
    if (full)
        message(S_full);
    return in ? 1 : 2;
}
