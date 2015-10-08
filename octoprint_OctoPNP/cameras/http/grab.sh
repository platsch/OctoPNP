#! /bin/bash -e

ROOT=$(readlink -f $(dirname $0))

wget http://192.168.100.165/liveimg.cgi $ROOT/head.jpg
wget http://192.168.100.167/liveimg.cgi $ROOT/bed.jpg

convert $ROOT/head.jpg -rotate 90 $ROOT/../head.png
convert $ROOT/bed.jpg $ROOT/../bed.png
