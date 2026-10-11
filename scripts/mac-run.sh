#!/usr/bin/env bash
# Run the local (Ollama) models on the Mac test machine and publish their scores.
#   scripts/mac-run.sh                      # every model with status "local"
#   scripts/mac-run.sh gemma-3-4b-q4-mac    # just these (comma-separated)
# Needs: Ollama running, Docker running (Docker Desktop or Colima), age, gh logged in,
# and the hidden-set key in .secrets/age-key.txt. Only scores and public-question outputs are committed.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull -q --rebase
scripts/decrypt-private.sh
python3 -m runner selfcheck          # also proves the Docker sandbox works before hours of generation

caffeinate -i python3 -m runner local ${1:+--models "$1"}

rm -rf bench/private
git add results/scores results/outputs bench/models.json
if git diff --cached --quiet; then
  echo "nothing new to publish"
else
  git commit -q -m "bench: local Mac results $(date -u +%F)"
  git pull -q --rebase && git push -q
  echo "pushed — GitHub Actions will rebuild the site in a few minutes"
fi
