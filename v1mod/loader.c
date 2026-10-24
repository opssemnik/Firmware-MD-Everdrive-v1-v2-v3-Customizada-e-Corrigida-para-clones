/*
 * EverDrive-MD v1 PT-BR loader: the only new code in the OS image (cart 0x1E400). The OS boot calls it
 * instead of its main menu. It brings the flash extension (cart 0x40000) up to date from
 * /EDMD/V1EXT.BIN and starts it; the extension has everything else, so a new version of the mod is
 * just a new V1EXT.BIN on the card. Without an extension (or holding B at power on) the stock OS runs.
 * Keep this file small and stable: changing it means flashing the OS again. It must not call anything
 * of the extension (other than through its header).
 */
#include "os.h"

static const char L_path[] = "/EDMD/V1EXT.BIN";
static const char L_update[] = "Atualizando o mod PT-BR...";

/* RAM for the copy: the browser page cache, unused this early */
#define L_HDR ((u32 *)RECCACHE)
#define L_BUF (RECCACHE + 512)
#define L_REC ((Rec *)(RECCACHE + 1024))

static int hdrOk(const u32 *h)
{
    return h[0] == EXT_MAGIC && h[1] == EXT_ABI;
}

/* V1EXT.BIN differs from the extension in flash (magic, abi, id, size): copy it, the header sector
 * last, so a cut copy never looks complete */
static void update(void)
{
    const u32 *cur = (const u32 *)EXT_ADDR;
    Rec *r = L_REC;
    u32 n, s;

    if (osFatInit())
        return;
    FAT_READY = 1;
    if (osFind(L_path, r, 0) || osOpen(r, 0) || osRead(L_HDR, 1) || !hdrOk(L_HDR)
        || (cur[0] == L_HDR[0] && cur[1] == L_HDR[1] && cur[2] == L_HDR[2] && cur[3] == L_HDR[3]))
        return;
    osPrintAl(PLANE_A, L_update, 0, 20, 12, ALIGN_CENTER);
    n = (r->size + 511) >> 9;
    osFlashErase(EXT_ADDR, 0x80, 1);
    for (s = 1; s < n && s < 128 && !osRead(L_BUF, 1); s++)
        osFlashWrite(L_BUF, EXT_ADDR + (s << 9), 1);
    if (s == n)
        osFlashWrite(L_HDR, EXT_ADDR, 1);
}

/* the OS boot's main menu call */
void loaderMain(void)
{
    if (!(osReadPad(0) & BTN_B)) {
        update();
        if (hdrOk((const u32 *)EXT_ADDR))
            EXT_HDR->main();            /* returns only when it could not start */
    }
    osMainMenu();
}
