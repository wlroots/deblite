from __future__ import annotations

from installer.i18n import get_language, language_for_locale, set_language, tr
from installer.i18n.strings.en import STRINGS as EN
from installer.i18n.strings.ru import STRINGS as RU


def test_english_has_all_ru_keys() -> None:
    missing = sorted(set(RU) - set(EN))
    assert missing == []


def test_fallback_and_formatting() -> None:
    set_language("en")
    assert tr("summary.disk", device="/dev/vda", firmware="uefi") == "Disk: /dev/vda (uefi)"
    assert tr("does.not.exist") == "does.not.exist"


def test_language_switch() -> None:
    set_language("ru")
    assert get_language() == "ru"
    assert tr("screen.disk.title") == "Диск и разметка"
    set_language("en")


def test_language_for_locale() -> None:
    assert language_for_locale("ru_RU.UTF-8") == "ru"
    assert language_for_locale("de_DE.UTF-8") == "en"
    assert language_for_locale("") == "en"
