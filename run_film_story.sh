#!/usr/bin/env bash
# Reproduce the film's story (seed 132): runs the simulation, writes story/ and maps/,
# then checks that the result is identical to the published copy in samples/story_seed132/.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

mkdir -p story maps
# The export layer reads two hand-written display files (city names and era names) for this story.
cp samples/story_seed132/names_v2.json samples/story_seed132/periods_v2.json story/

"$PY" sim.py export --seed 132
"$PY" quick_check.py | tail -n 12
echo
echo "Done. Open story/key_moments.md, story/log.txt and maps/*.svg"
