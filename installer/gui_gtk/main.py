"""GTK4 + libadwaita frontend.

The GUI runs as the unprivileged live user. It never partitions or writes
anything itself: it collects a JSON config and asks the privileged helper to
run the pipeline::

    sudo -n /usr/bin/deblite-installer --headless --config - --yes

With ``--debug`` the pipeline runs in-process in dry-run mode instead, which
makes the UI testable on a normal workstation.
"""
from __future__ import annotations

import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ..core.config import Firmware, InstallConfig  # noqa: E402
from ..core.executor import Executor  # noqa: E402
from ..core.steps import run_pipeline  # noqa: E402
from ..core.util import human_size, lsblk_disks  # noqa: E402
from ..frontend_common.summary import summarize  # noqa: E402
from ..i18n import language_for_locale, set_language, tr  # noqa: E402

FIRMWARE_VALUES = ["auto", "uefi", "bios"]
FILESYSTEM_VALUES = ["ext4", "btrfs", "xfs"]


class DebLiteWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, debug: bool, source: str, flavor: str):
        super().__init__(application=app, title=tr("app.name"))
        self.set_default_size(920, 720)

        self.debug = debug
        self.source = source
        self.flavor = flavor
        self.cfg = InstallConfig()
        if source:
            self.cfg.source = source
        if flavor:
            self.cfg.flavor = flavor

        self.widgets: dict[str, object] = {}
        self.disk_devices: list[str] = []
        self._installing = False
        self._pulse_id = 0

        self.nav = Adw.NavigationView()
        self.set_content(self.nav)
        self.nav.push(self._build_welcome())

    # -- page scaffolding ----------------------------------------------
    def _toolbar_page(self, title: str, content: Gtk.Widget, on_next=None, next_label=None):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))
        toolbar.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(content)
        toolbar.set_content(scrolled)

        if on_next is not None:
            bar = Gtk.Box(spacing=8)
            bar.set_margin_top(12)
            bar.set_margin_bottom(12)
            bar.set_margin_start(12)
            bar.set_margin_end(12)
            bar.set_halign(Gtk.Align.END)

            back = Gtk.Button(label=tr("gui.back"))
            back.connect("clicked", lambda *_: self.nav.pop())
            bar.append(back)

            nxt = Gtk.Button(label=next_label or tr("gui.next"))
            nxt.add_css_class("suggested-action")
            nxt.connect("clicked", lambda *_: on_next())
            bar.append(nxt)

            toolbar.add_bottom_bar(bar)

        return Adw.NavigationPage(child=toolbar, title=title)

    def _group(self, page: Adw.PreferencesPage, title: str | None = None) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=title) if title else Adw.PreferencesGroup()
        page.add(group)
        return group

    def _alert(self, message: str) -> None:
        dialog = Adw.AlertDialog(heading=tr("gui.error"), body=message)
        dialog.add_response("ok", tr("gui.close"))
        dialog.set_default_response("ok")
        dialog.present(self)

    # -- welcome --------------------------------------------------------
    def _build_welcome(self) -> Adw.NavigationPage:
        status = Adw.StatusPage()
        status.set_icon_name("drive-harddisk-symbolic")
        status.set_title(tr("welcome.title"))
        body = tr("welcome.body") + "\n\n" + tr("welcome.body.warning")
        if self.debug:
            body += "\n\n" + tr("welcome.body.debug")
        status.set_description(body)

        button = Gtk.Button(label=tr("welcome.start"))
        button.add_css_class("suggested-action")
        button.add_css_class("pill")
        button.set_halign(Gtk.Align.CENTER)
        button.connect("clicked", lambda *_: self.nav.push(self._build_locale()))
        status.set_child(button)

        return Adw.NavigationPage(child=status, title=tr("welcome.title"))

    # -- locale ---------------------------------------------------------
    def _build_locale(self) -> Adw.NavigationPage:
        page = Adw.PreferencesPage()
        group = self._group(page, tr("screen.locale.title"))

        locales = [
            "en_US.UTF-8",
            "ru_RU.UTF-8",
            "de_DE.UTF-8",
            "fr_FR.UTF-8",
            "es_ES.UTF-8",
            "pt_BR.UTF-8",
            "pl_PL.UTF-8",
            "uk_UA.UTF-8",
        ]
        keymaps = ["us", "ru", "de", "fr", "es", "pt", "pl", "ua", "gb"]

        locale_row = Adw.ComboRow(title=tr("field.locale.locale.label"))
        locale_row.set_model(Gtk.StringList.new(locales))
        locale_row.set_selected(_index_of(locales, self.cfg.locale.locale))
        group.add(locale_row)
        self.widgets["locale.locale"] = (locale_row, locales)

        keymap_row = Adw.ComboRow(title=tr("field.locale.keymap.label"))
        keymap_row.set_model(Gtk.StringList.new(keymaps))
        keymap_row.set_selected(_index_of(keymaps, self.cfg.locale.keymap))
        group.add(keymap_row)
        self.widgets["locale.keymap"] = (keymap_row, keymaps)

        tz_row = Adw.EntryRow(title=tr("field.locale.timezone.label"))
        tz_row.set_text(self.cfg.locale.timezone)
        group.add(tz_row)
        self.widgets["locale.timezone"] = tz_row

        def on_next():
            self.cfg.locale.locale = _selected(locale_row, locales, self.cfg.locale.locale)
            self.cfg.locale.keymap = _selected(keymap_row, keymaps, self.cfg.locale.keymap)
            self.cfg.locale.timezone = tz_row.get_text().strip() or "UTC"
            set_language(language_for_locale(self.cfg.locale.locale))
            self.nav.push(self._build_disk())

        return self._toolbar_page(tr("screen.locale.title"), page, on_next)

    # -- disk -----------------------------------------------------------
    def _build_disk(self) -> Adw.NavigationPage:
        page = Adw.PreferencesPage()
        group = self._group(page, tr("screen.disk.title"))

        disks = lsblk_disks()
        self.disk_devices = [d["device"] for d in disks]
        labels = [
            tr(
                "disk.size_model",
                size=human_size(d["size"]),
                model=d["model"] or d["device"],
            )
            for d in disks
        ] or [tr("disk.none")]

        disk_row = Adw.ComboRow(title=tr("field.disk.device.label"))
        disk_row.set_model(Gtk.StringList.new(labels))
        if self.disk_devices:
            disk_row.set_selected(0)
        group.add(disk_row)
        self.widgets["disk.device"] = disk_row

        firmware_row = Adw.ComboRow(title=tr("field.disk.firmware.label"))
        firmware_labels = [
            tr("disk.firmware.auto"),
            tr("disk.firmware.uefi"),
            tr("disk.firmware.bios"),
        ]
        firmware_row.set_model(Gtk.StringList.new(firmware_labels))
        firmware_row.set_selected(_index_of(FIRMWARE_VALUES, self.cfg.disk.firmware.value))
        group.add(firmware_row)
        self.widgets["disk.firmware"] = (firmware_row, FIRMWARE_VALUES)

        fs_row = Adw.ComboRow(title=tr("field.disk.filesystem.label"))
        fs_row.set_model(Gtk.StringList.new(FILESYSTEM_VALUES))
        fs_row.set_selected(_index_of(FILESYSTEM_VALUES, self.cfg.disk.filesystem))
        group.add(fs_row)
        self.widgets["disk.filesystem"] = (fs_row, FILESYSTEM_VALUES)

        esp_row = _spin(tr("field.disk.esp_size_mib.label"), 100, 4096, 64, self.cfg.disk.esp_size_mib)
        group.add(esp_row)
        self.widgets["disk.esp_size_mib"] = esp_row

        boot_row = _spin(
            tr("field.disk.boot_size_mib.label"), 256, 8192, 128, self.cfg.disk.boot_size_mib
        )
        group.add(boot_row)
        self.widgets["disk.boot_size_mib"] = boot_row

        swap_row = _spin(
            tr("field.disk.swap_size_mib.label"), 0, 262144, 512, self.cfg.disk.swap_size_mib
        )
        group.add(swap_row)
        self.widgets["disk.swap_size_mib"] = swap_row

        warning = Gtk.Label(label=tr("disk.warning", device=self.cfg.disk.device or "—"))
        warning.add_css_class("warning")
        warning.set_wrap(True)
        warning.set_margin_top(12)
        warning.set_halign(Gtk.Align.START)
        group.add(warning)

        def on_next():
            if not self.disk_devices:
                self._alert(tr("error.no_disk"))
                return
            index = disk_row.get_selected()
            if index >= len(self.disk_devices):
                self._alert(tr("error.no_disk"))
                return
            self.cfg.disk.device = self.disk_devices[index]
            self.cfg.disk.firmware = Firmware(
                _selected(firmware_row, FIRMWARE_VALUES, self.cfg.disk.firmware.value)
            )
            self.cfg.disk.filesystem = _selected(fs_row, FILESYSTEM_VALUES, self.cfg.disk.filesystem)
            self.cfg.disk.esp_size_mib = int(esp_row.get_value())
            self.cfg.disk.boot_size_mib = int(boot_row.get_value())
            self.cfg.disk.swap_size_mib = int(swap_row.get_value())
            warning.set_text(tr("disk.warning", device=self.cfg.disk.device))
            self.nav.push(self._build_luks())

        return self._toolbar_page(tr("screen.disk.title"), page, on_next)

    # -- luks -----------------------------------------------------------
    def _build_luks(self) -> Adw.NavigationPage:
        page = Adw.PreferencesPage()
        group = self._group(page, tr("screen.luks.title"))

        enable_row = Adw.SwitchRow(title=tr("field.luks.enabled.label"))
        enable_row.set_active(self.cfg.luks.enabled)
        group.add(enable_row)
        self.widgets["luks.enabled"] = enable_row

        pass_row = Adw.PasswordEntryRow(title=tr("field.luks.passphrase.label"))
        pass_row.set_text(self.cfg.luks.passphrase)
        group.add(pass_row)
        self.widgets["luks.passphrase"] = pass_row

        confirm_row = Adw.PasswordEntryRow(title=tr("field.luks.passphrase_confirm.label"))
        group.add(confirm_row)
        self.widgets["luks.passphrase_confirm"] = confirm_row

        info = Gtk.Label(label=tr("luks.body"))
        info.set_wrap(True)
        info.set_margin_top(12)
        info.set_halign(Gtk.Align.START)
        info.add_css_class("dim-label")
        group.add(info)

        def on_next():
            enabled = enable_row.get_active()
            if enabled:
                if not pass_row.get_text():
                    self._alert(tr("error.luks_passphrase"))
                    return
                if pass_row.get_text() != confirm_row.get_text():
                    self._alert(tr("error.password_mismatch"))
                    return
            self.cfg.luks.enabled = enabled
            self.cfg.luks.passphrase = pass_row.get_text() if enabled else ""
            self.nav.push(self._build_user())

        return self._toolbar_page(tr("screen.luks.title"), page, on_next)

    # -- user -----------------------------------------------------------
    def _build_user(self) -> Adw.NavigationPage:
        page = Adw.PreferencesPage()
        group = self._group(page, tr("screen.user.title"))

        username_row = Adw.EntryRow(title=tr("field.user.username.label"))
        username_row.set_text(self.cfg.user.username)
        group.add(username_row)
        self.widgets["user.username"] = username_row

        name_row = Adw.EntryRow(title=tr("field.user.full_name.label"))
        name_row.set_text(self.cfg.user.full_name)
        group.add(name_row)
        self.widgets["user.full_name"] = name_row

        password_row = Adw.PasswordEntryRow(title=tr("field.user.password.label"))
        group.add(password_row)
        self.widgets["user.password"] = password_row

        confirm_row = Adw.PasswordEntryRow(title=tr("field.user.password_confirm.label"))
        group.add(confirm_row)
        self.widgets["user.password_confirm"] = confirm_row

        root_row = Adw.PasswordEntryRow(title=tr("field.user.root_password.label"))
        root_row.set_text(self.cfg.user.root_password)
        group.add(root_row)
        self.widgets["user.root_password"] = root_row

        admin_row = Adw.SwitchRow(title=tr("field.user.is_admin.label"))
        admin_row.set_active(self.cfg.user.is_admin)
        group.add(admin_row)
        self.widgets["user.is_admin"] = admin_row

        autologin_row = Adw.SwitchRow(title=tr("field.user.autologin.label"))
        autologin_row.set_active(self.cfg.user.autologin)
        group.add(autologin_row)
        self.widgets["user.autologin"] = autologin_row

        hostname_row = Adw.EntryRow(title=tr("field.network.hostname.label"))
        hostname_row.set_text(self.cfg.network.hostname)
        group.add(hostname_row)
        self.widgets["network.hostname"] = hostname_row

        def on_next():
            username = username_row.get_text().strip()
            password = password_row.get_text()
            if not username:
                self._alert(tr("error.username"))
                return
            if not password:
                self._alert(tr("error.password"))
                return
            if password != confirm_row.get_text():
                self._alert(tr("error.password_mismatch"))
                return

            self.cfg.user.username = username
            self.cfg.user.full_name = name_row.get_text().strip() or username
            self.cfg.user.password = password
            self.cfg.user.root_password = root_row.get_text()
            self.cfg.user.is_admin = admin_row.get_active()
            self.cfg.user.autologin = autologin_row.get_active()
            self.cfg.network.hostname = hostname_row.get_text().strip() or "deblite"

            errors = self.cfg.validate()
            if errors:
                self._alert("\n".join(errors))
                return
            self.nav.push(self._build_confirm())

        return self._toolbar_page(tr("screen.user.title"), page, on_next)

    # -- confirm --------------------------------------------------------
    def _build_confirm(self) -> Adw.NavigationPage:
        page = Adw.PreferencesPage()
        group = self._group(page, tr("confirm.title"))

        for line in summarize(self.cfg):
            if ": " in line:
                title, subtitle = line.split(": ", 1)
                row = Adw.ActionRow(title=title, subtitle=subtitle)
            else:
                row = Adw.ActionRow(title=line)
            group.add(row)

        warning = Gtk.Label(label=tr("confirm.body"))
        warning.set_wrap(True)
        warning.set_margin_top(12)
        warning.set_halign(Gtk.Align.START)
        warning.add_css_class("dim-label")
        group.add(warning)

        def on_next():
            self._start_install()

        return self._toolbar_page(
            tr("screen.confirm.title"),
            page,
            on_next,
            next_label=tr("confirm.install"),
        )

    # -- progress -------------------------------------------------------
    def _build_progress(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr("screen.progress.title")))
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.08)
        box.append(self.progress_bar)

        self.result_label = Gtk.Label(label=tr("progress.step", index=1, total=1, title=""))
        self.result_label.set_wrap(True)
        self.result_label.set_halign(Gtk.Align.START)
        box.append(self.result_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_buffer = self.log_view.get_buffer()
        scrolled.set_child(self.log_view)
        box.append(scrolled)

        self.close_button = Gtk.Button(label=tr("gui.close"))
        self.close_button.set_halign(Gtk.Align.END)
        self.close_button.set_visible(False)
        self.close_button.connect("clicked", lambda *_: self.get_application().quit())
        box.append(self.close_button)

        toolbar.set_content(box)
        return Adw.NavigationPage(child=toolbar, title=tr("screen.progress.title"))

    def _start_install(self) -> None:
        if self._installing:
            return
        self._installing = True
        self.nav.push(self._build_progress())
        self._pulse_id = GLib.timeout_add(120, self._pulse)

        if self.debug:
            threading.Thread(target=self._run_debug, daemon=True).start()
        else:
            threading.Thread(target=self._run_privileged, daemon=True).start()

    def _pulse(self) -> bool:
        if not self._installing:
            return False
        self.progress_bar.pulse()
        return True

    def _run_privileged(self) -> None:
        command = [
            "sudo",
            "-n",
            "/usr/bin/deblite-installer",
            "--headless",
            "--config",
            "-",
            "--yes",
        ]
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdin is not None
            proc.stdin.write(self.cfg.to_json())
            proc.stdin.close()
            assert proc.stdout is not None
            for line in proc.stdout:
                GLib.idle_add(self._append_log, line.rstrip())
            code = proc.wait()
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(self._append_log, str(exc))
            code = 1
        GLib.idle_add(self._install_done, code)

    def _run_debug(self) -> None:
        ex = Executor(debug=True, log_callback=lambda line: GLib.idle_add(self._append_log, line))
        code = 0
        try:
            run_pipeline(
                self.cfg,
                ex,
                on_step=lambda step, index, total: GLib.idle_add(
                    self._append_log,
                    f"==> {tr('progress.step', index=index, total=total, title=step.title)}",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(self._append_log, f"ERROR: {exc}")
            code = 1
        GLib.idle_add(self._install_done, code)

    def _append_log(self, line: str) -> bool:
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, line + "\n")
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_mark_onscreen(mark)
        return False

    def _install_done(self, code: int) -> bool:
        self._installing = False
        if self._pulse_id:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = 0
        if code == 0:
            self.progress_bar.set_fraction(1.0)
            self.result_label.set_text(tr("progress.done") + "\n" + tr("progress.reboot"))
        else:
            self.progress_bar.set_fraction(0.0)
            self.result_label.set_text(tr("progress.failed"))
        self.close_button.set_visible(True)
        return False


class DebLiteApp(Adw.Application):
    def __init__(self, debug: bool, source: str, flavor: str):
        super().__init__(application_id="org.deblite.Installer")
        self.debug = debug
        self.source = source
        self.flavor = flavor

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = DebLiteWindow(self, self.debug, self.source, self.flavor)
        window.present()


def _index_of(values: list[str], value: str) -> int:
    try:
        return values.index(value)
    except ValueError:
        return 0


def _selected(row: Adw.ComboRow, values: list[str], fallback: str) -> str:
    index = row.get_selected()
    if 0 <= index < len(values):
        return values[index]
    return fallback


def _spin(title: str, minimum: int, maximum: int, step: int, value: int) -> Adw.SpinRow:
    row = Adw.SpinRow.new_with_range(minimum, maximum, step)
    row.set_title(title)
    row.set_value(value)
    return row


def run(debug: bool = False, source: str = "", flavor: str = "") -> int:
    import os

    set_language(language_for_locale(os.environ.get("LANG", "")))
    app = DebLiteApp(debug=debug, source=source or "", flavor=flavor or "")
    return app.run([])
