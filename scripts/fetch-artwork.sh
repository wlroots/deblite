#!/usr/bin/env bash
# Download the pinned deblite-artwork tarball from its GitHub Release, verify
# it against the release's SHA256SUMS asset, and extract it.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT=""
REPO_OVERRIDE=""
VERSION_OVERRIDE=""
ARCHIVE_OVERRIDE=""

usage() {
    cat <<EOF
usage: $0 [--output DIR] [--archive FILE] [--repo OWNER/NAME] [--version VERSION]

Fetches deblite-artwork-<version>.tar.gz from a GitHub Release and extracts
it to DIR (default: build/artwork). The result contains wallpapers/ and is
cached per version.

The release is pinned by artwork-release.env; command-line flags and the
DEBLITE_ARTWORK_* environment variables override it.

  --archive FILE   use a local tarball instead of downloading one

DEBLITE_ARTWORK_BASE_URL overrides the release URL, which is useful for
mirrors and for exercising the download/checksum path in tests.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            OUTPUT=$2
            shift 2
            ;;
        --archive)
            ARCHIVE_OVERRIDE=$2
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
[ -f "$ROOT/artwork-release.env" ] && . "$ROOT/artwork-release.env"

VERSION=${VERSION_OVERRIDE:-${DEBLITE_ARTWORK_VERSION:-0.1.0}}
REPO=${REPO_OVERRIDE:-${DEBLITE_ARTWORK_REPO:-}}
ARCHIVE_OVERRIDE=${ARCHIVE_OVERRIDE:-${DEBLITE_ARTWORK_ARCHIVE:-}}
OUTPUT=${OUTPUT:-$ROOT/build/artwork}

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
        REPO="$owner/deblite-artwork"
    else
        # Fallback used before the repository has a remote. Override it with
        # DEBLITE_ARTWORK_REPO or --repo.
        REPO="wlroots/deblite-artwork"
    fi
fi

NAME="deblite-artwork-${VERSION}"
TARBALL="$NAME.tar.gz"
STAMP="$OUTPUT/.deblite-artwork-version"
STAMP_VALUE=$VERSION
if [ -n "${DEBLITE_ARTWORK_SHA256:-}" ]; then
    STAMP_VALUE="$VERSION $DEBLITE_ARTWORK_SHA256"
fi

if [ -d "$OUTPUT/wallpapers" ] && [ -z "$ARCHIVE_OVERRIDE" ] &&
    [ "$(cat "$STAMP" 2>/dev/null || true)" = "$STAMP_VALUE" ]; then
    echo "artwork: using cached $OUTPUT ($VERSION)"
    exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/$TARBALL"

if [ -n "$ARCHIVE_OVERRIDE" ]; then
    echo "==> using local artwork: $ARCHIVE_OVERRIDE"
    cp "$ARCHIVE_OVERRIDE" "$ARCHIVE"
else
    BASE=${DEBLITE_ARTWORK_BASE_URL:-https://github.com/$REPO/releases/download/artwork-v${VERSION}}
    BASE=${BASE%/}
    echo "==> downloading $BASE/$TARBALL"
    curl -fL --retry 3 --connect-timeout 10 --max-time 300 -o "$ARCHIVE" "$BASE/$TARBALL"

    if [ -n "${DEBLITE_ARTWORK_SHA256:-}" ]; then
        printf '%s  %s\n' "$DEBLITE_ARTWORK_SHA256" "$TARBALL" |
            (cd "$TMP" && sha256sum -c -)
    else
        curl -fL --retry 3 --connect-timeout 10 --max-time 120 \
            -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS"
        expected=$(awk -v name="$TARBALL" '$2 == name { print $1 }' "$TMP/SHA256SUMS")
        if [ -z "$expected" ]; then
            echo "error: $TARBALL is not listed in the release's SHA256SUMS" >&2
            exit 1
        fi
        actual=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
        if [ "$actual" != "$expected" ]; then
            echo "error: checksum mismatch for $TARBALL" >&2
            echo "       expected $expected" >&2
            echo "       got      $actual" >&2
            exit 1
        fi
    fi
fi

# Reject absolute paths and parent-directory traversal before extracting.
while IFS= read -r entry; do
    case "$entry" in
        /* | ../* | */../* | */..)
            echo "error: unsafe path in artwork archive: $entry" >&2
            exit 1
            ;;
    esac
done < <(tar -tzf "$ARCHIVE")

mkdir -p "$TMP/extract"
tar -xzf "$ARCHIVE" -C "$TMP/extract" --no-same-owner
if [ ! -d "$TMP/extract/$NAME/wallpapers" ]; then
    echo "error: $TARBALL does not contain $NAME/wallpapers" >&2
    exit 1
fi

rm -rf "$OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
cp -a "$TMP/extract/$NAME" "$OUTPUT"
printf '%s\n' "$STAMP_VALUE" >"$STAMP"

echo "artwork: $VERSION -> $OUTPUT/wallpapers"
