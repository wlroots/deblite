#!/usr/bin/env bash
# Download the pinned deblite-installer .deb from its GitHub Release and
# verify it against the release's SHA256SUMS asset.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT=""
REPO_OVERRIDE=""
VERSION_OVERRIDE=""
DEB_OVERRIDE=""

usage() {
    cat <<EOF
usage: $0 [--output FILE] [--deb FILE] [--repo OWNER/NAME] [--version VERSION]

Fetches deblite-installer_<version>_amd64.deb from a GitHub Release. The
release is pinned by installer-release.env; command-line flags and the
DEBLITE_INSTALLER_* environment variables override it.

  --deb FILE   use a local .deb instead of downloading one

DEBLITE_INSTALLER_BASE_URL overrides the release URL, which is useful for
mirrors and for exercising the download/checksum path in tests.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            OUTPUT=$2
            shift 2
            ;;
        --deb)
            DEB_OVERRIDE=$2
            shift 2
            ;;
        --repo)
            REPO_OVERRIDE=$2
            shift 2
            ;;
        --version)
            VERSION_OVERRIDE=$2
            shift 2
            ;;
        -h | --help)
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

# shellcheck source=/dev/null
[ -f "$ROOT/installer-release.env" ] && . "$ROOT/installer-release.env"

VERSION=${VERSION_OVERRIDE:-${DEBLITE_INSTALLER_VERSION:-0.1.0}}
REPO=${REPO_OVERRIDE:-${DEBLITE_INSTALLER_REPO:-}}
DEB_OVERRIDE=${DEB_OVERRIDE:-${DEBLITE_INSTALLER_DEB:-}}

if [ -z "$REPO" ]; then
    origin=$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)
    case "$origin" in
        https://github.com/*/*)
            owner=${origin#https://github.com/}
            owner=${owner%%/*}
            ;;
        git@github.com:*/*)
            owner=${origin#git@github.com:}
            owner=${owner%%/*}
            ;;
        *)
            owner=""
            ;;
    esac
    if [ -n "$owner" ]; then
        REPO="$owner/deblite-installer"
    else
        # Fallback used before the repository has a remote. Override it with
        # DEBLITE_INSTALLER_REPO or --repo.
        REPO="deblite/deblite-installer"
    fi
fi

NAME="deblite-installer_${VERSION}_amd64.deb"
if [ -z "$OUTPUT" ]; then
    OUTPUT="$ROOT/out/$NAME"
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
DEB="$TMP/$NAME"

if [ -n "$DEB_OVERRIDE" ]; then
    echo "==> using local installer: $DEB_OVERRIDE"
    cp "$DEB_OVERRIDE" "$DEB"
else
    BASE=${DEBLITE_INSTALLER_BASE_URL:-https://github.com/$REPO/releases/download/installer-v${VERSION}}
    BASE=${BASE%/}
    echo "==> downloading $BASE/$NAME"
    curl -fL --retry 3 --connect-timeout 10 --max-time 300 -o "$DEB" "$BASE/$NAME"

    if [ -n "${DEBLITE_INSTALLER_SHA256:-}" ]; then
        printf '%s  %s\n' "$DEBLITE_INSTALLER_SHA256" "$NAME" |
            (cd "$TMP" && sha256sum -c -)
    else
        curl -fL --retry 3 --connect-timeout 10 --max-time 120 \
            -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS"
        expected=$(awk -v name="$NAME" '$2 == name { print $1 }' "$TMP/SHA256SUMS")
        if [ -z "$expected" ]; then
            echo "error: $NAME is not listed in the release's SHA256SUMS" >&2
            exit 1
        fi
        actual=$(sha256sum "$DEB" | cut -d' ' -f1)
        if [ "$actual" != "$expected" ]; then
            echo "error: checksum mismatch for $NAME" >&2
            echo "       expected $expected" >&2
            echo "       got      $actual" >&2
            exit 1
        fi
    fi
fi

dpkg-deb --info "$DEB" >/dev/null
mkdir -p "$(dirname "$OUTPUT")"
cp "$DEB" "$OUTPUT"

echo "installer: $(dpkg-deb -f "$DEB" Package) $(dpkg-deb -f "$DEB" Version)"
echo "saved:     $OUTPUT"
