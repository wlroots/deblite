from __future__ import annotations

import dataclasses
from enum import Enum


class Bootloader(str, Enum):
    GRUB = "grub"
    LIMINE = "limine"
    UKI_EFISTUB = "uki-efistub"  # unified kernel image, запуск через efibootmgr, без загрузчика


class Desktop(str, Enum):
    KDE = "kde"
    GNOME = "gnome"
    NONE = "none"


class PartitionMode(str, Enum):
    ERASE_DISK = "erase_disk"   # авторазметка всего диска
    MANUAL = "manual"           # пользователь сам задаёт разделы
    USE_EXISTING = "use_existing"  # раздел(ы) уже существуют, просто примонтировать


@dataclasses.dataclass
class DiskConfig:
    device: str = "/dev/sda"             # напр. /dev/nvme0n1
    mode: PartitionMode = PartitionMode.ERASE_DISK
    esp_size_mib: int = 512
    swap_size_mib: int = 0               # 0 = без свопа (или zram, см. SoftwareConfig)
    filesystem: str = "ext4"             # ext4 | btrfs | xfs


@dataclasses.dataclass
class LuksConfig:
    enabled: bool = False
    passphrase: str = ""
    cipher: str = "aes-xts-plain64"
    key_size: int = 512


@dataclasses.dataclass
class BootloaderConfig:
    kind: Bootloader = Bootloader.GRUB
    secure_boot: bool = False


@dataclasses.dataclass
class DesktopConfig:
    kind: Desktop = Desktop.KDE
    display_manager: str = "sddm"  # sddm | gdm


@dataclasses.dataclass
class NetworkConfig:
    hostname: str = "archbox"
    enable_networkmanager: bool = True


@dataclasses.dataclass
class UserConfig:
    username: str = "user"
    password: str = ""
    full_name: str = ""
    is_admin: bool = True
    root_password: str = ""


@dataclasses.dataclass
class SoftwareConfig:
    """Всё, что ставится/включается уже поверх базовой системы + DE."""
    enable_ufw: bool = True
    enable_zram: bool = True
    install_flatpak: bool = True
    install_pipewire: bool = True
    extra_packages: list[str] = dataclasses.field(default_factory=list)
    enable_bluetooth: bool = True
    install_common_apps: bool = True  # firefox, htop, git, etc.


@dataclasses.dataclass
class LocaleConfig:
    locale: str = "en_US.UTF-8"
    keymap: str = "us"
    timezone: str = "UTC"


@dataclasses.dataclass
class InstallConfig:
    disk: DiskConfig = dataclasses.field(default_factory=DiskConfig)
    luks: LuksConfig = dataclasses.field(default_factory=LuksConfig)
    bootloader: BootloaderConfig = dataclasses.field(default_factory=BootloaderConfig)
    desktop: DesktopConfig = dataclasses.field(default_factory=DesktopConfig)
    network: NetworkConfig = dataclasses.field(default_factory=NetworkConfig)
    user: UserConfig = dataclasses.field(default_factory=UserConfig)
    software: SoftwareConfig = dataclasses.field(default_factory=SoftwareConfig)
    locale: LocaleConfig = dataclasses.field(default_factory=LocaleConfig)
    mount_root: str = "/mnt"

    def validate(self) -> list[str]:
        """Возвращает список ошибок валидации (пусто = всё ок)."""
        errors = []
        if not self.disk.device:
            errors.append("Не выбран диск")
        if self.luks.enabled and not self.luks.passphrase:
            errors.append("Включён LUKS, но не задана парольная фраза")
        if not self.user.username:
            errors.append("Не задано имя пользователя")
        if self.bootloader.kind == Bootloader.UKI_EFISTUB and self.luks.enabled:
            # UKI+efistub без загрузчика требует, чтобы initramfs умел
            # спросить пароль LUKS (systemd-cryptenroll/sd-encrypt hook) —
            # это ограничение, а не запрет, просто предупреждаем.
            pass
        return errors
