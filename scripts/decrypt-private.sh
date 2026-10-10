#!/usr/bin/env bash
# Decrypt bench/private.tar.age into bench/private/.
# Key source: $AGE_SECRET_KEY (CI secret) or .secrets/age-key.txt (local).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p bench/private
if [ -n "${AGE_SECRET_KEY:-}" ]; then
  age -d -i <(printf '%s\n' "$AGE_SECRET_KEY") bench/private.tar.age | tar -C bench/private -xzf -
else
  age -d -i .secrets/age-key.txt bench/private.tar.age | tar -C bench/private -xzf -
fi
echo "decrypted $(ls bench/private | wc -l) files into bench/private/"
