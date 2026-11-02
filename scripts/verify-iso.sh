#!/usr/bin/env bash
# Static sanity checks for a built DebLite ISO.
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

echo "ISO:      $ISO ($(iso_size "$ISO"))"

if ! extract_squashfs "$ISO" "$TMP/filesystem.squashfs"; then
    echo "FAIL: cannot extract /live/filesystem.squashfs" >&2
    exit 1
fi
echo "squashfs: $(squashfs_size "$TMP/filesystem.squashfs")"

unsquashfs -l "$TMP/filesystem.squashfs" | sed 's#^squashfs-root/##' >"$TMP/list.txt"

fail=0
require() {
    if ! grep -qxF "$1" "$TMP/list.txt"; then
        echo "FAIL: missing $1" >&2
        fail=1
    fi
}
require_prefix() {
    if ! grep -q "^$1" "$TMP/list.txt"; then
        echo "FAIL: missing $1*" >&2
        fail=1
    fi
}
forbid_prefix() {
    if grep -q "^$1" "$TMP/list.txt"; then
        echo "FAIL: forbidden path present: $1*" >&2
        fail=1
    fi
}

# Required payload.
require usr/bin/deblite-installer
require usr/bin/apt
require usr/bin/dpkg
require etc/apt/apt.conf.d/99deblite
require etc/os-release
require etc/deblite-flavor
require usr/lib/grub/i386-pc
require usr/lib/grub/x86_64-efi
require_prefix boot/vmlinuz-
require_prefix boot/initrd.img-

# Every edition ships the core applications.
require usr/bin/nvim
require usr/bin/gimp
require usr/bin/helium
require usr/bin/onlyoffice-desktopeditors
require usr/bin/firewall-cmd

# The installer must never ship d-i or Calamares.
forbid_prefix usr/sbin/calamares
forbid_prefix usr/lib/calamares
forbid_prefix etc/calamares
forbid_prefix usr/sbin/debian-installer
forbid_prefix install/

# Live medium must provide the installer and the live stack.
if ! xorriso -indev "$ISO" -find / -name isolinux.bin -exec echo 2>/dev/null | grep -q isolinux.bin; then
    echo "WARN: isolinux.bin not found (BIOS boot may be unavailable)" >&2
fi
if ! xorriso -indev "$ISO" -find / -name grubx64.efi -exec echo 2>/dev/null | grep -q grubx64.efi; then
    echo "WARN: no grubx64.efi on the ISO (UEFI boot may be unavailable)" >&2
fi

# Confirm the lean-apt policy made it into the image.
if unsquashfs -cat "$TMP/filesystem.squashfs" etc/apt/apt.conf.d/99deblite 2>/dev/null |
    grep -q 'Install-Recommends "false"'; then
    :
else
    echo "FAIL: 99deblite apt policy missing or wrong" >&2
    fail=1
fi

flavor=$(unsquashfs -cat "$TMP/filesystem.squashfs" etc/deblite-flavor 2>/dev/null | head -n1)
case "$flavor" in
    kde)
        echo "flavor:   kde"
        require usr/bin/plasmashell
        require usr/bin/sddm
        ;;
    gnome|gnome-backports)
        echo "flavor:   $flavor"
        require usr/bin/gnome-shell
        require usr/sbin/gdm3
        ;;
    xfce)
        echo "flavor:   xfce"
        require usr/bin/xfce4-session
        require usr/sbin/lightdm
        require usr/bin/light-locker
        require_prefix usr/share/themes/Greybird
        ;;
    cinnamon)
        echo "flavor:   cinnamon"
        require usr/bin/cinnamon
        require usr/sbin/lightdm
        require usr/sbin/slick-greeter
        require_prefix usr/share/themes/Mint-Y
        require_prefix usr/share/icons/Mint-Y
        ;;
    *)
        echo "FAIL: unexpected /etc/deblite-flavor: '${flavor:-<empty>}'" >&2
        fail=1
        ;;
esac

# When the ISO follows our naming scheme, the baked edition must match it.
expected=$(basename "$ISO" | sed -nE 's/^deblite-13-(.+)-amd64\.iso$/\1/p')
if [ -n "$expected" ] && [ "$expected" != "$flavor" ]; then
    echo "FAIL: ISO is named '$expected' but contains flavor '$flavor'" >&2
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "verify-iso: FAILED" >&2
    exit 1
fi

echo "verify-iso: OK"
