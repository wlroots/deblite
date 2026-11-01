from __future__ import annotations

from .config import InstallConfig
from .executor import Executor

BASE_PACKAGES = [
    "base", "base-devel", "linux", "linux-firmware",
    "sudo", "networkmanager", "nano", "vim", "git",
]


def run_pacstrap(cfg: InstallConfig, ex: Executor, extra_packages: list[str]) -> None:
    packages = list(dict.fromkeys(BASE_PACKAGES + extra_packages))  # dedupe, keep order
    ex.run(["pacstrap", "-K", cfg.mount_root, *packages])


def generate_fstab(cfg: InstallConfig, ex: Executor) -> None:
    # genfstab читает реально смонтированные ФС — в debug-режиме их не
    # существует (мы ничего не монтировали), поэтому это тоже "деструктивная"
    # в смысле dry-run операция: она не выполняется, а только логируется.
    if ex.debug:
        ex.run(["genfstab", "-U", cfg.mount_root])
        ex.write_file(f"{cfg.mount_root}/etc/fstab", "# dry-run: fstab would be generated here\n")
        return

    result = ex.run(["genfstab", "-U", cfg.mount_root])
    ex.write_file(f"{cfg.mount_root}/etc/fstab", result.stdout)


def configure_base_system(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root

    ex.chroot_run(root, ["ln", "-sf", f"/usr/share/zoneinfo/{cfg.locale.timezone}", "/etc/localtime"])
    ex.chroot_run(root, ["hwclock", "--systohc"])

    ex.write_file(f"{root}/etc/locale.gen", f"{cfg.locale.locale} UTF-8\nen_US.UTF-8 UTF-8\n")
    ex.chroot_run(root, ["locale-gen"])
    ex.write_file(f"{root}/etc/locale.conf", f"LANG={cfg.locale.locale}\n")
    ex.write_file(f"{root}/etc/vconsole.conf", f"KEYMAP={cfg.locale.keymap}\n")

    ex.write_file(f"{root}/etc/hostname", f"{cfg.network.hostname}\n")
    ex.write_file(
        f"{root}/etc/hosts",
        "127.0.0.1\tlocalhost\n::1\t\tlocalhost\n"
        f"127.0.1.1\t{cfg.network.hostname}.localdomain\t{cfg.network.hostname}\n",
    )

    if cfg.network.enable_networkmanager:
        ex.chroot_run(root, ["systemctl", "enable", "NetworkManager"])

    # пользователи
    if cfg.user.root_password:
        ex.chroot_run(root, ["chpasswd"], input=f"root:{cfg.user.root_password}\n")

    useradd_cmd = ["useradd", "-m", "-c", cfg.user.full_name or cfg.user.username]
    if cfg.user.is_admin:
        useradd_cmd += ["-G", "wheel"]
    useradd_cmd.append(cfg.user.username)
    ex.chroot_run(root, useradd_cmd)

    if cfg.user.password:
        ex.chroot_run(root, ["chpasswd"], input=f"{cfg.user.username}:{cfg.user.password}\n")

    if cfg.user.is_admin:
        ex.write_file(
            f"{root}/etc/sudoers.d/10-wheel",
            "%wheel ALL=(ALL:ALL) ALL\n",
        )
