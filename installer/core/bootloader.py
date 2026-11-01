"""GRUB installation and initramfs regeneration inside the target root."""
from __future__ import annotations

from pathlib import Path

from .config import InstallConfig
from .executor import Executor, InstallerError


def install_bootloader(cfg: InstallConfig, ex: Executor, parts: dict[str, str]) -> None:
    root = cfg.mount_root
    firmware = parts.get("firmware", "uefi")

    _write_grub_defaults(cfg, ex)

    if firmware == "uefi":
        _install_efi(cfg, ex)
    else:
        _install_bios(cfg, ex, parts["disk"])

    ex.chroot_run(root, ["update-grub"])
    ex.chroot_run(root, ["update-initramfs", "-u", "-k", "all"])

    if firmware == "uefi" and not Path(root, "boot/efi/EFI/DebLite/grubx64.efi").exists():
        if not ex.debug:
            raise InstallerError("GRUB EFI binary was not created under /boot/efi/EFI/DebLite")


def _install_efi(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    base = [
        "grub-install",
        "--target=x86_64-efi",
        "--efi-directory=/boot/efi",
        "--bootloader-id=DebLite",
        "--recheck",
    ]
    # Prefer a real NVRAM entry; fall back to a removable-path install when the
    # firmware interface is read-only (common in containers and some VMs).
    result = ex.chroot_run(root, base, check=False)
    if not result.ok:
        ex.chroot_run(root, [*base, "--no-nvram"])

    ex.chroot_run(
        root,
        [
            "grub-install",
            "--target=x86_64-efi",
            "--efi-directory=/boot/efi",
            "--removable",
            "--no-nvram",
            "--recheck",
        ],
        check=False,
    )


def _install_bios(cfg: InstallConfig, ex: Executor, disk: str) -> None:
    ex.chroot_run(
        cfg.mount_root,
        ["grub-install", "--target=i386-pc", "--recheck", disk],
    )


def _write_grub_defaults(cfg: InstallConfig, ex: Executor) -> None:
    path = Path(cfg.mount_root, "etc/default/grub")
    content = path.read_text() if path.exists() else ""

    values = {
        "GRUB_DEFAULT": "0",
        "GRUB_TIMEOUT": "3",
        "GRUB_DISTRIBUTOR": '"DebLite"',
        "GRUB_CMDLINE_LINUX_DEFAULT": '"quiet"',
        "GRUB_CMDLINE_LINUX": '"root=/dev/mapper/cryptroot"' if cfg.luks.enabled else '""',
        "GRUB_DISABLE_OS_PROBER": "true",
        "GRUB_ENABLE_CRYPTODISK": "n",
    }
    for key, value in values.items():
        content = _set_key(content, key, value)

    ex.write_file(str(path), content if content.endswith("\n") else content + "\n")


def _set_key(content: str, key: str, value: str) -> str:
    lines = content.splitlines()
    prefix = f"{key}="
    replaced = False
    out = []
    for line in lines:
        if line.startswith(prefix):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    return "\n".join(out) + "\n"
