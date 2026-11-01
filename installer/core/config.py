"""Installation configuration.

The live ISO bakes the edition into the image, so the wizard no longer asks
which desktop to install. Everything here is JSON-serialisable: the GTK
frontend writes a config to stdin of the privileged headless helper.
"""
from __future__ import annotations

import dataclasses
import json
import re
from enum import Enum, StrEnum
from typing import Any


class PartitionMode(StrEnum):
    ERASE_DISK = "erase_disk"
    USE_EXISTING = "use_existing"


class Firmware(StrEnum):
    AUTO = "auto"
    UEFI = "uefi"
    BIOS = "bios"


FILESYSTEMS = ("ext4", "btrfs", "xfs")
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")


@dataclasses.dataclass
class DiskConfig:
    device: str = ""
    mode: PartitionMode = PartitionMode.ERASE_DISK
    firmware: Firmware = Firmware.AUTO
    esp_size_mib: int = 512
    boot_size_mib: int = 1024
    swap_size_mib: int = 0
    filesystem: str = "ext4"


@dataclasses.dataclass
class LuksConfig:
    enabled: bool = False
    passphrase: str = ""


@dataclasses.dataclass
class UserConfig:
    username: str = "deblite"
    full_name: str = "DebLite User"
    password: str = ""
    is_admin: bool = True
    root_password: str = ""
    autologin: bool = False


@dataclasses.dataclass
class LocaleConfig:
    locale: str = "en_US.UTF-8"
    keymap: str = "us"
    timezone: str = "UTC"


@dataclasses.dataclass
class NetworkConfig:
    hostname: str = "deblite"


@dataclasses.dataclass
class InstallConfig:
    flavor: str = "unknown"
    disk: DiskConfig = dataclasses.field(default_factory=DiskConfig)
    luks: LuksConfig = dataclasses.field(default_factory=LuksConfig)
    user: UserConfig = dataclasses.field(default_factory=UserConfig)
    locale: LocaleConfig = dataclasses.field(default_factory=LocaleConfig)
    network: NetworkConfig = dataclasses.field(default_factory=NetworkConfig)

    mount_root: str = "/mnt"
    # Explicit squashfs path; empty means "autodetect from the live medium".
    source: str = ""
    # Escape hatches used by the test-suite and by rescue installs.
    skip_delive: bool = False
    keep_live_user: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []

        if self.disk.mode == PartitionMode.ERASE_DISK and not self.disk.device:
            errors.append("no target disk selected")
        if self.disk.mode == PartitionMode.ERASE_DISK and self.disk.device:
            if not self.disk.device.startswith("/dev/"):
                errors.append("target disk must be a /dev/ path")
        if self.disk.filesystem not in FILESYSTEMS:
            errors.append(f"unsupported filesystem: {self.disk.filesystem}")
        if self.disk.esp_size_mib < 100:
            errors.append("ESP must be at least 100 MiB")
        if self.disk.boot_size_mib < 256:
            errors.append("separate /boot must be at least 256 MiB")
        if self.disk.swap_size_mib < 0:
            errors.append("swap size cannot be negative")

        if self.luks.enabled and len(self.luks.passphrase) < 1:
            errors.append("LUKS is enabled but no passphrase was set")

        if not USERNAME_RE.match(self.user.username):
            errors.append("invalid username (lowercase letters, digits, _ and - only)")
        if self.user.username == "root":
            errors.append("the user account cannot be root")
        if len(self.user.password) < 1:
            errors.append("user password is required")
        if "\n" in self.user.password or "\n" in self.user.root_password:
            errors.append("passwords cannot contain newlines")
        if "\n" in self.luks.passphrase:
            errors.append("LUKS passphrase cannot contain newlines")

        if not HOSTNAME_RE.match(self.network.hostname):
            errors.append("invalid hostname")

        if not re.match(r"^[a-z]{2,3}_[A-Z]{2}\.UTF-8$", self.locale.locale):
            errors.append("locale must look like en_US.UTF-8")

        return errors

    # -- JSON -----------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return _jsonable(dataclasses.asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InstallConfig:
        data = data or {}
        disk = _build(DiskConfig, data.get("disk"))
        luks = _build(LuksConfig, data.get("luks"))
        user = _build(UserConfig, data.get("user"))
        locale = _build(LocaleConfig, data.get("locale"))
        network = _build(NetworkConfig, data.get("network"))
        return cls(
            flavor=str(data.get("flavor", "unknown")),
            disk=disk,
            luks=luks,
            user=user,
            locale=locale,
            network=network,
            mount_root=str(data.get("mount_root", "/mnt")),
            source=str(data.get("source", "")),
            skip_delive=bool(data.get("skip_delive", False)),
            keep_live_user=bool(data.get("keep_live_user", False)),
        )

    @classmethod
    def from_json(cls, raw: str) -> InstallConfig:
        return cls.from_dict(json.loads(raw))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _build(cls, data: dict[str, Any] | None):
    """Build a dataclass from a dict, coercing enums and ignoring unknown keys."""
    import typing

    data = data or {}
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if field.name not in data:
            continue
        value = data[field.name]
        field_type = hints.get(field.name, field.type)
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            value = field_type(value)
        elif field_type is int:
            value = int(value)
        elif field_type is bool:
            value = bool(value)
        elif field_type is str:
            value = str(value)
        kwargs[field.name] = value
    return cls(**kwargs)
