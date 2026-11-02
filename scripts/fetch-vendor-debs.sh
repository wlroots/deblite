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

check_sha() {
    file=$1
    expected=$2
    if [ -z "$expected" ]; then
        return 0
    fi
    actual=$(sha256sum "$file" | cut -d' ' -f1)
    if [ "$actual" != "$expected" ]; then
        echo "error: checksum mismatch for $file" >&2
        echo "       expected $expected" >&2
        echo "       got      $actual" >&2
        exit 1
    fi
}

# mint-themes ships a single .deb inside packages.tar.gz. Pin both the release
# and the expected package version so a moved tag fails loudly instead of
# silently changing the ISO.
THEMES_VERSION=${MINT_THEMES_VERSION:-2.4.3}
THEMES_URL=${MINT_THEMES_URL:-https://github.com/linuxmint/mint-themes/releases/download/master.lmde7/packages.tar.gz}
echo "downloading $THEMES_URL"
curl -fL --retry 3 --connect-timeout 10 --max-time 180 -o "$TMP/packages.tar.gz" "$THEMES_URL"
tar -xzf "$TMP/packages.tar.gz" -C "$TMP"

DEB=$(find "$TMP" -type f -name 'mint-themes_*_all.deb' -print -quit)
if [ -z "$DEB" ]; then
    echo "error: mint-themes .deb not found in archive" >&2
    exit 1
fi
found=$(dpkg-deb -f "$DEB" Version)
if [ "$found" != "$THEMES_VERSION" ]; then
    echo "error: expected mint-themes $THEMES_VERSION, archive has $found" >&2
    exit 1
fi
check_sha "$DEB" "${MINT_THEMES_SHA256:-ea4239ee723e84acd11d233f51099fe28d99dcc984413018a8a4678caefae170}"
cp "$DEB" "$OUTPUT/"

# mint-themes depends on mint-x-icons, which Debian does not package. Pull the
# architecture-independent icons from the Linux Mint repository. The host's
# TLS endpoint is flaky from some networks, so fall back to HTTP.
X_ICONS_VERSION=${MINT_X_ICONS_VERSION:-1.8.1}
X_ICONS_PATH="pool/main/m/mint-x-icons/mint-x-icons_${X_ICONS_VERSION}_all.deb"
X_ICONS_URL=${MINT_X_ICONS_URL:-https://packages.linuxmint.com/$X_ICONS_PATH}
echo "downloading $X_ICONS_URL"
if ! curl -fL --retry 3 --connect-timeout 10 --max-time 180 -o "$OUTPUT/mint-x-icons_${X_ICONS_VERSION}_all.deb" "$X_ICONS_URL"; then
    echo "https failed; retrying over http"
    curl -fL --retry 3 --connect-timeout 10 --max-time 180 -o "$OUTPUT/mint-x-icons_${X_ICONS_VERSION}_all.deb" \
        "http://packages.linuxmint.com/$X_ICONS_PATH"
fi
check_sha "$OUTPUT/mint-x-icons_${X_ICONS_VERSION}_all.deb" \
    "${MINT_X_ICONS_SHA256:-53304c1616ff2af50d1c5e146d740610f417497ff4c6919087bda8774bdbb6e7}"

for deb in "$OUTPUT"/mint-themes_*_all.deb "$OUTPUT"/mint-x-icons_*_all.deb; do
    dpkg-deb --info "$deb" >/dev/null
    echo "vendored $(basename "$deb")"
done
