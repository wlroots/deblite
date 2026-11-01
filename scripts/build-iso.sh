#!/usr/bin/env bash
# Build one DebLite ISO with live-build.
#
# Usage:
#   sudo ./scripts/build-iso.sh kde
#   sudo ./scripts/build-iso.sh cinnamon --compress xz --release
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

FLAVOR=""
COMPRESS="zstd"
RELEASE=0
CLEAN=1
DEBIAN_VERSION="trixie"
OUT="$ROOT/out"
BUILD=""

usage() {
    cat <<EOF
usage: $0 FLAVOR [options]

Flavors: kde, gnome, xfce, cinnamon, gnome-backports

Options:
  --compress zstd|xz     squashfs compression (default: zstd)
  --release              release build: xz + 2 GiB GitHub guard
  --debian-version VER   informational Debian point release (default: trixie)
  --out DIR              output directory (default: ./out)
  --build DIR            build directory (default: ./build/FLAVOR)
  --no-clean             keep an existing build directory
  -h, --help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --compress)
            COMPRESS=$2
            shift 2
            ;;
        --release)
            RELEASE=1
            COMPRESS="xz"
            shift
            ;;
        --debian-version)
            DEBIAN_VERSION=$2
            shift 2
            ;;
        --out)
            OUT=$2
            shift 2
            ;;
        --build)
            BUILD=$2
            shift 2
            ;;
        --no-clean)
            CLEAN=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [ -n "$FLAVOR" ]; then
                echo "error: more than one flavor given" >&2
                exit 2
            fi
            FLAVOR=$1
            shift
            ;;
    esac
done

if [ -z "$FLAVOR" ]; then
    usage >&2
    exit 2
fi

if [ ! -d "$ROOT/config/flavors/$FLAVOR" ]; then
    echo "error: unknown flavor '$FLAVOR'" >&2
    exit 2
fi
if [ "$FLAVOR" = "gnome-backports" ] && [ "${DEBLITE_EXPERIMENTAL:-0}" != "1" ]; then
    echo "error: gnome-backports is scaffolded but not buildable yet." >&2
    echo "       See config/flavors/gnome-backports/README.md" >&2
    exit 2
fi

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "live-build needs root; re-running with sudo" >&2
    exec sudo -E -- "$0" "$@"
fi

if ! command -v lb >/dev/null 2>&1; then
    echo "error: live-build is not installed (apt-get install live-build)" >&2
    exit 1
fi

BUILD=${BUILD:-$ROOT/build/$FLAVOR}
mkdir -p "$OUT"

if [ "$CLEAN" = "1" ]; then
    rm -rf "$BUILD"
fi
mkdir -p "$BUILD"

echo "==> configuring live-build for $FLAVOR ($COMPRESS)"
cd "$BUILD"
lb config \
    --distribution trixie \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --archive-areas "main contrib non-free non-free-firmware" \
    --apt-recommends false \
    --apt-options "--yes --no-install-recommends --no-install-suggests" \
    --apt-indices false \
    --debootstrap-options "--variant=minbase" \
    --bootloaders "syslinux grub-efi" \
    --uefi-secure-boot auto \
    --debian-installer none \
    --memtest none \
    --firmware-chroot false \
    --firmware-binary false \
    --bootappend-live "boot=live components quiet" \
    --chroot-squashfs-compression-type "$COMPRESS" \
    --image-name "deblite-13-$FLAVOR" \
    --iso-application "DebLite" \
    --iso-preparer "DebLite build system" \
    --iso-publisher "DebLite Project" \
    --iso-volume "DEBLITE_${FLAVOR^^}" \
    --mirror-bootstrap "http://deb.debian.org/debian/" \
    --mirror-chroot "http://deb.debian.org/debian/" \
    --mirror-binary "http://deb.debian.org/debian/" \
    --zsync false

echo "==> copying common and $FLAVOR configuration"
cp -a "$ROOT/config/common/." "$BUILD/config/"
cp -a "$ROOT/config/flavors/$FLAVOR/." "$BUILD/config/"
mkdir -p "$BUILD/config/packages.chroot"

echo "==> building deblite-installer.deb"
"$ROOT/scripts/build-installer-deb.sh" \
    --output "$BUILD/config/packages.chroot/deblite-installer_amd64.deb"

echo "==> fetching vendored packages"
"$ROOT/scripts/fetch-vendor-debs.sh" \
    --flavor "$FLAVOR" \
    --output "$BUILD/config/packages.chroot"

echo "==> lb build (this takes a while)"
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C
set +e
lb build 2>&1 | tee "$BUILD/build.log"
status=${PIPESTATUS[0]}
set -e
if [ "$status" -ne 0 ]; then
    echo "error: lb build failed (see $BUILD/build.log)" >&2
    exit "$status"
fi

ISO=$(find "$BUILD" -maxdepth 1 -type f -name '*.iso' -print -quit)
if [ -z "$ISO" ]; then
    echo "error: lb build finished but no ISO was produced" >&2
    exit 1
fi

NAME="deblite-13-$FLAVOR-amd64.iso"
DEST="$OUT/$NAME"
mv "$ISO" "$DEST"

echo "==> verifying $NAME"
"$ROOT/scripts/verify-iso.sh" "$DEST"
"$ROOT/scripts/audit-bloat.sh" "$DEST"

SIZE=$(stat -c %s "$DEST")
GITHUB_LIMIT=$((2 * 1024 * 1024 * 1024))
if [ "$RELEASE" = "1" ] && [ "$SIZE" -ge "$GITHUB_LIMIT" ]; then
    echo "error: $NAME is $(numfmt --to=iec "$SIZE"), at or above GitHub's 2 GiB asset limit." >&2
    echo "       Split the ISO or use external storage before publishing." >&2
    exit 1
fi

(
    cd "$OUT"
    sha256sum "$NAME" >"$NAME.sha256"
)

cat >"$OUT/$NAME.manifest.json" <<EOF
{
  "flavor": "$FLAVOR",
  "debian_version": "$DEBIAN_VERSION",
  "compression": "$COMPRESS",
  "git_sha": "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)",
  "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "iso_bytes": $SIZE,
  "iso_sha256": "$(cut -d' ' -f1 "$OUT/$NAME.sha256")"
}
EOF

echo
echo "built: $DEST ($(numfmt --to=iec "$SIZE"))"
echo "sha256: $(cut -d' ' -f1 "$OUT/$NAME.sha256")"
