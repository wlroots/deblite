#!/usr/bin/env bash
# Install the built ISO's rootfs onto a loop-backed disk image and check the
# result. This exercises partitioning, unsquashfs, de-live, fstab, users and
# GRUB without touching a real disk. UEFI is intentionally not tested here:
# grub-install would write NVRAM entries on the build host. Use a VM for that.
#
# Usage:
#   sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso [--luks] [--boot]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ISO=${1:-}
shift || true
LUKS=0
BOOT=0
for arg in "$@"; do
    case "$arg" in
        --luks) LUKS=1 ;;
        --boot) BOOT=1 ;;
        -h|--help)
            echo "usage: $0 path/to/deblite.iso [--luks] [--boot]" >&2
            exit 0
            ;;
        *)
            echo "unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
    echo "usage: $0 path/to/deblite.iso [--luks] [--boot]" >&2
    exit 2
fi
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "this test needs root (loop devices, mounts, chroot)" >&2
    exit 2
fi

WORK=$(mktemp -d "${DEBLITE_TEST_WORK:-/var/tmp}/deblite-install-test.XXXXXX")
LOOP=""
cleanup() {
    set +e
    umount -R "$WORK/target" 2>/dev/null
    if [ "$LUKS" = "1" ]; then
        cryptsetup close deblite-test-root 2>/dev/null
    fi
    if [ -n "$LOOP" ]; then
        losetup -d "$LOOP" 2>/dev/null
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

DISK="$WORK/disk.img"
MOUNT_ROOT="$WORK/target"
SQUASHFS="$WORK/filesystem.squashfs"

echo "==> extracting filesystem.squashfs"
xorriso -osirrox on -indev "$ISO" -extract /live/filesystem.squashfs "$SQUASHFS" >/dev/null 2>&1
chmod +w "$SQUASHFS"

FLAVOR=$(unsquashfs -cat "$SQUASHFS" etc/deblite-flavor 2>/dev/null | head -n1)
FLAVOR=${FLAVOR:-unknown}
echo "==> edition baked into the ISO: $FLAVOR"

echo "==> creating a 12 GiB sparse disk image"
truncate -s 12G "$DISK"
LOOP=$(losetup --find --show --partscan "$DISK")

PASSPHRASE=""
if [ "$LUKS" = "1" ]; then
    PASSPHRASE="deblite-test-passphrase"
fi

CONFIG=$(mktemp)
cat >"$CONFIG" <<EOF
{
  "flavor": "$FLAVOR",
  "disk": {
    "device": "$LOOP",
    "mode": "erase_disk",
    "firmware": "bios",
    "esp_size_mib": 512,
    "boot_size_mib": 1024,
    "swap_size_mib": 0,
    "filesystem": "ext4"
  },
  "luks": {"enabled": $([ "$LUKS" = 1 ] && echo true || echo false), "passphrase": "$PASSPHRASE"},
  "user": {
    "username": "tester",
    "full_name": "DebLite Tester",
    "password": "test-password",
    "is_admin": true,
    "root_password": "",
    "autologin": false
  },
  "locale": {"locale": "en_US.UTF-8", "keymap": "us", "timezone": "UTC"},
  "network": {"hostname": "deblite-test"},
  "mount_root": "$MOUNT_ROOT",
  "source": "$SQUASHFS",
  "skip_delive": false,
  "keep_live_user": false
}
EOF

echo "==> running the installer"
"$ROOT/bin/deblite-installer" --headless --config "$CONFIG" --yes

echo "==> inspecting the installed system"
ROOT_DEV=$(lsblk -no PATH,PARTLABEL "$LOOP" | awk '$2 == "DEBLITE_ROOT" { print $1 }')
if [ -z "$ROOT_DEV" ]; then
    echo "FAIL: cannot find the DEBLITE_ROOT partition" >&2
    exit 1
fi
ROOT_PART=$ROOT_DEV
if [ "$LUKS" = "1" ]; then
    cryptsetup open --key-file <(printf '%s' "$PASSPHRASE") "$ROOT_DEV" deblite-test-root
    ROOT_PART="/dev/mapper/deblite-test-root"
fi

mkdir -p "$MOUNT_ROOT"
mount "$ROOT_PART" "$MOUNT_ROOT"

BOOT_DEV=$(lsblk -no PATH,PARTLABEL "$LOOP" | awk '$2 == "DEBLITE_BOOT" { print $1 }')
if [ -n "$BOOT_DEV" ]; then
    mkdir -p "$MOUNT_ROOT/boot"
    mount "$BOOT_DEV" "$MOUNT_ROOT/boot"
fi

fail=0
check() {
    if [ ! -e "$MOUNT_ROOT/$1" ]; then
        echo "FAIL: missing /$1" >&2
        fail=1
    fi
}
check etc/fstab
check etc/passwd
check boot/grub/grub.cfg
check usr/bin/apt

if grep -q '^tester:' "$MOUNT_ROOT/etc/passwd"; then
    :
else
    echo "FAIL: user tester was not created" >&2
    fail=1
fi

if grep -q '^Package: live-boot$' "$MOUNT_ROOT/var/lib/dpkg/status" 2>/dev/null; then
    echo "FAIL: live-boot is still installed on the target" >&2
    fail=1
fi

if [ "$(cat "$MOUNT_ROOT/etc/hostname")" != "deblite-test" ]; then
    echo "FAIL: hostname was not configured" >&2
    fail=1
fi

if [ -f "$MOUNT_ROOT/etc/crypttab" ] && [ "$LUKS" = "1" ]; then
    grep -q '^deblite-test-root\|^cryptroot' "$MOUNT_ROOT/etc/crypttab" ||
        { echo "FAIL: crypttab is missing the root mapping" >&2; fail=1; }
elif [ "$LUKS" = "1" ]; then
    echo "FAIL: /etc/crypttab is missing" >&2
    fail=1
fi

mountpoint -q "$MOUNT_ROOT/boot/efi" || true
if [ -f "$MOUNT_ROOT/etc/fstab" ]; then
    echo "--- /etc/fstab"
    sed 's/^/    /' "$MOUNT_ROOT/etc/fstab"
fi

if [ "$fail" -eq 0 ] && [ "$BOOT" = "1" ]; then
    if [ "$LUKS" = "1" ]; then
        echo "test-install: skipping the boot test for LUKS (passphrase prompt)"
    elif ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
        echo "test-install: qemu-system-x86_64 not installed; skipping boot test"
    else
        KERNEL=$(find "$MOUNT_ROOT/boot" -maxdepth 1 -name 'vmlinuz-*' -print -quit)
        INITRD=$(find "$MOUNT_ROOT/boot" -maxdepth 1 -name 'initrd.img-*' -print -quit)
        ROOT_UUID=$(awk '$2 == "/" { print $1 }' "$MOUNT_ROOT/etc/fstab" | sed 's/^UUID=//')
        if [ -z "$KERNEL" ] || [ -z "$INITRD" ] || [ -z "$ROOT_UUID" ]; then
            echo "FAIL: cannot prepare the installed-system boot test" >&2
            exit 1
        fi
        cp "$KERNEL" "$WORK/vmlinuz"
        cp "$INITRD" "$WORK/initrd.img"
        umount -R "$MOUNT_ROOT"
        losetup -d "$LOOP"
        LOOP=""

        ACCEL=()
        if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
            ACCEL=(-enable-kvm -cpu host)
        fi
        echo "==> booting the installed system"
        set +e
        timeout 150 qemu-system-x86_64 \
            -m 2048 -smp 2 -machine q35 "${ACCEL[@]}" \
            -kernel "$WORK/vmlinuz" \
            -initrd "$WORK/initrd.img" \
            -append "root=UUID=$ROOT_UUID rw console=ttyS0,115200" \
            -drive file="$DISK",format=raw,if=virtio \
            -nographic -no-reboot \
            >"$WORK/boot.log" 2>&1
        set -e
        if grep -qE 'systemd\[1\]|Reached target|DebLite|login:' "$WORK/boot.log"; then
            echo "test-install: installed system booted"
        else
            echo "FAIL: the installed system did not boot" >&2
            tail -40 "$WORK/boot.log" >&2
            exit 1
        fi
    fi
fi

if [ "$fail" -ne 0 ]; then
    echo "test-install: FAILED" >&2
    exit 1
fi
echo "test-install: OK"
