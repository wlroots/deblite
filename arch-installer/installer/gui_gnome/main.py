"""
GNOME-фронтенд (GTK4 + libadwaita) для установщика.

Требует: python-gobject, gtk4, libadwaita.
    (Arch: pacman -S python-gobject gtk4 libadwaita)

Построен на Adw.NavigationView — штатном способе libadwaita делать
многостраничные мастера (как в "Параметры" GNOME или в gnome-initial-setup):
каждый экран — отдельная Adw.NavigationPage, кнопка "назад" и анимация
перехода рисуются самим NavigationView.

Страницы визарда строятся ЛЕНИВО, по одной, непосредственно перед push().
Это не только проще, но и нужно для локализации: язык установщика
переключается сразу после того, как пользователь выбрал локаль (первый
экран после приветствия), и все страницы, построенные ПОСЛЕ этого момента,
уже используют новый язык — а раньше построенные (приветствие, экран
локали) просто остаются такими, какими были показаны.

Вся логика установки — в installer.core, здесь только UI и вызов
run_pipeline() в фоновом потоке, чтобы не блокировать интерфейс.

Запуск:
    python -m installer.gui_gnome.main [--debug]
"""
from __future__ import annotations

import argparse
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib  # noqa: E402

from ..core.config import InstallConfig
from ..core.executor import Executor, InstallerError
from ..core.steps import run_pipeline
from ..frontend_common.summary import summarize
from ..frontend_common.wizard_model import (
    WIZARD_SCREENS, FieldKind, field_label, screen_title, set_by_path,
)
from ..i18n import language_for_locale, set_language, tr

# Экраны с полями, в порядке визарда (без служебного "confirm" — он строится отдельно)
DATA_SCREENS = [s for s in WIZARD_SCREENS if s.fields]


def _wrap_with_header(body: Gtk.Widget) -> Adw.ToolbarView:
    """Оборачивает содержимое страницы в HeaderBar — так NavigationView
    сам рисует кнопку "назад", когда страница не первая в стеке."""
    view = Adw.ToolbarView()
    view.add_top_bar(Adw.HeaderBar())
    view.set_content(body)
    return view


class InstallerWindow(Adw.ApplicationWindow):
    def __init__(self, app, debug: bool):
        super().__init__(application=app, title=tr("welcome.title"))
        self.set_default_size(820, 620)
        self.cfg = InstallConfig()
        self.debug = debug

        self.nav_view = Adw.NavigationView()
        self.set_content(self.nav_view)
        self.nav_view.push(self._build_welcome_page())

    # ---------------------------------------------------------------- welcome
    def _build_welcome_page(self) -> Adw.NavigationPage:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, vexpand=True)

        icon = Gtk.Image(icon_name="drive-harddisk-system-symbolic", pixel_size=96)
        box.append(icon)

        title = Gtk.Label(label=tr("welcome.title"))
        title.add_css_class("title-1")
        box.append(title)

        body_text = tr("welcome.body") + "\n" + (
            tr("welcome.body.debug") if self.debug else tr("welcome.body.warning")
        )
        desc = Gtk.Label(label=body_text, wrap=True, justify=Gtk.Justification.CENTER,
                          max_width_chars=50)
        if self.debug:
            desc.add_css_class("warning")
        box.append(desc)

        start_btn = Gtk.Button(label=tr("welcome.start"))
        start_btn.add_css_class("suggested-action")
        start_btn.add_css_class("pill")
        start_btn.set_halign(Gtk.Align.CENTER)
        # Первый экран данных (по индексу 0 в DATA_SCREENS) строится только
        # сейчас, по клику — а не заранее, см. docstring модуля.
        start_btn.connect("clicked", lambda _b: self.nav_view.push(self._build_screen_page(0)))
        box.append(start_btn)

        page = Adw.NavigationPage(title=tr("welcome.title"), tag="welcome")
        page.set_child(_wrap_with_header(box))
        return page

    # ----------------------------------------------------------- data screens
    def _build_screen_page(self, screen_index: int) -> Adw.NavigationPage:
        screen = DATA_SCREENS[screen_index]
        is_last = screen_index == len(DATA_SCREENS) - 1

        prefs = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=screen_title(screen))
        for field in screen.fields:
            group.add(self._make_row(field))
        prefs.add(group)

        next_btn = Gtk.Button(
            label=tr("nav.review_and_install") if is_last else tr("nav.next")
        )
        next_btn.add_css_class("suggested-action")
        next_btn.add_css_class("pill")
        next_btn.set_halign(Gtk.Align.END)
        next_btn.set_margin_top(6)
        next_btn.set_margin_bottom(12)
        next_btn.set_margin_end(12)

        def go_next(_b, idx=screen_index, last=is_last):
            if last:
                self.nav_view.push(self._build_confirm_page())
            else:
                self.nav_view.push(self._build_screen_page(idx + 1))

        next_btn.connect("clicked", go_next)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        box.append(prefs)
        box.append(next_btn)

        page = Adw.NavigationPage(title=screen_title(screen), tag=screen.id)
        page.set_child(_wrap_with_header(box))
        return page

    def _make_row(self, field) -> Adw.PreferencesRow:
        label = field_label(field)

        if field.kind == FieldKind.BOOL:
            row = Adw.SwitchRow(title=label, active=bool(field.default))
            row.connect("notify::active", lambda r, _p: set_by_path(self.cfg, field.key, r.get_active()))
            return row

        if field.kind == FieldKind.CHOICE:
            row = Adw.ComboRow(title=label)
            model = Gtk.StringList.new(field.choices or [])
            row.set_model(model)
            if field.default in (field.choices or []):
                row.set_selected(field.choices.index(field.default))
                set_by_path(self.cfg, field.key, field.default)

            def on_selected(r, _p):
                idx = r.get_selected()
                if 0 <= idx < len(field.choices):
                    set_by_path(self.cfg, field.key, field.choices[idx])

            row.connect("notify::selected", on_selected)
            return row

        if field.kind == FieldKind.PASSWORD:
            row = Adw.PasswordEntryRow(title=label)
            row.connect("changed", lambda r: set_by_path(self.cfg, field.key, r.get_text()))
            return row

        # TEXT / INT -> Adw.EntryRow
        row = Adw.EntryRow(title=label)
        if field.default is not None:
            row.set_text(str(field.default))
            set_by_path(self.cfg, field.key, field.default)

        def on_changed(r):
            value = r.get_text()
            if field.kind == FieldKind.INT:
                try:
                    value = int(value)
                except ValueError:
                    return
            set_by_path(self.cfg, field.key, value)
            # Локаль — первое поле первого экрана. Как только она известна,
            # переключаем язык установщика: все страницы, построенные ПОСЛЕ
            # этого момента (следующие "Далее"), уже будут на новом языке.
            if field.key == "locale.locale" and value:
                set_language(language_for_locale(str(value)))

        row.connect("changed", on_changed)
        return row

    # -------------------------------------------------------------- confirm
    def _build_confirm_page(self) -> Adw.NavigationPage:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=18, margin_bottom=18, margin_start=18, margin_end=18)

        if self.debug:
            banner = Adw.Banner(title=tr("confirm.debug_notice"), revealed=True)
            box.append(banner)

        summary_label = Gtk.Label(label=summarize(self.cfg), wrap=True, xalign=0, selectable=True)
        summary_label.add_css_class("card")
        summary_label.set_margin_top(6)
        summary_label.set_margin_bottom(6)
        summary_label.set_margin_start(12)
        summary_label.set_margin_end(12)
        box.append(summary_label)

        install_btn = Gtk.Button(
            label=tr("confirm.install_dryrun") if self.debug else tr("confirm.install")
        )
        install_btn.add_css_class("suggested-action")
        install_btn.add_css_class("pill")
        install_btn.set_halign(Gtk.Align.END)
        box.append(install_btn)

        log_heading = Gtk.Label(label=tr("confirm.log"), xalign=0, visible=False)
        log_heading.add_css_class("title-4")
        box.append(log_heading)

        log_view = Gtk.TextView(editable=False, monospace=True, vexpand=True)
        log_scroll = Gtk.ScrolledWindow(vexpand=True, visible=False)
        log_scroll.set_child(log_view)
        box.append(log_scroll)

        def append_log(line: str) -> None:
            buf = log_view.get_buffer()
            buf.insert(buf.get_end_iter(), line + "\n")

        def on_install_clicked(_btn) -> None:
            errors = self.cfg.validate()
            if errors:
                log_scroll.set_visible(True)
                log_heading.set_visible(True)
                append_log("; ".join(errors))
                return

            install_btn.set_sensitive(False)
            log_scroll.set_visible(True)
            log_heading.set_visible(True)
            ex = Executor(debug=self.debug, log_callback=lambda line: GLib.idle_add(append_log, line))

            def on_step(step, i, total):
                GLib.idle_add(append_log, f"\n[{i}/{total}] {step.title}...")

            def worker():
                try:
                    run_pipeline(self.cfg, ex, on_step=on_step)
                    GLib.idle_add(append_log, "\n✔ " + tr("cli.done_dryrun" if self.debug else "cli.done"))
                except InstallerError as exc:
                    GLib.idle_add(append_log, "\n✘ " + tr("cli.error", message=str(exc)))
                finally:
                    GLib.idle_add(install_btn.set_sensitive, True)

            threading.Thread(target=worker, daemon=True).start()

        install_btn.connect("clicked", on_install_clicked)

        page = Adw.NavigationPage(title=tr("screen.confirm.title"), tag="confirm")
        page.set_child(_wrap_with_header(box))
        return page


class InstallerApp(Adw.Application):
    def __init__(self, debug: bool):
        super().__init__(application_id="org.archinstaller.gnome")
        self.debug = debug

    def do_activate(self):
        win = InstallerWindow(self, self.debug)
        win.present()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "--dry-run", dest="debug", action="store_true")
    args, gtk_args = parser.parse_known_args(argv)

    app = InstallerApp(debug=args.debug)
    return app.run([sys.argv[0], *gtk_args])


if __name__ == "__main__":
    raise SystemExit(main())
