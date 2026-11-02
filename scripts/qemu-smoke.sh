#!/usr/bin/env bash
# Optional smoke test: boot the ISO's kernel/initramfs in QEMU with a serial
# console and wait for live-boot/systemd markers. This bypasses isolinux/GRUB
# (use a VM for bootloader testing) but proves the live rootfs actually boots.
set -euo pipefail

ISO=${1:-}
if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
    echo "usage: $0 path/to/deblite.iso" >&2
    exit 2
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    echo "qemu-system-x86_64 not installed; skipping smoke test" >&2
    exit 0
fi

TIMEOUT=${TIMEOUT:-180}
TMP=$(mktemp -d)
LOG="$TMP/serial.log"
trap 'rm -rf "$TMP"' EXIT

if ! xorriso -osirrox on -indev "$ISO" \
    -extract /live/vmlinuz "$TMP/vmlinuz" \
    -extract /live/initrd.img "$TMP/initrd.img" >/dev/null 2>&1; then
    echo "qemu-smoke: cannot extract /live/vmlinuz and /live/initrd.img" >&2
    exit 1
fi
chmod +w "$TMP/vmlinuz" "$TMP/initrd.img"

ACCEL=()
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    ACCEL=(-enable-kvm -cpu host)
fi

set +e
timeout "$TIMEOUT" qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -machine q35 \
    "${ACCEL[@]}" \
    -kernel "$TMP/vmlinuz" \
    -initrd "$TMP/initrd.img" \
    -append "boot=live components console=ttyS0,115200" \
    -cdrom "$ISO" \
    -boot d \
    -nographic \
    -no-reboot \
    >"$LOG" 2>&1
status=$?
set -e

if grep -qE 'Linux version|DebLite|live-boot|systemd\[1\]|Reached target' "$LOG"; then
    echo "qemu-smoke: boot markers found"
    exit 0
fi

echo "qemu-smoke: no boot markers (qemu exit $status)" >&2
tail -50 "$LOG" >&2
exit 1
