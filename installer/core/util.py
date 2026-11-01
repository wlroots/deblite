"""Small read-only helpers shared by the installer core."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

SQUASHFS_CANDIDATES = (
    "/run/live/medium/live/filesystem.squashfs",
    "/lib/live/mount/medium/live/filesystem.squashfs",
    "/run/live/rootfs/filesystem.squashfs",
    "/cdrom/live/filesystem.squashfs",
)

LIVE_MEDIUM_CANDIDATES = (
    "/run/live/medium",
    "/lib/live/mount/medium",
    "/cdrom",
)

# Pseudo filesystems that must be available inside the target chroot.
PSEUDO_MOUNTS = (
    ("/dev", "dev"),
    ("/dev/pts", "dev/pts"),
    ("/proc", "proc"),
    ("/sys", "sys"),
    ("/run", "run"),
)


def which(name: str) -> str | None:
    return shutil.which(name)


def is_efi() -> bool:
    return Path("/sys/firmware/efi").is_dir()


def resolve_firmware(mode: str) -> str:
    if mode in ("uefi", "bios"):
        return mode
    return "uefi" if is_efi() else "bios"


def resolve_squashfs(explicit: str = "") -> str | None:
    if explicit:
        p = Path(explicit)
        return str(p) if p.is_file() else None
    for candidate in SQUASHFS_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def live_medium() -> str | None:
    for candidate in LIVE_MEDIUM_CANDIDATES:
        if Path(candidate).is_dir():
            return candidate
    return None


def part_suffix(device: str, index: int) -> str:
    """``/dev/nvme0n1`` -> ``/dev/nvme0n1p1``; ``/dev/sda`` -> ``/dev/sda1``."""
    if device and device[-1].isdigit():
        return f"{device}p{index}"
    return f"{device}{index}"


def run_output(args: list[str], default: str = "") -> str:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return default
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def blkid(device: str, tag: str) -> str:
    return run_output(["blkid", "-s", tag, "-o", "value", device])


def blkid_uuid(device: str) -> str:
    return blkid(device, "UUID")


def blkid_type(device: str) -> str:
    return blkid(device, "TYPE")


def lsblk_disks() -> list[dict]:
    raw = run_output(
        [
            "lsblk",
            "-J",
            "-b",
            "-d",
            "-o",
            "NAME,SIZE,MODEL,SERIAL,TRAN,TYPE,ROTA",
        ]
    )
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    live_disk = live_medium_disk()
    disks = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        name = dev.get("name", "")
        if not name or name.startswith(("loop", "zram", "sr")):
            continue
        device = f"/dev/{name}"
        if live_disk and device == live_disk:
            # Never offer the medium the installer is running from.
            continue
        disks.append(
            {
                "device": device,
                "name": name,
                "size": int(dev.get("size") or 0),
                "model": (dev.get("model") or "").strip(),
                "serial": (dev.get("serial") or "").strip(),
                "transport": (dev.get("tran") or "").strip(),
                "rotational": bool(dev.get("rota")),
            }
        )
    disks.sort(key=lambda d: d["device"])
    return disks


def live_medium_disk() -> str | None:
    """Return the whole disk that backs the running live medium, if any."""
    for mountpoint in LIVE_MEDIUM_CANDIDATES:
        if not Path(mountpoint).is_dir():
            continue
        source = run_output(["findmnt", "-n", "-o", "SOURCE", "-T", mountpoint])
        if not source or not source.startswith("/dev/"):
            continue
        parent = run_output(["lsblk", "-n", "-o", "PKNAME", source])
        if parent:
            return f"/dev/{parent.strip()}"
        return source
    return None


def human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num} B"


def ensure_commands(names: list[str]) -> list[str]:
    return [name for name in names if which(name) is None]
