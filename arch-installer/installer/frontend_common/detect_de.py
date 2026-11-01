"""Определяет, какое окружение сейчас запущено (live-ISO), чтобы
bin/arch-installer мог автоматически выбрать "родной" UI —
Kirigami/Qt под KDE, libadwaita/GTK под GNOME, иначе — CLI-визард."""
from __future__ import annotations

import os


def detect() -> str:
    """Возвращает 'kde' | 'gnome' | 'unknown'."""
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    combined = f"{xdg} {session}"

    if "kde" in combined or "plasma" in combined:
        return "kde"
    if "gnome" in combined:
        return "gnome"
    return "unknown"
