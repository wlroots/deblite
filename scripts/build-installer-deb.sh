#!/usr/bin/env bash
# Build the deblite-installer .deb from the current tree.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT=""
VERSION=""

usage() {
    cat <<EOF
usage: $0 [--output FILE] [--version VERSION]

Builds a small architecture-independent-ish .deb containing the installer,
its desktop entry and the scoped live-session sudoers rule.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            OUTPUT=$2
            shift 2
            ;;
        --version)
            VERSION=$2
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

if [ -z "$VERSION" ]; then
    if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
        VERSION="0.1.0+git$(git -C "$ROOT" rev-parse --short HEAD)"
    else
        VERSION="0.1.0"
    fi
fi
# dpkg versions must start with a digit and contain no slashes.
VERSION=$(printf '%s' "$VERSION" | sed 's/^v//; s/[^A-Za-z0-9.+:~-]/./g')

if [ -z "$OUTPUT" ]; then
    OUTPUT="$ROOT/out/deblite-installer_${VERSION}_amd64.deb"
fi
# live-build silently ignores local packages whose filename does not end in
# _amd64.deb or _all.deb. Refuse to produce a package it would skip.
case "$(basename "$OUTPUT")" in
    *_amd64.deb | *_all.deb) ;;
    *)
        echo "error: local package must be named *_amd64.deb or *_all.deb" >&2
        echo "       got: $(basename "$OUTPUT")" >&2
        exit 2
        ;;
esac

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

install -d "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/lib/deblite-installer"
cp -a "$ROOT/installer" "$STAGE/usr/lib/deblite-installer/"
find "$STAGE/usr/lib/deblite-installer" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$STAGE/usr/lib/deblite-installer" -type f -name '*.pyc' -delete

install -m 0755 "$ROOT/bin/deblite-installer" "$STAGE/usr/bin/deblite-installer"
cp -a "$ROOT/packaging/deblite-installer/usr/." "$STAGE/usr/"
cp -a "$ROOT/packaging/deblite-installer/etc" "$STAGE/etc"

chmod 0440 "$STAGE/etc/sudoers.d/deblite-installer"
chmod 0644 "$STAGE/etc/xdg/autostart/deblite-installer.desktop"
chmod 0644 "$STAGE/usr/share/applications/deblite-installer.desktop"
chmod 0644 "$STAGE/usr/share/icons/hicolor/scalable/apps/deblite-installer.svg"

cp "$ROOT/packaging/deblite-installer/DEBIAN/control" "$STAGE/DEBIAN/control"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGE/DEBIAN/control"

SIZE=$(du -sk --exclude=DEBIAN "$STAGE" | cut -f1)
sed -i "s/^Installed-Size:.*/Installed-Size: $SIZE/" "$STAGE/DEBIAN/control"

(
    cd "$STAGE"
    find . -path ./DEBIAN -prune -o -type f -print0 |
        sed -z 's|^\./||' |
        sort -z |
        xargs -0 -r md5sum > DEBIAN/md5sums
)

install -d "$(dirname "$OUTPUT")"
dpkg-deb --build --root-owner-group "$STAGE" "$OUTPUT" >/dev/null
echo "built $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
