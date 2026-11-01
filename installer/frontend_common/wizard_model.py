"""Shared description of the wizard screens used by the CLI and GTK frontend."""
from __future__ import annotations

import dataclasses
from enum import Enum, StrEnum

from ..i18n import tr


class FieldKind(StrEnum):
    TEXT = "text"
    PASSWORD = "password"
    BOOL = "bool"
    CHOICE = "choice"
    INT = "int"


@dataclasses.dataclass
class Field:
    key: str
    label: str
    kind: FieldKind
    choices: list[str] | None = None
    minimum: int | None = None
    maximum: int | None = None
    suffix: str = ""


@dataclasses.dataclass
class Screen:
    id: str
    title_key: str
    fields: list[Field]

    @property
    def title(self) -> str:
        return tr(self.title_key)


WIZARD_SCREENS: list[Screen] = [
    Screen(
        "locale",
        "screen.locale.title",
        [
            Field(
                "locale.locale",
                "field.locale.locale.label",
                FieldKind.CHOICE,
                [
                    "en_US.UTF-8",
                    "ru_RU.UTF-8",
                    "de_DE.UTF-8",
                    "fr_FR.UTF-8",
                    "es_ES.UTF-8",
                    "pt_BR.UTF-8",
                    "pl_PL.UTF-8",
                    "uk_UA.UTF-8",
                ],
            ),
            Field(
                "locale.keymap",
                "field.locale.keymap.label",
                FieldKind.CHOICE,
                ["us", "ru", "de", "fr", "es", "pt", "pl", "ua", "gb"],
            ),
            Field("locale.timezone", "field.locale.timezone.label", FieldKind.TEXT),
        ],
    ),
    Screen(
        "disk",
        "screen.disk.title",
        [
            Field("disk.device", "field.disk.device.label", FieldKind.CHOICE),
            Field(
                "disk.firmware",
                "field.disk.firmware.label",
                FieldKind.CHOICE,
                ["auto", "uefi", "bios"],
            ),
            Field(
                "disk.filesystem",
                "field.disk.filesystem.label",
                FieldKind.CHOICE,
                ["ext4", "btrfs", "xfs"],
            ),
            Field(
                "disk.esp_size_mib",
                "field.disk.esp_size_mib.label",
                FieldKind.INT,
                minimum=100,
                maximum=4096,
            ),
            Field(
                "disk.boot_size_mib",
                "field.disk.boot_size_mib.label",
                FieldKind.INT,
                minimum=256,
                maximum=8192,
            ),
            Field(
                "disk.swap_size_mib",
                "field.disk.swap_size_mib.label",
                FieldKind.INT,
                minimum=0,
                maximum=262144,
            ),
        ],
    ),
    Screen(
        "luks",
        "screen.luks.title",
        [
            Field("luks.enabled", "field.luks.enabled.label", FieldKind.BOOL),
            Field("luks.passphrase", "field.luks.passphrase.label", FieldKind.PASSWORD),
        ],
    ),
    Screen(
        "user",
        "screen.user.title",
        [
            Field("user.username", "field.user.username.label", FieldKind.TEXT),
            Field("user.full_name", "field.user.full_name.label", FieldKind.TEXT),
            Field("user.password", "field.user.password.label", FieldKind.PASSWORD),
            Field("user.root_password", "field.user.root_password.label", FieldKind.PASSWORD),
            Field("user.is_admin", "field.user.is_admin.label", FieldKind.BOOL),
            Field("user.autologin", "field.user.autologin.label", FieldKind.BOOL),
            Field("network.hostname", "field.network.hostname.label", FieldKind.TEXT),
        ],
    ),
]


def get_by_path(obj, path: str):
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def set_by_path(obj, path: str, value) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    current = getattr(obj, parts[-1])
    if isinstance(current, Enum):
        value = type(current)(value)
    elif isinstance(current, bool):
        value = _as_bool(value)
    elif isinstance(current, int):
        value = int(value)
    setattr(obj, parts[-1], value)


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on", "да")
    return bool(value)


def screen_title(screen: Screen) -> str:
    return tr(screen.title_key)


def field_label(field: Field) -> str:
    return tr(field.label)


def get_screen(screen_id: str) -> Screen | None:
    for screen in WIZARD_SCREENS:
        if screen.id == screen_id:
            return screen
    return None
