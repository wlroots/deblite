#!/usr/bin/env bash
# Optional smoke test: boot the ISO in QEMU and wait for a Linux banner.
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
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

set +e
timeout "$TIMEOUT" qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -machine q35 \
    -cdrom "$ISO" \
    -boot d \
    -nographic \
    -no-reboot \
    -serial mon:stdio \
    >"$LOG" 2>&1
status=$?
set -e

if grep -qE 'Linux version|DebLite|live-boot|systemd\[1\]' "$LOG"; then
    echo "qemu-smoke: boot markers found"
    exit 0
fi

echo "qemu-smoke: no boot markers (qemu exit $status)" >&2
tail -50 "$LOG" >&2
exit 1
