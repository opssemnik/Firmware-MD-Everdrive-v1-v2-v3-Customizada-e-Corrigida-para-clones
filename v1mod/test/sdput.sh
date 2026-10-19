# v3 tests: copies the current build to /EDMD/MDOS.BIN on the test SD images (sd/sd.img, sd/sdb.img)
# - the overlay screens are read from that file - and makes sd/sdn.img without it. Run in WSL.
set -e
export PATH=$HOME/fat/usr/sbin:$HOME/fat/usr/bin:$PATH MTOOLS_SKIP_CHECK=1
cd "$(dirname "$0")/sd"
for img in sd.img sdb.img; do
    [ -f $img ] && mcopy -o -i $img ../../../MDOS.ptbr.BIN ::/EDMD/MDOS.BIN
done
cp sd.img sdn.img && mdel -i sdn.img ::/EDMD/MDOS.BIN
