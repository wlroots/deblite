#!/usr/bin/env bash
# Detect the current Debian 13 point release from cdimage.debian.org.
#
# Prints key=value lines and, when GITHUB_OUTPUT is set, writes them there.
set -euo pipefail

BASE_URL=${1:-https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/}
CURRENT_FILE=${CURRENT_FILE:-debian-version.txt}

html=$(curl -fsSL --retry 3 "$BASE_URL" || true)
version=$(printf '%s' "$html" |
    grep -oE 'debian-13\.[0-9]+\.0-amd64-netinst\.iso' |
    head -1 |
    sed -E 's/^debian-(13\.[0-9]+)\.0-amd64-netinst\.iso$/\1/')

if [ -z "$version" ]; then
    echo "error: could not determine the Debian point release from $BASE_URL" >&2
    exit 1
fi

current=""
if [ -f "$CURRENT_FILE" ]; then
    current=$(tr -d '[:space:]' <"$CURRENT_FILE")
fi

changed=false
if [ "$version" != "$current" ]; then
    changed=true
fi

echo "debian_version=$version"
echo "current_version=$current"
echo "changed=$changed"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "debian_version=$version"
        echo "current_version=$current"
        echo "changed=$changed"
    } >>"$GITHUB_OUTPUT"
fi
