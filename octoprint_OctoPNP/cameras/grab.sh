#! /bin/bash -e

ROOT=$(readlink -f $(dirname $0))
$ROOT/pylon/grab.sh
$ROOT/http/grab.sh

