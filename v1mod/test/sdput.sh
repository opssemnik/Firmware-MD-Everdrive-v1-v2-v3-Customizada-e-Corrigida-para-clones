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
