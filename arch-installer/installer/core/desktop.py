from __future__ import annotations

from .config import Desktop, InstallConfig
from .executor import Executor

KDE_PACKAGES = [
    "plasma-meta", "plasma-nm", "sddm", "kde-applications-meta",
    "dolphin", "konsole", "kate",
]

GNOME_PACKAGES = [
    "gnome", "gnome-tweaks", "gdm",
]


def desktop_packages(cfg: InstallConfig) -> list[str]:
    if cfg.desktop.kind == Desktop.KDE:
        return KDE_PACKAGES
    if cfg.desktop.kind == Desktop.GNOME:
        return GNOME_PACKAGES
    return []


def install_desktop(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    if cfg.desktop.kind == Desktop.NONE:
        return

    packages = desktop_packages(cfg)
    ex.chroot_run(root, ["pacman", "-S", "--noconfirm", *packages])

    dm = "sddm" if cfg.desktop.kind == Desktop.KDE else "gdm"
    ex.chroot_run(root, ["systemctl", "enable", dm])
