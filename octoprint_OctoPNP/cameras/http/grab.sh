#! /bin/bash -e

ROOT=$(readlink -f "$(dirname "$0")")

wget http://192.168.100.165/liveimg.cgi -O "$ROOT"/head.jpg
wget http://192.168.100.167/liveimg.cgi -O "$ROOT"/bed.jpg

convert "$ROOT"/head.jpg -rotate 90 "$ROOT"/../head.jpg
convert "$ROOT"/bed.jpg "$ROOT"/../bed.jpg
