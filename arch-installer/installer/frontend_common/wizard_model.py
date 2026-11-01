"""
Общее описание "экранов" визарда, которое используют оба GUI (Kirigami и
GNOME/libadwaita) и CLI. Каждый UI сам рисует поля как умеет (QML Kirigami
Form vs Adw.PreferencesGroup vs текстовый prompt), но порядок экранов,
их id и то, какие поля InstallConfig они меняют — общие, чтобы визарды
не расходились логикой.

Screen.title и Field.label здесь — это КЛЮЧИ перевода (installer.i18n.tr),
а не готовый текст на каком-то одном языке. Перевод хранится отдельно в
installer/i18n/strings/<lang>.py — см. screen_title()/field_label() ниже.
"""
from __future__ import annotations

import dataclasses
from enum import Enum

from ..i18n import tr


class FieldKind(str, Enum):
    TEXT = "text"
    PASSWORD = "password"
    BOOL = "bool"
    CHOICE = "choice"
    INT = "int"


@dataclasses.dataclass
class Field:
    key: str            # dotted path в InstallConfig, напр. "disk.device"
    label: str           # ключ перевода, напр. "field.disk.device.label"
    kind: FieldKind
    choices: list[str] | None = None
    default: object = None


@dataclasses.dataclass
class Screen:
    id: str
    title: str           # ключ перевода, напр. "screen.disk.title"
    fields: list[Field]


def screen_title(screen: Screen) -> str:
    return tr(screen.title)


def field_label(field: Field) -> str:
    return tr(field.label)


# Локаль стоит сразу после приветствия и раньше диска: во-первых, это
# частый в других установщиках порядок (выбрал язык/регион — дальше всё
# остальное общается уже на нём), во-вторых, выбор locale.locale сразу же
# переключает язык самого установщика (см. cli/wizard.py и gui_gnome/main.py,
# где на изменение этого поля вызывается installer.i18n.set_language()).
WIZARD_SCREENS: list[Screen] = [
    Screen("locale", "screen.locale.title", [
        Field("locale.locale", "field.locale.locale.label", FieldKind.TEXT, default="en_US.UTF-8"),
        Field("locale.keymap", "field.locale.keymap.label", FieldKind.TEXT, default="us"),
        Field("locale.timezone", "field.locale.timezone.label", FieldKind.TEXT, default="UTC"),
        Field("network.hostname", "field.network.hostname.label", FieldKind.TEXT, default="archbox"),
    ]),
    Screen("disk", "screen.disk.title", [
        Field("disk.device", "field.disk.device.label", FieldKind.TEXT, default="/dev/sda"),
        Field("disk.filesystem", "field.disk.filesystem.label", FieldKind.CHOICE,
              choices=["ext4", "btrfs", "xfs"], default="ext4"),
        Field("disk.esp_size_mib", "field.disk.esp_size_mib.label", FieldKind.INT, default=512),
        Field("disk.swap_size_mib", "field.disk.swap_size_mib.label", FieldKind.INT, default=0),
    ]),
    Screen("luks", "screen.luks.title", [
        Field("luks.enabled", "field.luks.enabled.label", FieldKind.BOOL, default=False),
        Field("luks.passphrase", "field.luks.passphrase.label", FieldKind.PASSWORD),
    ]),
    Screen("bootloader", "screen.bootloader.title", [
        Field("bootloader.kind", "field.bootloader.kind.label", FieldKind.CHOICE,
              choices=["grub", "limine", "uki-efistub"], default="grub"),
    ]),
    Screen("desktop", "screen.desktop.title", [
        Field("desktop.kind", "field.desktop.kind.label", FieldKind.CHOICE,
              choices=["kde", "gnome", "none"], default="kde"),
    ]),
    Screen("user", "screen.user.title", [
        Field("user.username", "field.user.username.label", FieldKind.TEXT, default="user"),
        Field("user.password", "field.user.password.label", FieldKind.PASSWORD),
        Field("user.is_admin", "field.user.is_admin.label", FieldKind.BOOL, default=True),
        Field("user.root_password", "field.user.root_password.label", FieldKind.PASSWORD),
    ]),
    Screen("software", "screen.software.title", [
        Field("software.enable_ufw", "field.software.enable_ufw.label", FieldKind.BOOL, default=True),
        Field("software.enable_zram", "field.software.enable_zram.label", FieldKind.BOOL, default=True),
        Field("software.install_flatpak", "field.software.install_flatpak.label", FieldKind.BOOL, default=True),
        Field("software.install_pipewire", "field.software.install_pipewire.label", FieldKind.BOOL, default=True),
        Field("software.enable_bluetooth", "field.software.enable_bluetooth.label", FieldKind.BOOL, default=True),
        Field("software.install_common_apps", "field.software.install_common_apps.label",
              FieldKind.BOOL, default=True),
    ]),
    Screen("confirm", "screen.confirm.title", []),
]


def set_by_path(obj, dotted_key: str, value) -> None:
    parts = dotted_key.split(".")
    target = obj
    for p in parts[:-1]:
        target = getattr(target, p)
    setattr(target, parts[-1], value)


def get_by_path(obj, dotted_key: str):
    target = obj
    for p in dotted_key.split("."):
        target = getattr(target, p)
    return target
