"""GPT partitioning, LUKS2, filesystems, mounting and fstab generation."""
from __future__ import annotations

import os
from pathlib import Path

from .config import InstallConfig, PartitionMode
from .executor import Executor, InstallerError
from .util import blkid_type, blkid_uuid, part_suffix, resolve_firmware, run_output

LUKS_MAPPER = "cryptroot"


def partition_disk(cfg: InstallConfig, ex: Executor) -> dict[str, str]:
    dev = cfg.disk.device
    if not dev:
        raise InstallerError("no target disk selected")
    if cfg.disk.mode != PartitionMode.ERASE_DISK:
        raise InstallerError(
            "only erase-disk partitioning is supported in this release; "
            "manual/existing layouts are planned"
        )
    if not os.path.exists(dev) and not ex.debug:
        raise InstallerError(f"target disk does not exist: {dev}")

    firmware = resolve_firmware(cfg.disk.firmware.value)
    parts: dict[str, str] = {"disk": dev, "firmware": firmware}

    _release_disk(dev, ex)

    layout: list[tuple[str, str, str, str]] = []
    index = 1

    if firmware == "uefi":
        layout.append((str(index), f"0:+{cfg.disk.esp_size_mib}M", "ef00", "DEBLITE_ESP"))
        index += 1
    else:
        # GPT + GRUB on BIOS needs a tiny BIOS boot partition.
        layout.append((str(index), "0:+1M", "ef02", "DEBLITE_BIOS"))
        index += 1

    if cfg.luks.enabled:
        layout.append((str(index), f"0:+{cfg.disk.boot_size_mib}M", "8300", "DEBLITE_BOOT"))
        index += 1

    if cfg.disk.swap_size_mib:
        layout.append((str(index), f"0:+{cfg.disk.swap_size_mib}M", "8200", "DEBLITE_SWAP"))
        index += 1

    layout.append((str(index), "0:0", "8300", "DEBLITE_ROOT"))

    ex.run(["sgdisk", "--zap-all", dev])
    args = ["sgdisk"]
    for num, size, code, name in layout:
        args += ["-n", f"{num}:{size}", "-t", f"{num}:{code}", "-c", f"{num}:{name}"]
    args.append(dev)
    ex.run(args)
    ex.run(["partprobe", dev], check=False)
    ex.run(["udevadm", "settle"], check=False)

    idx = 1
    if firmware == "uefi":
        parts["esp"] = part_suffix(dev, idx)
        idx += 1
    else:
        # partition 1 is the BIOS boot partition
        idx += 1
    if cfg.luks.enabled:
        parts["boot"] = part_suffix(dev, idx)
        idx += 1
    if cfg.disk.swap_size_mib:
        parts["swap"] = part_suffix(dev, idx)
        idx += 1
    parts["root"] = part_suffix(dev, idx)
    return parts


def _release_disk(dev: str, ex: Executor) -> None:
    """Unmount anything that belongs to the target disk before re-partitioning."""
    import json

    raw = run_output(["lsblk", "-J", "-b", "-o", "NAME,PATH,TYPE,MOUNTPOINT,SWAP", dev])
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    def walk(node: dict) -> None:
        for child in node.get("children") or []:
            walk(child)
        mountpoint = node.get("mountpoint")
        if mountpoint:
            ex.run(["umount", "-l", mountpoint], check=False)
        if node.get("swap") or node.get("type") == "swap":
            ex.run(["swapoff", node.get("path") or f"/dev/{node.get('name')}"], check=False)

    for node in data.get("blockdevices", []):
        walk(node)


def setup_luks(cfg: InstallConfig, ex: Executor, root_part: str) -> str:
    if not cfg.luks.enabled:
        return root_part

    ex.run(
        [
            "cryptsetup",
            "luksFormat",
            "--batch-mode",
            "--key-file",
            "-",
            "--type",
            "luks2",
            "--cipher",
            "aes-xts-plain64",
            "--key-size",
            "512",
            "--hash",
            "sha256",
            "--pbkdf",
            "argon2id",
            "--label",
            "DEBLITE_CRYPT",
            root_part,
        ],
        input=cfg.luks.passphrase,
    )
    ex.run(
        ["cryptsetup", "open", "--key-file", "-", root_part, LUKS_MAPPER],
        input=cfg.luks.passphrase,
    )
    return f"/dev/mapper/{LUKS_MAPPER}"


def format_and_mount(cfg: InstallConfig, ex: Executor, parts: dict[str, str], root_dev: str) -> None:
    root = cfg.mount_root
    fs = cfg.disk.filesystem

    if "esp" in parts:
        ex.run(["mkfs.fat", "-F", "32", "-n", "DEBLITE_ESP", parts["esp"]])
    if "boot" in parts:
        ex.run(["mkfs.ext4", "-F", "-L", "DEBLITE_BOOT", parts["boot"]])
    if "swap" in parts:
        ex.run(["swapoff", parts["swap"]], check=False)
        ex.run(["mkswap", "-L", "DEBLITE_SWAP", parts["swap"]])

    if fs == "btrfs":
        ex.run(["mkfs.btrfs", "-f", "-L", "DEBLITE_ROOT", root_dev])
    elif fs == "xfs":
        ex.run(["mkfs.xfs", "-f", "-L", "DEBLITE_ROOT", root_dev])
    else:
        ex.run(["mkfs.ext4", "-F", "-L", "DEBLITE_ROOT", root_dev])

    ex.mkdir(root)
    ex.run(["mount", "-o", "noatime", root_dev, root])

    if "boot" in parts:
        ex.mkdir(f"{root}/boot")
        ex.run(["mount", "-o", "noatime", parts["boot"], f"{root}/boot"])

    if "esp" in parts:
        ex.mkdir(f"{root}/boot/efi")
        ex.run(["mount", parts["esp"], f"{root}/boot/efi"])

    if "swap" in parts:
        ex.run(["swapon", parts["swap"]])


def generate_fstab(
    cfg: InstallConfig,
    ex: Executor,
    parts: dict[str, str],
    root_dev: str,
) -> None:
    root = cfg.mount_root
    root_uuid = blkid_uuid(root_dev)
    if not root_uuid and not ex.debug:
        raise InstallerError(f"cannot read filesystem UUID of {root_dev}")

    lines = [
        "# <file system> <mount point> <type> <options> <dump> <pass>",
        f"UUID={root_uuid or '<root-uuid>'} / {cfg.disk.filesystem} "
        f"defaults,noatime 0 {1 if cfg.disk.filesystem == 'ext4' else 0}",
    ]

    if "boot" in parts:
        lines.append(
            f"UUID={blkid_uuid(parts['boot']) or '<boot-uuid>'} /boot ext4 defaults,noatime 0 2"
        )
    if "esp" in parts:
        lines.append(
            f"UUID={blkid_uuid(parts['esp']) or '<esp-uuid>'} /boot/efi vfat umask=0077 0 1"
        )
    if "swap" in parts:
        lines.append(f"UUID={blkid_uuid(parts['swap']) or '<swap-uuid>'} none swap sw 0 0")

    ex.write_file(f"{root}/etc/fstab", "\n".join(lines) + "\n")

    if cfg.luks.enabled:
        luks_uuid = blkid_uuid(parts["root"])
        if not luks_uuid and not ex.debug:
            raise InstallerError(f"cannot read LUKS UUID of {parts['root']}")
        ex.write_file(
            f"{root}/etc/crypttab",
            f"# <name> <device> <key file> <options>\n"
            f"{LUKS_MAPPER} UUID={luks_uuid or '<luks-uuid>'} none luks,discard\n",
        )
        ex.write_file(f"{root}/etc/cryptsetup-initramfs/conf-hook", "CRYPTSETUP=y\n")


def unmount(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    ex.run(["umount", "-R", root], check=False)
    if cfg.luks.enabled:
        ex.run(["cryptsetup", "close", LUKS_MAPPER], check=False)


def mount_pseudo(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    for src, rel in (
        ("/dev", "dev"),
        ("/dev/pts", "dev/pts"),
        ("/proc", "proc"),
        ("/sys", "sys"),
        ("/run", "run"),
    ):
        if not Path(src).exists():
            continue
        ex.mkdir(f"{root}/{rel}")
        ex.run(["mount", "--bind", src, f"{root}/{rel}"])

    efivars = "/sys/firmware/efi/efivars"
    if Path(efivars).is_dir():
        ex.mkdir(f"{root}/sys/firmware/efi/efivars")
        ex.run(["mount", "--bind", efivars, f"{root}/sys/firmware/efi/efivars"], check=False)

    resolv = Path("/etc/resolv.conf")
    if resolv.is_file() or resolv.is_symlink():
        try:
            ex.write_file(f"{root}/etc/resolv.conf", resolv.read_text())
        except OSError:
            pass


def unmount_pseudo(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    for rel in (
        "sys/firmware/efi/efivars",
        "run",
        "sys",
        "proc",
        "dev/pts",
        "dev",
    ):
        ex.run(["umount", "-l", f"{root}/{rel}"], check=False)

    # mount_pseudo copied the live DNS config in for the chroot. Remove it so
    # NetworkManager creates the installed system's resolver on first boot.
    ex.remove(f"{root}/etc/resolv.conf")


def verify_filesystem(device: str) -> str:
    return blkid_type(device)
