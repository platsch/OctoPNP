#! /bin/bash -e

# setup the pylon environment
source /opt/pylon5/bin/pylon-setup-env.sh /opt/pylon5

#disable usb cameras to avoid conflict between on board built-in Webcam or USB2 Web Cam and Pylon4Linux V4.
export PYLON_USE_TL=BaslerGigE

ROOT=$(readlink -f "$(dirname "$0")")

pwd
#start the image grabber
"$ROOT"/grab "$ROOT" bed

#convert $ROOT/head.tiff -rotate 270 $ROOT/../head.png
#rm $ROOT/head.tiff
convert "$ROOT"/bed.tiff -rotate 270 "$ROOT"/../bed.png
