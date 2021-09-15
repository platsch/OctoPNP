#! /bin/bash -e

ROOT=$(readlink -f "$(dirname "$0")")

cp "$ROOT"/head.png  "$ROOT"/../head.png
cp "$ROOT"/head.png "$ROOT"/../bed.png
