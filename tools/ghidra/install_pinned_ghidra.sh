#!/usr/bin/env bash
# Install the pinned official Ghidra 12.2 PUBLIC distribution on CI Linux.
# Refuse both modified and tampered artifacts; never run unverified downloads.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash install_pinned_ghidra.sh CACHE_DIR INSTALL_DIR" >&2
  exit 2
fi

cache_dir="$1"
install_dir="$2"
name="ghidra_12.2_PUBLIC_20261016.zip"
url="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.2_build/$name"
expected="2c2cd776db3c1f6a097ba418922378ac3649cadd5e844a6f5f088ae628a7be67"
archive="$cache_dir/$name"
mkdir -p "$cache_dir" "$install_dir"

if [[ ! -s "$archive" ]]; then
  curl --fail --location --silent --show-error --retry 3 \
    --retry-all-errors --output "$archive" "$url"
fi
if ! printf '%s  %s\n' "$expected" "$archive" | sha256sum --check >&2; then
  rm -f "$archive"
  echo "Ghidra 12.2 SHA256 mismatch. Refusing to execute." >&2
  exit 1
fi

if [[ ! -f "$install_dir/ghidra_12.2_PUBLIC/support/analyzeHeadless" ]]; then
  unzip -q "$archive" -d "$install_dir"
fi
home="$install_dir/ghidra_12.2_PUBLIC"
if [[ ! -f "$home/support/analyzeHeadless" ]]; then
  echo "Verified Ghidra ZIP did not contain expected headless analyzer" >&2
  exit 1
fi
chmod u+x "$home/support/analyzeHeadless"
printf '%s\n' "$home"
