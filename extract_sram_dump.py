import sys
import os
import struct
import hashlib

def rol32(val, n=1):
    return ((val << n) & 0xFFFFFFFF) | (val >> (32 - n))

def calc_crc_longs(buf):
    crc = 0
    for (w,) in struct.iter_unpack('>I', buf):
        crc = (rol32(crc, 1) + w) & 0xFFFFFFFF
    return crc

def main():
    srm_path = sys.argv[1] if len(sys.argv) > 1 else 'OSV3DUMP.SRM'
    if not os.path.exists(srm_path):
        print(f"Usage: python extract_sram_dump.py <path-to-OSV3DUMP.SRM>")
        sys.exit(1)

    with open(srm_path, 'rb') as f:
        srm = f.read()

    if len(srm) == 65536:
        # EverDrive-MD v3 .SRM files store the 32,768 SRAM bytes in the odd byte of each 16-bit word
        mdos_32k = bytes(srm[1::2])
    elif len(srm) == 32768:
        mdos_32k = srm
    else:
        raise ValueError(f"Unexpected SRM size: {len(srm)} bytes (expected 65536 or 32768)")

    # Pad to 128 KB (131,072 bytes) with 0x00 to match MDOS.patched.BIN / MDOS.stock.BIN format
    mdos_128k = mdos_32k + (b'\x00' * (131072 - len(mdos_32k)))
    out_mdos = os.path.join(os.path.dirname(srm_path) or '.', 'MDOS-V3.BIN')
    with open(out_mdos, 'wb') as f:
        f.write(mdos_128k)

    out_bios = os.path.join(os.path.dirname(srm_path) or '.', 'BIOS-V31.BIN')
    with open(out_bios, 'wb') as f:
        f.write(mdos_32k[0x0020:0x0820])

    print(f"Extracted {out_mdos} (131,072 bytes, SHA-256: {hashlib.sha256(mdos_128k).hexdigest()})")
    print(f"Extracted {out_bios} (2,048 bytes,  SHA-256: {hashlib.sha256(mdos_32k[0x20:0x820]).hexdigest()})")
    print(f"  Full 32K/128K Rolling CRC : 0x{calc_crc_longs(mdos_32k):08X}")
    print(f"  HDR  (0x0000..0x001F) CRC : 0x{calc_crc_longs(mdos_32k[:0x20]):08X}")
    print(f"  BIOS (0x0020..0x081F) CRC : 0x{calc_crc_longs(mdos_32k[0x20:0x820]):08X}")
    print(f"  OS   (0x0820..0x7FFF) CRC : 0x{calc_crc_longs(mdos_32k[0x820:0x8000]):08X}")

    patched_path = os.path.join(os.path.dirname(__file__), 'MDOS.patched.BIN')
    if os.path.exists(patched_path):
        with open(patched_path, 'rb') as f:
            p = f.read(0x8000)
        hdr_diffs = sum(1 for a, b in zip(mdos_32k[:0x20], p[:0x20]) if a != b)
        bios_diffs = sum(1 for a, b in zip(mdos_32k[0x20:0x820], p[0x20:0x820]) if a != b)
        os_diffs = sum(1 for a, b in zip(mdos_32k[0x820:], p[0x820:]) if a != b)
        print(f"\nComparison vs MDOS.patched.BIN:")
        print(f"  HDR  (0x0000..0x001F) diffs: {hdr_diffs}")
        print(f"  BIOS (0x0020..0x081F) diffs: {bios_diffs} (Boot ROM BIOS 3.1 vs file BIOS 3.0)")
        print(f"  OS   (0x0820..0x7FFF) diffs: {os_diffs}")

if __name__ == '__main__':
    main()
