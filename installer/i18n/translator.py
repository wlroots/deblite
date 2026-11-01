"""Tiny gettext-free translation layer.

English is the source of truth. Other languages only translate the keys they
care about; anything missing falls back to English. Adding a language means
adding ``installer/i18n/strings/<code>.py`` and one entry below.
"""
from __future__ import annotations

import importlib

DEFAULT_LANGUAGE = "en"

AVAILABLE_LANGUAGES = {
    "en": "English",
    "ru": "Русский",
}

_current_language = DEFAULT_LANGUAGE
_cache: dict[str, dict[str, str]] = {}


def _load(lang: str) -> dict[str, str]:
    if lang not in _cache:
        try:
            module = importlib.import_module(f"{__package__}.strings.{lang}")
            _cache[lang] = dict(getattr(module, "STRINGS", {}))
        except ModuleNotFoundError:
            _cache[lang] = {}
    return _cache[lang]


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language


def language_for_locale(locale: str) -> str:
    code = (locale or "").split("_", 1)[0].split("-", 1)[0].lower()
    return code if code in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE


def tr(key: str, **kwargs) -> str:
    text = _load(_current_language).get(key)
    if text is None:
        text = _load(DEFAULT_LANGUAGE).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text
