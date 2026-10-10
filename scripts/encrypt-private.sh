#!/usr/bin/env bash
# Encrypt bench/private/ (plaintext, gitignored) into bench/private.tar.age (committed).
# Only the public recipient key is needed, so anyone with repo access can add questions.
set -euo pipefail
cd "$(dirname "$0")/.."
test -d bench/private || { echo "bench/private/ not found" >&2; exit 1; }
tar -C bench/private -czf - . | age -r "$(cat bench/age-recipient.txt)" -o bench/private.tar.age
echo "wrote bench/private.tar.age ($(ls bench/private | wc -l) files)"
