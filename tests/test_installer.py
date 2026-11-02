from __future__ import annotations

import json
import subprocess
import sys

import pytest

from installer.core.config import Firmware, InstallConfig, PartitionMode
from installer.core.executor import Executor
from installer.core.steps import run_pipeline
from installer.core.util import part_suffix


def base_config() -> InstallConfig:
    cfg = InstallConfig()
    cfg.disk.device = "/dev/vda"
    cfg.disk.firmware = Firmware.UEFI
    cfg.user.password = "correct horse"
    cfg.luks.enabled = True
    cfg.luks.passphrase = "battery staple"
    return cfg


def test_defaults_are_valid_with_required_fields() -> None:
    cfg = InstallConfig()
    cfg.disk.device = "/dev/vda"
    cfg.user.password = "secret"
    assert cfg.validate() == []


def test_missing_password_is_rejected() -> None:
    cfg = base_config()
    cfg.user.password = ""
    assert any("password" in e for e in cfg.validate())


def test_luks_requires_passphrase() -> None:
    cfg = base_config()
    cfg.luks.passphrase = ""
    assert any("passphrase" in e for e in cfg.validate())


def test_bad_username_and_hostname() -> None:
    cfg = base_config()
    cfg.user.username = "Root User"
    cfg.network.hostname = "-bad-"
    errors = cfg.validate()
    assert any("username" in e for e in errors)
    assert any("hostname" in e for e in errors)


def test_json_roundtrip() -> None:
    cfg = base_config()
    restored = InstallConfig.from_json(cfg.to_json())
    assert restored.to_dict() == cfg.to_dict()
    assert restored.disk.firmware is Firmware.UEFI
    assert restored.disk.mode is PartitionMode.ERASE_DISK


def test_part_suffix() -> None:
    assert part_suffix("/dev/sda", 2) == "/dev/sda2"
    assert part_suffix("/dev/nvme0n1", 1) == "/dev/nvme0n1p1"


@pytest.mark.parametrize(
    ("firmware", "luks", "swap", "expected_root", "has_esp"),
    [
        (Firmware.UEFI, False, 0, "/dev/vda2", True),
        (Firmware.UEFI, True, 0, "/dev/vda3", True),
        (Firmware.UEFI, True, 4096, "/dev/vda4", True),
        (Firmware.BIOS, False, 0, "/dev/vda2", False),
        (Firmware.BIOS, True, 0, "/dev/vda3", False),
    ],
)
def test_partition_layout_dry_run(firmware, luks, swap, expected_root, has_esp) -> None:
    cfg = base_config()
    cfg.disk.firmware = firmware
    cfg.disk.swap_size_mib = swap
    cfg.luks.enabled = luks
    ex = Executor(debug=True, echo=False)
    state = run_pipeline(cfg, ex)
    assert state["parts"]["root"] == expected_root
    assert ("esp" in state["parts"]) is has_esp


def test_full_pipeline_dry_run_emits_expected_commands() -> None:
    cfg = base_config()
    ex = Executor(debug=True, echo=False)
    state = run_pipeline(cfg, ex)
    log = "\n".join(ex.log)

    assert state["root_dev"] == "/dev/mapper/cryptroot"
    for needle in (
        "sgdisk --zap-all /dev/vda",
        "cryptsetup luksFormat",
        "mkfs.ext4",
        "unsquashfs",
        "chpasswd",
        "grub-install --target=x86_64-efi",
        "update-grub",
        "update-initramfs",
    ):
        assert needle in log, needle


def test_luks_writes_crypttab_and_cmdline() -> None:
    cfg = base_config()
    ex = Executor(debug=True, echo=False)
    run_pipeline(cfg, ex)
    log = "\n".join(ex.log)
    assert "/etc/crypttab" in log
    assert "root=/dev/mapper/cryptroot" in log


def test_cli_headless_dry_run() -> None:
    cfg = base_config()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.cli.main",
            "--headless",
            "--config",
            "-",
            "--yes",
            "--debug",
        ],
        input=cfg.to_json(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Installation completed successfully" in proc.stdout


def test_cli_list_disks_is_json() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "installer.cli.main", "--list-disks"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert isinstance(json.loads(proc.stdout), list)


def test_cli_rejects_invalid_config() -> None:
    cfg = base_config()
    cfg.user.password = ""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.cli.main",
            "--headless",
            "--config",
            "-",
            "--yes",
            "--debug",
        ],
        input=cfg.to_json(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "invalid configuration" in proc.stdout.lower()


def test_strip_source_archives(tmp_path) -> None:
    from installer.core import system

    cfg = InstallConfig()
    cfg.mount_root = str(tmp_path)
    (tmp_path / "etc/apt").mkdir(parents=True)
    sources = tmp_path / "etc/apt/sources.list"
    sources.write_text(
        "deb http://deb.debian.org/debian trixie main\n"
        "deb-src http://deb.debian.org/debian trixie main\n"
        "deb http://security.debian.org/ trixie-security main\n"
    )
    system._strip_source_archives(cfg, Executor(echo=False))
    text = sources.read_text()
    assert "deb http://deb.debian.org/debian trixie main" in text
    assert "deb-src" not in text
    assert text.count("deb ") == 2


def test_autologin_is_written_for_the_chosen_user(tmp_path) -> None:
    from installer.core import system

    cfg = InstallConfig()
    cfg.mount_root = str(tmp_path)
    cfg.flavor = "xfce"
    cfg.user.username = "alice"
    cfg.user.autologin = True
    system._autologin(cfg, Executor(echo=False))
    text = (tmp_path / "etc/lightdm/lightdm.conf.d/50-deblite.conf").read_text()
    assert "autologin-user=alice" in text

    cfg.user.autologin = False
    system._autologin(cfg, Executor(echo=False))
    assert not (tmp_path / "etc/lightdm/lightdm.conf.d/50-deblite.conf").exists()


class RecordingExecutor(Executor):
    def __init__(self) -> None:
        super().__init__(debug=True, echo=False)
        self.calls: list[tuple[list[str], str | None]] = []

    def run(self, args, *, input=None, **kw):
        self.calls.append(([str(a) for a in args], input))
        return super().run(args, input=input, **kw)


def test_luks_key_has_no_trailing_newline() -> None:
    from installer.core import disk

    cfg = base_config()
    ex = RecordingExecutor()
    disk.setup_luks(cfg, ex, "/dev/vda3")
    luks_calls = [c for c in ex.calls if c[0][0] == "cryptsetup"]
    assert len(luks_calls) == 2
    assert all(call[1] == "battery staple" for call in luks_calls)


def test_installed_packages_parser(tmp_path) -> None:
    from installer.core.delive import _installed_packages

    status = tmp_path / "status"
    status.write_text(
        "Package: live-boot\nStatus: install ok installed\n\n"
        "Package: vim\nStatus: deinstall ok config-files\n\n"
        "Package: gimp\nStatus: install ok installed\n"
    )
    assert _installed_packages(status) == {"live-boot", "gimp"}


def test_non_admin_user_is_not_added_to_sudo(tmp_path) -> None:
    from installer.core import system

    cfg = InstallConfig()
    cfg.mount_root = str(tmp_path)
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc/group").write_text(
        "root:x:0:\nsudo:x:27:deblite\naudio:x:29:\nvideo:x:44:\n"
    )
    assert system._user_groups(cfg) == ["sudo", "audio", "video"]

    cfg.user.is_admin = False
    assert system._user_groups(cfg) == ["audio", "video"]


def test_detect_flavor_reads_the_baked_file(tmp_path, monkeypatch) -> None:
    from installer.core import config

    flavor_file = tmp_path / "deblite-flavor"
    flavor_file.write_text("kde\n")
    monkeypatch.setattr(config, "FLAVOR_FILE", str(flavor_file))
    assert config.detect_flavor() == "kde"
    assert config.InstallConfig().flavor == "kde"

    flavor_file.unlink()
    assert config.detect_flavor("fallback") == "fallback"
