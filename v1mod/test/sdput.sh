# Test SD images (run in WSL after building): /EDMD/MDOS.BIN = the current v3 build (the overlay screens
# are read from it) and /EDMD/V1EXT.BIN = the v1 flash extension, on sd.img and sdb.img; sdw.img = sd.img
# + the sd/EDMD banner and wallpaper; sdn.img = sd.img without MDOS.BIN.
set -e
export PATH=$HOME/fat/usr/sbin:$HOME/fat/usr/bin:$PATH MTOOLS_SKIP_CHECK=1
R=$(cd "$(dirname "$0")/../.." && pwd)
cd "$(dirname "$0")/sd"
for img in sd.img sdb.img; do
    [ -f $img ] && mcopy -o -i $img "$R/MDOS.ptbr.BIN" ::/EDMD/MDOS.BIN
    [ -f $img ] && mcopy -o -i $img "$R/V1EXT.BIN" ::/EDMD/V1EXT.BIN
done
cp sd.img sdw.img
mcopy -o -i sdw.img "$R/sd/EDMD/BANNER.ART" ::/EDMD/BANNER.ART
mcopy -o -i sdw.img "$R/sd/EDMD/WALL.ART" ::/EDMD/WALL.ART
cp sd.img sdn.img && mdel -i sdn.img ::/EDMD/MDOS.BIN
# t_loader.py: sdx.img = sd.img without V1EXT.BIN, sdo.img = a V1EXT.BIN made for another loader (abi 9)
cp sd.img sdx.img && mdel -i sdx.img ::/EDMD/V1EXT.BIN
head -c 2560 /dev/zero | tr '\0' 'x' > /tmp/old.bin && printf 'PTBX\x00\x00\x00\x09' | dd of=/tmp/old.bin conv=notrunc 2>/dev/null
cp sd.img sdo.img && mcopy -o -i sdo.img /tmp/old.bin ::/EDMD/V1EXT.BIN
# sdm.img = sd.img + the Maddrugamers theme (temas/), banner with theme colours
cp sd.img sdm.img
mcopy -o -i sdm.img "$R/temas/maddrugamers/EDMD/BANNER.ART" ::/EDMD/BANNER.ART
mcopy -o -i sdm.img "$R/temas/maddrugamers/EDMD/WALL.ART" ::/EDMD/WALL.ART
