import os
import re
import sys
import time
import zlib
import random
import struct
import argparse
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

# =============================================================================
# EverDrive-MD v3 PT-BR Custom OS - Parallel Boxart Downloader & .ART Builder
# Retrogamer POA by Antonio and the Nobre
# =============================================================================

CACHE_DIR = Path(__file__).parent / ".art_cache"
ART_FILE_SIZE = 3584

LIBRETRO_DAT_URLS = {
    "md": "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/Sega%20-%20Mega%20Drive%20-%20Genesis.dat",
    "sms": "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/Sega%20-%20Master%20System%20-%20Mark%20III.dat",
}

LIBRETRO_THUMB_BASES = {
    "md": "https://thumbnails.libretro.com/Sega%20-%20Mega%20Drive%20-%20Genesis",
    "sms": "https://thumbnails.libretro.com/Sega%20-%20Master%20System%20-%20Mark%20III",
}

ROM_EXTENSIONS = {".md", ".bin", ".gen", ".smd", ".sms", ".32x"}

# Global coordination for HTTP 429 / server rate-limiting across worker threads
_rate_lock = threading.Lock()
_rate_limit_until = 0.0
_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg, flush=True)


def wait_for_rate_limit():
    while True:
        with _rate_lock:
            now = time.monotonic()
            wait_sec = _rate_limit_until - now
        if wait_sec <= 0:
            return
        time.sleep(min(wait_sec, 1.0))


def trigger_global_cooldown(seconds: float, reason: str):
    global _rate_limit_until
    with _rate_lock:
        now = time.monotonic()
        target = now + seconds
        if target > _rate_limit_until:
            _rate_limit_until = target
            safe_print(f"  [Rate Limit] {reason} -> aguardando {seconds:.1f}s em todas as threads...")


def http_get_with_retry(url: str, timeout: float = 15.0, max_retries: int = 4) -> bytes | None:
    """
    Fetches a URL with automatic retry, exponential backoff + jitter, and global
    coordination on HTTP 429 (Too Many Requests) or 5xx server errors.
    Returns None immediately on HTTP 404 (Not Found).
    """
    for attempt in range(max_retries + 1):
        wait_for_rate_limit()
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RetrogamerPOA-ArtSync/2.0",
                    "Accept": "image/png,image/*,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Normal miss when trying Boxart before Title/Snap fallback
                return None

            if e.code in (429, 503, 502, 500, 504, 408):
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if retry_after and retry_after.isdigit():
                    wait_s = float(retry_after) + random.uniform(0.5, 1.5)
                else:
                    base = 4.0 if e.code == 429 else 2.0
                    wait_s = base * (2 ** attempt) + random.uniform(0.3, 1.2)

                if e.code == 429 or e.code == 503:
                    trigger_global_cooldown(wait_s, f"HTTP {e.code} ({e.reason})")
                elif attempt < max_retries:
                    time.sleep(wait_s)

                if attempt < max_retries:
                    continue
            return None

        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt < max_retries:
                wait_s = 1.5 * (2 ** attempt) + random.uniform(0.2, 0.8)
                time.sleep(wait_s)
                continue
            safe_print(f"  [Erro Rede] Falha apos {max_retries + 1} tentativas em {url}: {e}")
            return None

    return None


def calc_rom_art_id(sector0: bytes) -> str:
    """
    Computes the exact 8-hex-character Artwork ID (XXXXXXXX) from the first
    512 bytes (Sector 0) of a ROM file, matching calcRomArtPath in MDOS.ptbr.BIN.
    """
    if len(sector0) < 512:
        sector0 = sector0.ljust(512, b"\x00")
    h = 0
    for w in struct.unpack(">256H", sector0[:512]):
        h = ((h << 5) | (h >> 27)) & 0xFFFFFFFF
        h ^= w
    return f"{h:08X}"


def deinterleave_smd_if_needed(rom_data: bytes) -> bytes:
    """
    Detects if a ROM is in interleaved Super Magic Drive (.smd) format
    and de-interleaves it into standard linear Mega Drive format.
    """
    if len(rom_data) >= 512 + 16384 and rom_data[8] == 0xAA and rom_data[9] == 0xBB:
        if rom_data[0x100:0x104] == b"SEGA":
            return rom_data
        body = rom_data[512:]
        out = bytearray(len(body))
        num_blocks = len(body) // 16384
        for b in range(num_blocks):
            blk = body[b * 16384 : (b + 1) * 16384]
            out[b * 16384 + 1 : (b + 1) * 16384 : 2] = blk[:8192]
            out[b * 16384 : (b + 1) * 16384 : 2] = blk[8192:16384]
        return bytes(out)
    return rom_data


def parse_sega_header(rom_data: bytes) -> dict:
    """
    Extracts metadata from the SEGA Mega Drive header at 0x100..0x1FF.
    """
    lin = deinterleave_smd_if_needed(rom_data)
    if len(lin) < 0x200:
        return {
            "is_sega": False,
            "console": "",
            "copyright": "",
            "title_jp": "",
            "title_us": "",
            "serial": "",
            "serial_core": "",
            "checksum": 0,
            "region": "",
        }
    hdr = lin[0x100:0x200]
    console = hdr[0x00:0x10].decode("latin1", errors="ignore").strip()
    copyright_s = hdr[0x10:0x20].decode("latin1", errors="ignore").strip()
    title_jp = re.sub(r"\s+", " ", hdr[0x20:0x50].decode("latin1", errors="ignore")).strip()
    title_us = re.sub(r"\s+", " ", hdr[0x50:0x80].decode("latin1", errors="ignore")).strip()
    serial_full = hdr[0x80:0x8E].decode("latin1", errors="ignore").strip()
    checksum = struct.unpack_from(">H", hdr, 0x8E)[0]
    region = hdr[0xF0:0xF3].decode("latin1", errors="ignore").strip()

    serial_core = ""
    m = re.search(r"([A-Z]{1,2}[-\s]?\d{4,8})", serial_full)
    if m:
        serial_core = m.group(1).replace(" ", "-")
    else:
        m2 = re.search(r"(\d{4,8})", serial_full)
        if m2:
            serial_core = m2.group(1)

    is_sega = ("SEGA" in console.upper()) or ("GENESIS" in console.upper()) or ("MEGA" in console.upper())
    return {
        "is_sega": is_sega,
        "console": console,
        "copyright": copyright_s,
        "title_jp": title_jp,
        "title_us": title_us,
        "serial": serial_full,
        "serial_core": serial_core,
        "checksum": checksum,
        "region": region,
    }


def normalize_title(s: str) -> str:
    s = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", s)
    s = re.sub(r"^\d+[\s\.\-_]+", "", s)
    s = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", s)
    s = s.upper()
    s = re.sub(r"\bTHE\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_cached_text(url: str, cache_name: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / cache_name
    if cache_file.exists() and cache_file.stat().st_size > 1000:
        return cache_file.read_text(encoding="utf-8", errors="ignore")
    safe_print(f"  [Web] Baixando catalogo {cache_name}...")
    raw = http_get_with_retry(url, timeout=25.0, max_retries=4)
    if not raw:
        raise RuntimeError(f"Falha ao baixar {url}")
    text = raw.decode("utf-8", errors="ignore")
    tmp_file = cache_file.with_suffix(".tmp")
    tmp_file.write_text(text, encoding="utf-8")
    tmp_file.replace(cache_file)
    return text


class LibretroDatabase:
    def __init__(self, sys_key="md"):
        self.sys_key = sys_key
        self.crc_to_name = {}
        self.serial_to_name = {}
        self.boxarts = []           # list of (exact_png_stem, norm_title, token_set)
        self.norm_to_stems = {}     # norm_title -> list of exact_png_stems
        self.token_index = {}       # token -> list of indices in self.boxarts
        self._load()

    def _load(self):
        try:
            dat_txt = fetch_cached_text(LIBRETRO_DAT_URLS[self.sys_key], f"libretro_{self.sys_key}.dat")
            for blk in dat_txt.split("game (")[1:]:
                m_name = re.search(r'^\s*name\s+"([^"]+)"', blk, re.MULTILINE)
                if not m_name:
                    continue
                gname = m_name.group(1)
                for m_crc in re.finditer(r"\bcrc\s+([0-9A-Fa-f]{8})\b", blk):
                    self.crc_to_name[m_crc.group(1).upper()] = gname
                for m_ser in re.finditer(r'serial\s+"([^"]+)"', blk):
                    ser_raw = m_ser.group(1).strip().upper()
                    self.serial_to_name.setdefault(ser_raw, gname)
                    ser_base = re.sub(r"-\d{2}$", "", ser_raw).replace(" ", "-")
                    self.serial_to_name.setdefault(ser_base, gname)
                    m_digits = re.search(r"([A-Z]*-?\d{4,8})", ser_base)
                    if m_digits:
                        self.serial_to_name.setdefault(m_digits.group(1), gname)
        except Exception as e:
            safe_print(f"  [Aviso] Nao foi possivel carregar DAT ({e})")

        try:
            idx_url = f"{LIBRETRO_THUMB_BASES[self.sys_key]}/Named_Boxarts/"
            html = fetch_cached_text(idx_url, f"boxarts_{self.sys_key}.html")
            for m in re.finditer(r'href="([^"]+\.png)"', html):
                href = urllib.parse.unquote(m.group(1))
                if "/" in href:
                    href = href.rsplit("/", 1)[-1]
                stem = href[:-4]
                norm = normalize_title(stem)
                if norm:
                    tokens = set(norm.split())
                    idx = len(self.boxarts)
                    self.boxarts.append((stem, norm, tokens))
                    self.norm_to_stems.setdefault(norm, []).append(stem)
                    for tok in tokens:
                        self.token_index.setdefault(tok, []).append(idx)
        except Exception as e:
            safe_print(f"  [Aviso] Nao foi possivel carregar indice de Boxarts ({e})")

    def _pick_best_region(self, stems: list[str]) -> str:
        def score(s: str) -> int:
            sc = 0
            if "(USA" in s or "(World" in s:
                sc += 30
            if "(Brazil" in s:
                sc += 25
            if "(Europe" in s:
                sc += 20
            if "(Japan" in s:
                sc += 10
            if "Beta" in s or "Proto" in s or "Sample" in s or "Demo" in s:
                sc -= 50
            return sc
        return sorted(stems, key=score, reverse=True)[0]

    def find_match(self, crc_hex: str, hdr: dict, file_stem: str) -> str | None:
        # 1. Exact CRC32 match in DAT
        if crc_hex in self.crc_to_name:
            cand = self.crc_to_name[crc_hex]
            norm = normalize_title(cand)
            if norm in self.norm_to_stems:
                if cand in self.norm_to_stems[norm]:
                    return cand
                return self._pick_best_region(self.norm_to_stems[norm])
            return cand

        # 2. SEGA Header Serial match in DAT
        for ser_candidate in (hdr.get("serial", ""), hdr.get("serial_core", "")):
            ser_clean = ser_candidate.strip().upper()
            if not ser_clean:
                continue
            for key in (ser_clean, re.sub(r"-\d{2}$", "", ser_clean)):
                if key in self.serial_to_name:
                    cand = self.serial_to_name[key]
                    norm = normalize_title(cand)
                    if norm in self.norm_to_stems:
                        return self._pick_best_region(self.norm_to_stems[norm])
                    return cand

        # 3. Exact normalized title match
        queries = []
        for q in (file_stem, hdr.get("title_us", ""), hdr.get("title_jp", "")):
            nq = normalize_title(q)
            if len(nq) >= 2 and nq not in queries:
                queries.append(nq)

        for nq in queries:
            if nq in self.norm_to_stems:
                return self._pick_best_region(self.norm_to_stems[nq])

        # 4. Fast inverted-index token & substring match
        best_stem = None
        best_score = 0.0
        for nq in queries:
            q_tokens = set(nq.split())
            if not q_tokens:
                continue
            candidate_indices = set()
            for tok in q_tokens:
                for idx in self.token_index.get(tok, ()):
                    candidate_indices.add(idx)

            for idx in candidate_indices:
                stem, b_norm, b_tokens = self.boxarts[idx]
                inter = len(q_tokens & b_tokens)
                if nq in b_norm or b_norm in nq:
                    overlap = inter / max(len(q_tokens), len(b_tokens))
                    if nq == b_norm:
                        overlap += 1.0
                    elif b_norm.startswith(nq) or nq.startswith(b_norm):
                        overlap += 0.35
                else:
                    overlap = inter / len(q_tokens | b_tokens)

                if overlap > best_score:
                    best_score = overlap
                    best_stem = stem

            if best_score >= 0.65:
                return best_stem

        if best_score >= 0.5:
            return best_stem
        return None


def download_artwork_png(sys_key: str, match_stem: str) -> Path | None:
    """
    Downloads the PNG artwork for `match_stem` from Libretro Thumbnails with retry/backoff,
    prioritizing Named_Boxarts -> Named_Titles -> Named_Snaps.
    """
    png_cache_dir = CACHE_DIR / "png" / sys_key
    png_cache_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r'[&\*/:`<>\?\\\|"]', "_", match_stem)
    local_png = png_cache_dir / f"{safe_stem}.png"
    if local_png.exists() and local_png.stat().st_size > 200:
        return local_png

    base = LIBRETRO_THUMB_BASES[sys_key]
    encoded_name = urllib.parse.quote(f"{safe_stem}.png")
    for folder in ("Named_Boxarts", "Named_Titles", "Named_Snaps"):
        url = f"{base}/{folder}/{encoded_name}"
        data = http_get_with_retry(url, timeout=15.0, max_retries=4)
        if data and data[:8] == b"\x89PNG\r\n\x1a\n":
            tmp_png = local_png.with_suffix(f".{threading.get_ident()}.tmp")
            tmp_png.write_bytes(data)
            tmp_png.replace(local_png)
            return local_png
    return None


def rgb24_to_md9(r: int, g: int, b: int) -> int:
    r3 = min(7, (r + 18) // 36)
    g3 = min(7, (g + 18) // 36)
    b3 = min(7, (b + 18) // 36)
    return ((b3 * 2) << 8) | ((g3 * 2) << 4) | (r3 * 2)


def md9_to_rgb24(cram: int) -> tuple[int, int, int]:
    r3 = (cram >> 1) & 7
    g3 = (cram >> 5) & 7
    b3 = (cram >> 9) & 7
    return (r3 * 36, g3 * 36, b3 * 36)


def convert_image_to_art(img_path: Path) -> bytes:
    """
    Converts an image into the 3,584-byte (7-sector) EverDrive-MD v3 .ART format:
      - Bytes 0x000..0x01F (32 bytes): 16 big-endian words of VDP Palette 3
      - Bytes 0x020..0xD9F (3,456 bytes): 108 8x8 4bpp VDP tiles (12x9 grid = 96x72 px)
      - Bytes 0xDA0..0xDFF (96 bytes): zero-padding to 3,584 bytes (7 sectors)
    """
    W, H = 96, 72
    orig_im = Image.open(img_path).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    im = orig_im.copy()

    px = im.load()
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            px[x, y] = md9_to_rgb24(rgb24_to_md9(r, g, b))

    q_im = im.quantize(colors=14, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    raw_pal = q_im.getpalette()[: 14 * 3]
    pal_rgb = []
    for i in range(14):
        if i * 3 + 2 < len(raw_pal):
            pal_rgb.append((raw_pal[i * 3], raw_pal[i * 3 + 1], raw_pal[i * 3 + 2]))
        else:
            pal_rgb.append((0, 0, 0))

    cram_words = [0x0000] * 16
    full_rgb_candidates = {15: (0, 0, 0)}
    for i, (r, g, b) in enumerate(pal_rgb):
        cram = rgb24_to_md9(r, g, b)
        cram_words[i + 1] = cram
        full_rgb_candidates[i + 1] = md9_to_rgb24(cram)

    bayer2 = ((0, 2), (3, 1))
    idx_grid = [[15 for _ in range(W)] for _ in range(H)]
    opx = orig_im.load()
    for y in range(H):
        for x in range(W):
            r, g, b = opx[x, y]
            d = (bayer2[y & 1][x & 1] - 1.5) * 5
            r = max(0, min(255, int(r + d)))
            g = max(0, min(255, int(g + d)))
            b = max(0, min(255, int(b + d)))
            best_idx = 15
            best_dist = 1 << 30
            for c_idx, (cr, cg, cb) in full_rgb_candidates.items():
                dr = r - cr
                dg = g - cg
                db = b - cb
                dist = dr * dr * 3 + dg * dg * 4 + db * db * 2
                if dist < best_dist:
                    best_dist = dist
                    best_idx = c_idx
            idx_grid[y][x] = best_idx

    out = bytearray()
    for w_val in cram_words:
        out.extend(struct.pack(">H", w_val))

    for ty in range(9):
        for tx in range(12):
            for ry in range(8):
                y = ty * 8 + ry
                row = idx_grid[y][tx * 8 : (tx + 1) * 8]
                for bx in range(0, 8, 2):
                    b_val = ((row[bx] & 0x0F) << 4) | (row[bx + 1] & 0x0F)
                    out.append(b_val)

    assert len(out) == 32 + 108 * 32
    out.extend(b"\x00" * (ART_FILE_SIZE - len(out)))
    return bytes(out)


def _process_single_rom(
    idx: int,
    total: int,
    rom_path: Path,
    art_id: str,
    art_file: Path,
    db_md: LibretroDatabase,
    db_sms: LibretroDatabase | None,
) -> str:
    """
    Worker function executed in parallel threads for each ROM that needs artwork.
    Returns status: 'ok', 'not_found', or 'error'.
    """
    try:
        raw = rom_path.read_bytes()
        hdr = parse_sega_header(raw)
        crc_hex = f"{zlib.crc32(deinterleave_smd_if_needed(raw)) & 0xFFFFFFFF:08X}"
        sys_key = "sms" if rom_path.suffix.lower() == ".sms" else "md"
        db = db_sms if (sys_key == "sms" and db_sms is not None) else db_md

        # 1. Check if user placed a local image next to the ROM (<rom_stem>.png / .jpg)
        local_img = None
        for ext in (".png", ".jpg", ".jpeg", ".bmp"):
            cand_img = rom_path.with_suffix(ext)
            if cand_img.exists():
                local_img = cand_img
                break

        match_label = "Imagem Local"
        if local_img is None:
            match_stem = db.find_match(crc_hex, hdr, rom_path.stem)
            if not match_stem:
                safe_print(
                    f"[{idx}/{total}] [!] Sem match: {rom_path.name} "
                    f"(US='{hdr['title_us']}', Serial='{hdr['serial']}')"
                )
                return "not_found"

            match_label = match_stem
            local_img = download_artwork_png(sys_key, match_stem)
            if local_img is None:
                safe_print(f"[{idx}/{total}] [!] PNG indisponivel na Libretro para '{match_stem}' ({rom_path.name})")
                return "not_found"

        art_bytes = convert_image_to_art(local_img)
        tmp_art = art_file.with_suffix(f".{threading.get_ident()}.tmp")
        tmp_art.write_bytes(art_bytes)
        tmp_art.replace(art_file)

        safe_print(f"[{idx}/{total}] [OK] {rom_path.name} -> {art_file.name} ('{match_label}')")
        return "ok"

    except Exception as e:
        safe_print(f"[{idx}/{total}] [ERRO] {rom_path.name}: {e}")
        return "error"


def sync_roms_directory(
    roms_dir: Path,
    out_art_dir: Path,
    workers: int = 8,
    force: bool = False,
):
    out_art_dir.mkdir(parents=True, exist_ok=True)
    rom_files = sorted(
        p for p in roms_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in ROM_EXTENSIONS
        and not p.name.upper().startswith(("MDOS", "BOOT-", "OS-V3", "OS38DUMP", "OSV3DUMP"))
    )

    if not rom_files:
        print(f"Nenhuma ROM encontrada em {roms_dir}")
        return

    # Fast pre-scan of first 512 bytes to skip existing .ART files and deduplicate by art_id
    pending_tasks = []
    skipped_existing = 0
    skipped_dup = 0
    seen_art_ids = set()
    has_sms = False

    print(f"Analisando {len(rom_files)} ROM(s) em '{roms_dir}'...")
    for rom_path in rom_files:
        try:
            with open(rom_path, "rb") as f:
                sector0 = f.read(512)
        except OSError:
            continue
        if len(sector0) < 512:
            continue

        art_id = calc_rom_art_id(sector0)
        art_file = out_art_dir / f"{art_id}.ART"

        if not force and art_file.exists() and art_file.stat().st_size == ART_FILE_SIZE:
            skipped_existing += 1
            continue

        if art_id in seen_art_ids:
            skipped_dup += 1
            continue
        seen_art_ids.add(art_id)

        if rom_path.suffix.lower() == ".sms":
            has_sms = True
        pending_tasks.append((rom_path, art_id, art_file))

    print(
        f"Resumo inicial: {len(rom_files)} total | "
        f"{skipped_existing} ja possuem .ART (puladas) | "
        f"{skipped_dup} duplicadas | "
        f"{len(pending_tasks)} para processar"
    )

    if not pending_tasks:
        print(f"Tudo atualizado! Nenhuma capa nova necessaria em {out_art_dir}")
        return

    print(f"Carregando catalogos Libretro e iniciando {workers} threads em paralelo...")
    db_md = LibretroDatabase("md")
    db_sms = LibretroDatabase("sms") if has_sms else None

    stats = {"ok": 0, "not_found": 0, "error": 0}
    total = len(pending_tasks)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [
            pool.submit(
                _process_single_rom,
                idx,
                total,
                rom_path,
                art_id,
                art_file,
                db_md,
                db_sms,
            )
            for idx, (rom_path, art_id, art_file) in enumerate(pending_tasks, 1)
        ]
        for fut in as_completed(futures):
            res = fut.result()
            stats[res] = stats.get(res, 0) + 1

    print(
        f"\nConcluido! Novas geradas: {stats['ok']} | "
        f"Puladas (ja existiam): {skipped_existing} | "
        f"Nao encontradas: {stats['not_found']} | "
        f"Erros: {stats['error']}\n"
        f"Pasta de saida: {out_art_dir}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Baixa Boxarts da Libretro em paralelo e converte para .ART do EverDrive-MD v3."
    )
    parser.add_argument("roms_dir", type=Path, help="Pasta raiz contendo suas ROMs (varre subpastas)")
    parser.add_argument(
        "out_art_dir",
        type=Path,
        nargs="?",
        default=None,
        help="Pasta de saida para os arquivos .ART (padrao: <roms_dir>/EDMD/ART)",
    )
    parser.add_argument(
        "-o", "--out",
        dest="out_opt",
        type=Path,
        default=None,
        help="Pasta de saida para os arquivos .ART (alternativa via flag)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=8,
        help="Numero de downloads/conversoes em paralelo (padrao: 8)",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Regerar arquivos .ART mesmo se ja existirem",
    )

    args = parser.parse_args()
    art_out = args.out_opt or args.out_art_dir or (args.roms_dir / "EDMD" / "ART")
    sync_roms_directory(args.roms_dir, art_out, workers=args.workers, force=args.force)
