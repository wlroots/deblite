"""Detect the running desktop so the launcher can pick a sensible UI."""
from __future__ import annotations

import os


def detect() -> str:
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    combined = f"{xdg} {session}"

    if "kde" in combined or "plasma" in combined:
        return "kde"
    if "gnome" in combined:
        return "gnome"
    if "xfce" in combined:
        return "xfce"
    if "cinnamon" in combined:
        return "cinnamon"
    return "unknown"


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
