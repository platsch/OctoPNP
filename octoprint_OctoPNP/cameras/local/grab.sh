#! /bin/bash -e

ROOT=$(readlink -f "$(dirname "$0")")

streamer -s "[640x480]" -o "$ROOT"/head.jpeg

convert "$ROOT"/head.jpeg  "$ROOT"/../head.jpeg
convert "$ROOT"/head.jpeg "$ROOT"/../bed.jpeg
