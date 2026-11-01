from __future__ import annotations

from .config import InstallConfig
from .executor import Executor

COMMON_APPS = ["firefox", "htop", "man-db", "man-pages", "bash-completion", "unzip", "wget"]
PIPEWIRE_PACKAGES = ["pipewire", "pipewire-alsa", "pipewire-pulse", "pipewire-jack", "wireplumber"]
BLUETOOTH_PACKAGES = ["bluez", "bluez-utils"]


def collect_extra_packages(cfg: InstallConfig) -> list[str]:
    """Пакеты, которые нужно поставить ОДНИМ pacstrap-вызовом (проще и надёжнее,
    чем ставить их отдельно после — меньше шагов, где может не быть сети в chroot)."""
    pkgs: list[str] = []
    if cfg.software.enable_ufw:
        pkgs.append("ufw")
    if cfg.software.enable_zram:
        pkgs.append("zram-generator")
    if cfg.software.install_flatpak:
        pkgs.append("flatpak")
    if cfg.software.install_pipewire:
        pkgs += PIPEWIRE_PACKAGES
    if cfg.software.enable_bluetooth:
        pkgs += BLUETOOTH_PACKAGES
    if cfg.software.install_common_apps:
        pkgs += COMMON_APPS
    pkgs += cfg.software.extra_packages
    return pkgs


def configure_software(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root

    if cfg.software.enable_ufw:
        ex.chroot_run(root, ["systemctl", "enable", "ufw"])
        ex.chroot_run(root, ["ufw", "default", "deny", "incoming"], check=False)
        ex.chroot_run(root, ["ufw", "default", "allow", "outgoing"], check=False)
        ex.chroot_run(root, ["ufw", "enable"], check=False)

    if cfg.software.enable_zram:
        ex.write_file(
            f"{root}/etc/systemd/zram-generator.conf",
            "[zram0]\nzram-size = min(ram / 2, 4096)\ncompression-algorithm = zstd\n",
        )

    if cfg.software.enable_bluetooth:
        ex.chroot_run(root, ["systemctl", "enable", "bluetooth"])
