set -e
export PATH=$HOME/fat/usr/sbin:$HOME/fat/usr/bin:$PATH MTOOLS_SKIP_CHECK=1
cd "$(dirname "$0")/sd"
rm -f sd.img; mkfs.vfat -F 32 -C sd.img 65536 >/dev/null
cd stage && mcopy -s -i ../sd.img ./* ::/ && cd ..
mdir -i sd.img -/ ::/ | grep -vE '^\s*$' | head -40
