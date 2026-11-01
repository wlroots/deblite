#!/usr/bin/env bash
# Fail if a built ISO contains packages DebLite explicitly excludes.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/lib.sh
. "$ROOT/scripts/lib.sh"

ISO=${1:-}
if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
    echo "usage: $0 path/to/deblite.iso" >&2
    exit 2
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if ! extract_squashfs "$ISO" "$TMP/filesystem.squashfs"; then
    echo "FAIL: cannot extract squashfs" >&2
    exit 1
fi

unsquashfs -cat "$TMP/filesystem.squashfs" var/lib/dpkg/status >"$TMP/status" 2>/dev/null || true
if [ ! -s "$TMP/status" ]; then
    echo "FAIL: cannot read dpkg status from squashfs" >&2
    exit 1
fi

grep '^Package:' "$TMP/status" | awk '{print $2}' | sort -u >"$TMP/packages.txt"
echo "packages installed: $(wc -l <"$TMP/packages.txt")"

DENY=(
    libreoffice
    libreoffice-core
    libreoffice-common
    thunderbird
    evolution
    evolution-data-server
    gnome-software
    gnome-maps
    gnome-weather
    gnome-contacts
    gnome-calendar
    gnome-clocks
    simple-scan
    orca
    gnome-snapshot
    totem
    cheese
    rhythmbox
    transmission-gtk
    gnome-games
    aisleriot
    gnome-mines
    gnome-sudoku
    gnome-mahjongg
    quadrapassel
    five-or-more
    four-in-a-row
    hitori
    iagno
    lightsoff
    swell-foop
    tali
    gnome-2048
    gnome-nibbles
    gnome-robots
    gnome-taquin
    gnome-tetravex
    xfce4-goodies
    kde-applications
    kde-full
    kde-standard
)

found=0
for pkg in "${DENY[@]}"; do
    if grep -qxF "$pkg" "$TMP/packages.txt"; then
        echo "BLOCKED: $pkg" >&2
        found=1
    fi
done

# Catch any libreoffice-* flavour not listed above.
if grep -q '^libreoffice-' "$TMP/packages.txt"; then
    echo "BLOCKED: libreoffice-* packages" >&2
    grep '^libreoffice-' "$TMP/packages.txt" >&2 || true
    found=1
fi

if [ "$found" -ne 0 ]; then
    if [ "${DEBLITE_ALLOW_BLOAT:-0}" = "1" ]; then
        echo "audit-bloat: warnings only (DEBLITE_ALLOW_BLOAT=1)"
        exit 0
    fi
    echo "audit-bloat: FAILED" >&2
    exit 1
fi

echo "audit-bloat: OK"
