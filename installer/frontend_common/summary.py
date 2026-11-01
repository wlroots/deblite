"""Human-readable summary of an InstallConfig (shared by CLI and GTK)."""
from __future__ import annotations

from ..core.config import InstallConfig
from ..core.util import human_size
from ..i18n import tr


def summarize(cfg: InstallConfig) -> list[str]:
    yes_no = lambda v: tr("summary.yes") if v else tr("summary.no")  # noqa: E731
    lines = [
        tr("summary.disk", device=cfg.disk.device or "—", firmware=cfg.disk.firmware.value),
        tr("summary.filesystem", filesystem=cfg.disk.filesystem),
        tr("summary.esp", size=cfg.disk.esp_size_mib),
    ]
    if cfg.luks.enabled:
        lines.append(tr("summary.boot", size=cfg.disk.boot_size_mib))
    if cfg.disk.swap_size_mib:
        lines.append(tr("summary.swap", size=cfg.disk.swap_size_mib))
    else:
        lines.append(tr("summary.no_swap"))
    lines.append(tr("summary.luks") if cfg.luks.enabled else tr("summary.no_luks"))
    lines.append(
        tr(
            "summary.user",
            username=cfg.user.username,
            full_name=cfg.user.full_name or cfg.user.username,
        )
    )
    lines.append(tr("summary.admin", value=yes_no(cfg.user.is_admin)))
    lines.append(tr("summary.hostname", hostname=cfg.network.hostname))
    lines.append(
        tr(
            "summary.locale",
            locale=cfg.locale.locale,
            keymap=cfg.locale.keymap,
            timezone=cfg.locale.timezone,
        )
    )
    return lines


def disk_size(size: int) -> str:
    return human_size(size)
