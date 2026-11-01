"""Command-line and headless entry point.

The graphical frontend never touches the disk itself: it writes a JSON config
and executes::

    sudo -n /usr/bin/deblite-installer --headless --config - --yes

This module is therefore the single privileged installation path.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys

from .. import __version__
from ..core.config import InstallConfig
from ..core.executor import Executor, InstallerError
from ..core.steps import run_pipeline
from ..core.util import lsblk_disks
from ..frontend_common.summary import summarize
from ..frontend_common.wizard_model import (
    WIZARD_SCREENS,
    Field,
    FieldKind,
    field_label,
    get_by_path,
    set_by_path,
)
from ..i18n import language_for_locale, set_language, tr


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.lang:
        set_language(args.lang)
    else:
        set_language(language_for_locale(os.environ.get("LANG", "")))

    if args.list_disks:
        print(json.dumps(lsblk_disks(), indent=2))
        return 0

    if args.gui:
        return _run_gui(args)

    if args.headless:
        return _run_headless(args)

    if not sys.stdin.isatty():
        print("error: interactive mode needs a terminal; use --headless --config", file=sys.stderr)
        return 2

    if os.geteuid() != 0 and not args.debug:
        print(tr("cli.need_root"), file=sys.stderr)
        return 1

    cfg = _interactive_wizard(args)
    return _run(cfg, debug=args.debug)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deblite-installer",
        description="DebLite installer (partition, copy rootfs, configure GRUB).",
    )
    parser.add_argument("--headless", action="store_true", help="run without a UI")
    parser.add_argument("-c", "--config", help="JSON config file, or - for stdin")
    parser.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument(
        "--debug",
        "--dry-run",
        dest="debug",
        action="store_true",
        help="log every command without changing anything",
    )
    parser.add_argument("--gui", action="store_true", help="launch the GTK4 frontend")
    parser.add_argument("--list-disks", action="store_true", help="print disks as JSON and exit")
    parser.add_argument("--source", help="path to filesystem.squashfs")
    parser.add_argument("--flavor", help="edition name (normally baked into the ISO)")
    parser.add_argument("--lang", choices=["en", "ru"], help="UI language")
    parser.add_argument("--version", action="version", version=f"deblite-installer {__version__}")
    return parser


# -- headless -----------------------------------------------------------
def _run_headless(args) -> int:
    if not args.config:
        print("error: --headless requires --config", file=sys.stderr)
        return 2

    try:
        raw = sys.stdin.read() if args.config == "-" else open(args.config).read()
        cfg = InstallConfig.from_json(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"error: cannot read config: {exc}", file=sys.stderr)
        return 2

    if args.source:
        cfg.source = args.source
    if args.flavor:
        cfg.flavor = args.flavor

    set_language(language_for_locale(cfg.locale.locale))

    if os.geteuid() != 0 and not args.debug:
        print(tr("cli.need_root"), file=sys.stderr)
        return 1

    if not args.yes and sys.stdin.isatty():
        print("\n".join(summarize(cfg)))
        answer = input("Proceed? [y/N]: ").strip().lower()
        if answer not in ("y", "yes", "д", "да"):
            return 1

    return _run(cfg, debug=args.debug)


def _run(cfg: InstallConfig, *, debug: bool) -> int:
    errors = cfg.validate()
    if errors:
        print(tr("cli.invalid_config", errors="\n".join(f"  - {e}" for e in errors)))
        return 2

    if debug:
        print(tr("cli.dry_run"), file=sys.stderr)

    ex = Executor(debug=debug)

    def on_step(step, index, total):
        print(f"\n==> {tr('progress.step', index=index, total=total, title=step.title)}", flush=True)

    try:
        run_pipeline(cfg, ex, on_step=on_step)
    except (InstallerError, ValueError, OSError) as exc:
        print(tr("cli.failure", error=exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130

    print(tr("cli.success"))
    return 0


# -- interactive --------------------------------------------------------
def _interactive_wizard(args) -> InstallConfig:
    cfg = InstallConfig()
    if args.source:
        cfg.source = args.source
    if args.flavor:
        cfg.flavor = args.flavor

    print()
    print("=" * 60)
    print(tr("welcome.title"))
    print("=" * 60)
    print(tr("welcome.body"))
    print(tr("welcome.body.warning"))
    if args.debug:
        print(tr("welcome.body.debug"))
    input(f"\n{tr('welcome.start')} [Enter] ")

    disks = lsblk_disks()
    for screen in WIZARD_SCREENS:
        print(f"\n--- {screen.title} ---")
        for field in screen.fields:
            _ask_field(cfg, field, disks)

    return cfg


def _ask_field(cfg: InstallConfig, field: Field, disks: list[dict]) -> None:
    label = field_label(field)
    current = get_by_path(cfg, field.key)

    if field.kind == FieldKind.BOOL:
        default = bool(current)
        raw = input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        value = default if raw == "" else raw in ("y", "yes", "д", "да")
        set_by_path(cfg, field.key, value)
        return

    if field.kind == FieldKind.CHOICE:
        choices = field.choices
        if field.key == "disk.device":
            choices = _disk_choices(disks)
        if not choices:
            return
        print(label + ":")
        for index, choice in enumerate(choices, start=1):
            marker = " (default)" if str(choice) == str(current) else ""
            print(f"  {index}) {choice}{marker}")
        raw = input(f"{tr('cli.choose')} [1-{len(choices)}]: ").strip()
        if raw:
            try:
                value = choices[int(raw) - 1]
            except (ValueError, IndexError):
                print(tr("cli.invalid_choice"))
                return _ask_field(cfg, field, disks)
        else:
            value = current
        set_by_path(cfg, field.key, value)
        return

    if field.kind == FieldKind.INT:
        while True:
            raw = input(f"{label} [{current}]: ").strip()
            if raw == "":
                return
            try:
                value = int(raw)
            except ValueError:
                print(tr("cli.required"))
                continue
            if field.minimum is not None and value < field.minimum:
                print(f">= {field.minimum}")
                continue
            if field.maximum is not None and value > field.maximum:
                print(f"<= {field.maximum}")
                continue
            set_by_path(cfg, field.key, value)
            return

    if field.kind == FieldKind.PASSWORD:
        value = getpass.getpass(f"{label}: ")
        if field.key == "luks.passphrase" and value:
            confirm = getpass.getpass(f"{tr('field.luks.passphrase_confirm.label')}: ")
            while confirm != value:
                print(tr("cli.confirm_password"))
                value = getpass.getpass(f"{label}: ")
                confirm = getpass.getpass(f"{tr('field.luks.passphrase_confirm.label')}: ")
        if field.key == "user.password" and value:
            confirm = getpass.getpass(f"{tr('field.user.password_confirm.label')}: ")
            while confirm != value:
                print(tr("cli.confirm_password"))
                value = getpass.getpass(f"{label}: ")
                confirm = getpass.getpass(f"{tr('field.user.password_confirm.label')}: ")
        set_by_path(cfg, field.key, value)
        return

    raw = input(f"{label} [{current}]: ").strip()
    if raw:
        set_by_path(cfg, field.key, raw)


def _disk_choices(disks: list[dict]) -> list[str]:
    if not disks:
        print(tr("disk.none"))
        return []
    return [d["device"] for d in disks]


def _run_gui(args) -> int:
    try:
        from ..gui_gtk.main import run
    except ImportError as exc:
        print(f"error: GTK frontend unavailable: {exc}", file=sys.stderr)
        return 1
    return run(debug=args.debug, source=args.source, flavor=args.flavor)


if __name__ == "__main__":
    raise SystemExit(main())
