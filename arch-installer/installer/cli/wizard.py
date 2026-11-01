from __future__ import annotations

import argparse
import sys

from ..core.config import InstallConfig
from ..core.executor import Executor, InstallerError
from ..core.steps import run_pipeline
from ..frontend_common.summary import summarize
from ..frontend_common.wizard_model import (
    WIZARD_SCREENS, FieldKind, field_label, get_by_path, screen_title, set_by_path,
)
from ..i18n import language_for_locale, set_language, tr


def _prompt_field(field, cfg: InstallConfig, non_interactive: bool) -> None:
    current = get_by_path(cfg, field.key)
    default = field.default if field.default is not None else current
    label = field_label(field)

    if non_interactive:
        return  # оставляем значения по умолчанию из InstallConfig (уже верного типа, вкл. Enum)

    if field.kind == FieldKind.BOOL:
        raw = input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        value = bool(default) if raw == "" else raw in ("y", "yes", "д", "да")
    elif field.kind == FieldKind.CHOICE:
        choices = field.choices or []
        raw = input(f"{label} ({'/'.join(choices)}) [{default}]: ").strip()
        value = raw or default
    elif field.kind == FieldKind.INT:
        raw = input(f"{label} [{default}]: ").strip()
        value = int(raw) if raw else int(default)
    elif field.kind == FieldKind.PASSWORD:
        import getpass
        value = getpass.getpass(f"{label}: ")
        if not value:
            return  # не перезаписываем, если пусто
    else:
        raw = input(f"{label} [{default}]: ").strip()
        value = raw or default

    set_by_path(cfg, field.key, value)

    # Как только известна выбранная локаль — сразу переключаем язык
    # самого установщика на неё (если для языка есть файл перевода;
    # иначе остаёмся на английском).
    if field.key == "locale.locale" and value:
        set_language(language_for_locale(str(value)))


def run_wizard(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="arch-installer",
        description="Установщик Arch Linux (CLI-режим / общий движок для GUI).",
    )
    parser.add_argument(
        "--debug", "--dry-run", dest="debug", action="store_true",
        help="Режим отладки: ничего не пишется на диск, все команды только логируются.",
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Не задавать вопросы, использовать значения по умолчанию (для тестов).",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Не спрашивать финальное подтверждение перед установкой.",
    )
    args = parser.parse_args(argv)

    cfg = InstallConfig()

    print(tr("cli.title"))
    if args.debug:
        print(tr("cli.debug_banner"))

    for screen in WIZARD_SCREENS:
        if screen.id == "confirm":
            continue
        print(f"\n--- {screen_title(screen)} ---")
        for field in screen.fields:
            _prompt_field(field, cfg, args.non_interactive)

    errors = cfg.validate()
    if errors:
        print(f"\n{tr('cli.config_errors')}")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"\n{tr('cli.final_config')}")
    print(summarize(cfg))

    if not args.yes and not args.non_interactive:
        confirm = input(f"\n{tr('cli.confirm_prompt')}").strip().lower()
        if confirm not in ("y", "yes", "д", "да"):
            print(tr("cli.cancelled"))
            return 1

    ex = Executor(debug=args.debug)

    def on_step(step, i, total):
        print("\n" + tr("cli.step", index=i, total=total, title=step.title))

    try:
        run_pipeline(cfg, ex, on_step=on_step)
    except InstallerError as exc:
        print(f"\n{tr('cli.error', message=str(exc))}", file=sys.stderr)
        return 1

    print(f"\n{tr('cli.done_dryrun') if args.debug else tr('cli.done')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_wizard())
