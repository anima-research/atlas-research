#!/bin/sh
# Pull a frozen copy of one finalized Atlas release's creature texts to this machine.
# Read-only on the box; writes data/snapshot_rN.sqlite and its sha256 here.
# usage: ./snapshot.sh 15
set -eu
REV="$1"
# ATLAS_BOX       ssh address of the machine that holds the finalized releases
# ATLAS_RELEASES  directory on it that contains r1, r2, ... (each with FINALIZED)
BOX="${ATLAS_BOX:?set ATLAS_BOX to the ssh address of the corpus box}"
REL="${ATLAS_RELEASES:?set ATLAS_RELEASES to the releases directory on the box}/r${REV}"
HERE="$(cd "$(dirname "$0")" && pwd)"
scp -q "$HERE/export_on_box.py" "$BOX:/tmp/names_export_on_box.py"
ssh "$BOX" "python3 /tmp/names_export_on_box.py $REL /tmp/names_snapshot_r${REV}.sqlite && gzip -f /tmp/names_snapshot_r${REV}.sqlite"
scp -q "$BOX:/tmp/names_snapshot_r${REV}.sqlite.gz" "$HERE/data/"
ssh "$BOX" "rm -f /tmp/names_snapshot_r${REV}.sqlite.gz /tmp/names_export_on_box.py"
gunzip -f "$HERE/data/names_snapshot_r${REV}.sqlite.gz"
mv "$HERE/data/names_snapshot_r${REV}.sqlite" "$HERE/data/snapshot_r${REV}.sqlite"
shasum -a 256 "$HERE/data/snapshot_r${REV}.sqlite" | tee "$HERE/data/snapshot_r${REV}.sha256"
