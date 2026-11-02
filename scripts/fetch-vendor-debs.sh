#!/usr/bin/env bash
# Download packages that are not in Debian and place them in packages.chroot.
#
# Currently only the Cinnamon edition needs this: Debian ships mint-y-icons but
# not mint-themes, so the pinned Mint release is vendored as a .deb.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FLAVOR=""
OUTPUT="$ROOT/out/vendor"

usage() {
    cat <<EOF
usage: $0 --flavor FLAVOR [--output DIR]

Downloads third-party .deb files for FLAVOR into DIR.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --flavor)
            FLAVOR=$2
            shift 2
            ;;
        --output)
            OUTPUT=$2
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$FLAVOR" ]; then
    echo "error: --flavor is required" >&2
    exit 2
fi

install -d "$OUTPUT"

if [ "$FLAVOR" != "cinnamon" ]; then
    echo "no vendored packages needed for $FLAVOR"
    exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# mint-themes ships a single .deb inside packages.tar.gz.
THEMES_URL=${MINT_THEMES_URL:-https://github.com/linuxmint/mint-themes/releases/latest/download/packages.tar.gz}
echo "downloading $THEMES_URL"
curl -fL --retry 3 -o "$TMP/packages.tar.gz" "$THEMES_URL"
tar -xzf "$TMP/packages.tar.gz" -C "$TMP"

DEB=$(find "$TMP" -type f -name 'mint-themes_*_all.deb' -print -quit)
if [ -z "$DEB" ]; then
    echo "error: mint-themes .deb not found in archive" >&2
    exit 1
fi
cp "$DEB" "$OUTPUT/"

# mint-themes depends on mint-x-icons, which Debian does not package. Pull the
# architecture-independent icons from the Linux Mint repository.
X_ICONS_VERSION=${MINT_X_ICONS_VERSION:-1.8.1}
X_ICONS_URL=${MINT_X_ICONS_URL:-http://packages.linuxmint.com/pool/main/m/mint-x-icons/mint-x-icons_${X_ICONS_VERSION}_all.deb}
echo "downloading $X_ICONS_URL"
curl -fL --retry 3 -o "$OUTPUT/mint-x-icons_${X_ICONS_VERSION}_all.deb" "$X_ICONS_URL"

for deb in "$OUTPUT"/mint-themes_*_all.deb "$OUTPUT"/mint-x-icons_*_all.deb; do
    dpkg-deb --info "$deb" >/dev/null
    echo "vendored $(basename "$deb")"
done
