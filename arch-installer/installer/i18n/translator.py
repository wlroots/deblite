"""
Лёгкий движок локализации установщика.

Язык по умолчанию — английский (installer/i18n/strings/en.py). Любой другой
язык — отдельный файл в installer/i18n/strings/<code>.py с одним словарём
STRINGS = {"ключ": "перевод"}. Переводить нужно только те ключи, которые
хочется перевести — всё остальное само подхватывается из английского.

Добавить новый язык = создать installer/i18n/strings/<code>.py и одну
строку в AVAILABLE_LANGUAGES ниже. Никакой сборки .mo/.po не нужно —
это сознательное упрощение вместо полноценного gettext, чтобы не тащить
инструментарий сборки ради пары языков; при желании легко заменить на
gettext, не трогая вызывающий код (tr() как точка входа не изменится).
"""
from __future__ import annotations

import importlib

DEFAULT_LANGUAGE = "en"

# code -> отображаемое имя (для будущего выпадающего списка "язык установщика")
AVAILABLE_LANGUAGES = {
    "en": "English",
    "ru": "Русский",
}

_current_language = DEFAULT_LANGUAGE
_cache: dict[str, dict[str, str]] = {}


def _load(lang: str) -> dict[str, str]:
    if lang not in _cache:
        try:
            module = importlib.import_module(f"installer.i18n.strings.{lang}")
        except ImportError:
            module = importlib.import_module(f"installer.i18n.strings.{DEFAULT_LANGUAGE}")
        _cache[lang] = module.STRINGS
    return _cache[lang]


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language


def tr(key: str, **kwargs) -> str:
    """Переводит ключ на текущий язык; если ключа нет — берёт английский;
    если и там нет — возвращает сам ключ (чтобы не падать в рантайме,
    а сразу было видно в UI, что перевод забыли добавить)."""
    text = _load(_current_language).get(key)
    if text is None:
        text = _load(DEFAULT_LANGUAGE).get(key, key)
    return text.format(**kwargs) if kwargs else text


def language_for_locale(locale: str) -> str:
    """'ru_RU.UTF-8' -> 'ru'; 'en_US.UTF-8' -> 'en'; неизвестное -> DEFAULT_LANGUAGE."""
    lang = locale.split("_")[0].split(".")[0].strip().lower()
    return lang if lang in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE
