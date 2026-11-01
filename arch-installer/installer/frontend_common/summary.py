"""Человекочитаемая сводка InstallConfig для последнего экрана визарда
(общая для Kirigami и GNOME, чтобы текст не расходился). Локализована
через installer.i18n — см. ключи summary.* в installer/i18n/strings/*.py."""
from __future__ import annotations

from ..core.config import InstallConfig
from ..i18n import tr


def summarize(cfg: InstallConfig) -> str:
    esp = tr("summary.esp", size=cfg.disk.esp_size_mib)
    swap = tr("summary.swap", size=cfg.disk.swap_size_mib) if cfg.disk.swap_size_mib else ""

    software_names = [
        name for enabled, name in [
            (cfg.software.enable_ufw, "UFW"),
            (cfg.software.enable_zram, "zram"),
            (cfg.software.install_flatpak, "Flatpak"),
            (cfg.software.install_pipewire, "PipeWire"),
            (cfg.software.enable_bluetooth, "Bluetooth"),
            (cfg.software.install_common_apps, tr("field.software.install_common_apps.label")),
        ] if enabled
    ]
    software_text = ", ".join(software_names) if software_names else tr("summary.software.none")

    lines = [
        tr("summary.disk", device=cfg.disk.device, fs=cfg.disk.filesystem, esp=esp, swap=swap),
        tr("summary.encryption",
           status=tr("summary.encryption.on" if cfg.luks.enabled else "summary.encryption.off")),
        tr("summary.bootloader", kind=cfg.bootloader.kind.value),
        tr("summary.desktop", kind=cfg.desktop.kind.value),
        tr("summary.locale", locale=cfg.locale.locale, timezone=cfg.locale.timezone,
           keymap=cfg.locale.keymap),
        tr("summary.hostname", hostname=cfg.network.hostname),
        tr("summary.user", username=cfg.user.username,
           admin=tr("summary.user.admin") if cfg.user.is_admin else ""),
        tr("summary.software", list=software_text),
    ]
    return "\n".join(lines)
