#!/usr/bin/env bash
# Shared helpers for the ISO inspection scripts.
set -euo pipefail

extract_squashfs() {
    local iso=$1
    local out=$2
    rm -f "$out"

    if xorriso -osirrox on -indev "$iso" -extract /live/filesystem.squashfs "$out" \
        >/dev/null 2>&1; then
        [ -s "$out" ] && return 0
    fi

    # Fallback for unusual layouts.
    local mnt
    mnt=$(mktemp -d)
    if mount -o loop,ro "$iso" "$mnt" 2>/dev/null; then
        if [ -f "$mnt/live/filesystem.squashfs" ]; then
            cp "$mnt/live/filesystem.squashfs" "$out"
            umount "$mnt"
            rmdir "$mnt"
            return 0
        fi
        umount "$mnt"
    fi
    rmdir "$mnt" 2>/dev/null || true
    return 1
}

iso_size() {
    du -h "$1" | cut -f1
}

squashfs_size() {
    du -h "$1" | cut -f1
}
