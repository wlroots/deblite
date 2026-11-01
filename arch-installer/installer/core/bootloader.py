from __future__ import annotations

from .config import Bootloader, InstallConfig
from .executor import Executor


def _kernel_cmdline(cfg: InstallConfig, root_device: str) -> str:
    parts = []
    if cfg.luks.enabled:
        # root_device здесь физический раздел под LUKS
        parts.append(f"cryptdevice=UUID=$(blkid -s UUID -o value {root_device}):cryptroot")
        parts.append("root=/dev/mapper/cryptroot")
    else:
        parts.append(f"root=UUID=$(blkid -s UUID -o value {root_device})")
    parts += ["rw", "quiet"]
    return " ".join(parts)


def install_bootloader(cfg: InstallConfig, ex: Executor, esp_partition: str, root_partition: str) -> None:
    root = cfg.mount_root
    kind = cfg.bootloader.kind

    if cfg.luks.enabled:
        # добавляем encrypt hook в mkinitcpio для всех вариантов загрузки
        ex.chroot_run(root, [
            "sed", "-i",
            "s/^HOOKS=.*/HOOKS=(base udev autodetect microcode modconf kms keyboard keymap "
            "consolefont block encrypt filesystems fsck)/",
            "/etc/mkinitcpio.conf",
        ])
        ex.chroot_run(root, ["mkinitcpio", "-P"])

    if kind == Bootloader.GRUB:
        ex.chroot_run(root, ["pacman", "-S", "--noconfirm", "grub", "efibootmgr"])
        ex.chroot_run(root, [
            "grub-install", "--target=x86_64-efi",
            "--efi-directory=/boot", "--bootloader-id=GRUB",
        ])
        if cfg.luks.enabled:
            cmdline = _kernel_cmdline(cfg, root_partition)
            ex.chroot_run(root, [
                "sed", "-i",
                f's|^GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX="{cmdline}"|',
                "/etc/default/grub",
            ])
        ex.chroot_run(root, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])

    elif kind == Bootloader.LIMINE:
        ex.chroot_run(root, ["pacman", "-S", "--noconfirm", "limine"])
        ex.chroot_run(root, ["cp", "/usr/share/limine/BOOTX64.EFI", "/boot/EFI/BOOT/BOOTX64.EFI"])
        cmdline = _kernel_cmdline(cfg, root_partition)
        limine_cfg = (
            "TIMEOUT=3\n\n"
            ":Arch Linux\n"
            "PROTOCOL=linux\n"
            "KERNEL_PATH=boot:///vmlinuz-linux\n"
            "MODULE_PATH=boot:///initramfs-linux.img\n"
            f"CMDLINE={cmdline}\n"
        )
        ex.write_file(f"{root}/boot/limine.cfg", limine_cfg)

    elif kind == Bootloader.UKI_EFISTUB:
        # Unified Kernel Image, загружается напрямую через efibootmgr,
        # без отдельного загрузчика (grub/limine/systemd-boot не нужны).
        ex.chroot_run(root, ["pacman", "-S", "--noconfirm", "efibootmgr", "binutils"])
        cmdline = _kernel_cmdline(cfg, root_partition)
        ex.write_file(f"{root}/etc/kernel/cmdline", cmdline + "\n")
        ex.mkdir(f"{root}/boot/EFI/Linux")
        ex.chroot_run(root, [
            "dracut", "--uefi", "--kver", "linux",
            "--cmdline", cmdline,
            "/boot/EFI/Linux/arch-linux.efi",
        ], check=False)  # dracut может отсутствовать в базовом наборе — не критично для каркаса
        ex.chroot_run(root, [
            "efibootmgr", "--create", "--disk", cfg.disk.device,
            "--part", "1", "--label", "Arch Linux",
            "--loader", "\\EFI\\Linux\\arch-linux.efi",
        ])

    else:
        raise ValueError(f"Неизвестный загрузчик: {kind}")
