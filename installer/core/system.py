"""Configure the copied rootfs: identity, locale, users, services, apt policy."""
from __future__ import annotations

from pathlib import Path

from .config import InstallConfig
from .executor import Executor, InstallerError

DISPLAY_MANAGERS = {
    "kde": "sddm.service",
    "gnome": "gdm3.service",
    "gnome-backports": "gdm3.service",
    "xfce": "lightdm.service",
    "cinnamon": "lightdm.service",
}

BASE_GROUPS = ("sudo", "audio", "video", "plugdev", "netdev", "bluetooth", "lpadmin")


def configure(cfg: InstallConfig, ex: Executor) -> None:
    _hostname(cfg, ex)
    _locale(cfg, ex)
    _keyboard(cfg, ex)
    _timezone(cfg, ex)
    _users(cfg, ex)
    _autologin(cfg, ex)
    _apt_policy(cfg, ex)
    _services(cfg, ex)
    _misc(cfg, ex)


def _host_path(cfg: InstallConfig, rel: str) -> str:
    return str(Path(cfg.mount_root, rel.lstrip("/")))


def _hostname(cfg: InstallConfig, ex: Executor) -> None:
    hostname = cfg.network.hostname
    ex.write_file(_host_path(cfg, "/etc/hostname"), hostname + "\n")
    ex.write_file(
        _host_path(cfg, "/etc/hosts"),
        "127.0.0.1\tlocalhost\n"
        f"127.0.1.1\t{hostname}\n"
        "::1\t\tlocalhost ip6-localhost ip6-loopback\n"
        "ff02::1\t\tip6-allnodes\n"
        "ff02::2\t\tip6-allrouters\n",
    )


def _locale(cfg: InstallConfig, ex: Executor) -> None:
    locale = cfg.locale.locale
    ex.write_file(_host_path(cfg, "/etc/locale.gen"), f"{locale} UTF-8\n")
    ex.write_file(_host_path(cfg, "/etc/default/locale"), f"LANG={locale}\n")
    ex.chroot_run(cfg.mount_root, ["locale-gen"], env={"DEBIAN_FRONTEND": "noninteractive"})


def _keyboard(cfg: InstallConfig, ex: Executor) -> None:
    ex.write_file(
        _host_path(cfg, "/etc/default/keyboard"),
        'XKBMODEL="pc105"\n'
        f'XKBLAYOUT="{cfg.locale.keymap}"\n'
        'XKBVARIANT=""\n'
        'XKBOPTIONS=""\n'
        'BACKSPACE="guess"\n',
    )


def _timezone(cfg: InstallConfig, ex: Executor) -> None:
    tz = cfg.locale.timezone
    zone = Path(cfg.mount_root, "usr/share/zoneinfo", tz)
    if not zone.exists() and not ex.debug:
        raise InstallerError(f"unknown timezone: {tz}")
    ex.symlink(f"/usr/share/zoneinfo/{tz}", _host_path(cfg, "/etc/localtime"))
    ex.write_file(_host_path(cfg, "/etc/timezone"), tz + "\n")


def _existing_groups(cfg: InstallConfig) -> set[str]:
    group_file = Path(cfg.mount_root, "etc/group")
    if not group_file.exists():
        return set()
    groups = set()
    for line in group_file.read_text().splitlines():
        if line and not line.startswith("#"):
            groups.add(line.split(":", 1)[0])
    return groups


def _user_exists(cfg: InstallConfig, ex: Executor, username: str) -> bool:
    result = ex.chroot_run(cfg.mount_root, ["id", "-u", username], check=False)
    return result.ok


def _user_groups(cfg: InstallConfig) -> list[str]:
    allowed = BASE_GROUPS if cfg.user.is_admin else tuple(g for g in BASE_GROUPS if g != "sudo")
    return [g for g in allowed if g in _existing_groups(cfg)]


def _users(cfg: InstallConfig, ex: Executor) -> None:
    root = cfg.mount_root
    username = cfg.user.username
    groups = _user_groups(cfg)
    group_arg = ",".join(groups) if groups else ""

    if _user_exists(cfg, ex, username):
        ex.chroot_run(root, ["usermod", "-s", "/bin/bash", "-c", cfg.user.full_name, username])
        if group_arg:
            ex.chroot_run(root, ["usermod", "-aG", group_arg, username])
    else:
        args = ["useradd", "-m", "-s", "/bin/bash", "-c", cfg.user.full_name]
        if group_arg:
            args += ["-G", group_arg]
        args.append(username)
        ex.chroot_run(root, args)

    if not cfg.user.is_admin:
        ex.chroot_run(root, ["gpasswd", "-d", username, "sudo"], check=False)

    ex.chroot_run(
        root,
        ["chpasswd"],
        input=f"{username}:{cfg.user.password}\n",
    )

    if cfg.user.root_password:
        ex.chroot_run(root, ["chpasswd"], input=f"root:{cfg.user.root_password}\n")
    else:
        ex.chroot_run(root, ["passwd", "-l", "root"], check=False)

    home = Path(root, "home", username)
    if home.exists():
        ex.chown(str(home), _uid(cfg, username), _gid(cfg, username), recursive=True)


def _uid(cfg: InstallConfig, username: str) -> int:
    return _passwd_id(cfg, username, 2)


def _gid(cfg: InstallConfig, username: str) -> int:
    return _passwd_id(cfg, username, 3)


def _passwd_id(cfg: InstallConfig, username: str, index: int) -> int:
    passwd = Path(cfg.mount_root, "etc/passwd")
    if passwd.exists():
        for line in passwd.read_text().splitlines():
            fields = line.split(":")
            if len(fields) > 3 and fields[0] == username:
                return int(fields[index])
    return 1000


def _autologin(cfg: InstallConfig, ex: Executor) -> None:
    paths = (
        "/etc/sddm.conf.d/50-deblite.conf",
        "/etc/gdm3/daemon.conf.d/50-deblite.conf",
        "/etc/lightdm/lightdm.conf.d/50-deblite.conf",
    )
    if not cfg.user.autologin:
        for path in paths:
            ex.remove(_host_path(cfg, path))
        return

    user = cfg.user.username
    if cfg.flavor == "kde":
        ex.write_file(
            _host_path(cfg, paths[0]),
            f"[Autologin]\nUser={user}\nSession=plasmax11\nRelogin=false\n",
        )
    elif cfg.flavor in ("gnome", "gnome-backports"):
        ex.write_file(
            _host_path(cfg, paths[1]),
            "[daemon]\n"
            "AutomaticLoginEnable=true\n"
            f"AutomaticLogin={user}\n"
            "TimedLoginEnable=true\n"
            f"TimedLogin={user}\n"
            "TimedLoginDelay=0\n",
        )
    else:
        ex.write_file(
            _host_path(cfg, paths[2]),
            "[Seat:*]\n"
            f"autologin-user={user}\n"
            "autologin-user-timeout=0\n",
        )


def _apt_policy(cfg: InstallConfig, ex: Executor) -> None:
    ex.write_file(
        _host_path(cfg, "/etc/apt/apt.conf.d/99deblite"),
        'APT::Install-Recommends "false";\n'
        'APT::Install-Suggests "false";\n'
        'APT::AutoRemove::RecommendsImportant "false";\n'
        'APT::AutoRemove::SuggestsImportant "false";\n',
    )
    _strip_source_archives(cfg, ex)


def _strip_source_archives(cfg: InstallConfig, ex: Executor) -> None:
    """Drop deb-src entries: the installed desktop does not need source indices."""
    path = Path(_host_path(cfg, "/etc/apt/sources.list"))
    if not path.exists():
        return
    kept = [
        line for line in path.read_text().splitlines()
        if not line.lstrip().startswith("deb-src")
    ]
    ex.write_file(str(path), "\n".join(kept) + "\n")


def _unit_exists(cfg: InstallConfig, unit: str) -> bool:
    for base in ("lib/systemd/system", "usr/lib/systemd/system", "etc/systemd/system"):
        if Path(cfg.mount_root, base, unit).exists():
            return True
    return False


def _enable(cfg: InstallConfig, ex: Executor, unit: str) -> None:
    if _unit_exists(cfg, unit):
        ex.chroot_run(cfg.mount_root, ["systemctl", "enable", unit], check=False)


def _services(cfg: InstallConfig, ex: Executor) -> None:
    for unit in (
        "NetworkManager.service",
        "firewalld.service",
        "bluetooth.service",
        "fstrim.timer",
        "systemd-timesyncd.service",
        "zramswap.service",
    ):
        _enable(cfg, ex, unit)

    dm = DISPLAY_MANAGERS.get(cfg.flavor)
    if dm:
        _enable(cfg, ex, dm)
    else:
        for candidate in ("gdm3.service", "sddm.service", "lightdm.service"):
            if _unit_exists(cfg, candidate):
                _enable(cfg, ex, candidate)
                break

    ex.chroot_run(cfg.mount_root, ["systemctl", "set-default", "graphical.target"], check=False)


def _misc(cfg: InstallConfig, ex: Executor) -> None:
    ex.write_file(
        _host_path(cfg, "/etc/default/zramswap"),
        "ALGO=zstd\nPERCENT=50\nPRIORITY=100\n",
    )
    ex.write_file(
        _host_path(cfg, "/etc/sysctl.d/99-deblite.conf"),
        "vm.swappiness=10\n",
    )

    sudoers = _host_path(cfg, "/etc/sudoers")
    if Path(sudoers).exists() and "%sudo" not in Path(sudoers).read_text():
        ex.write_file(
            _host_path(cfg, "/etc/sudoers.d/00-deblite"),
            "%sudo ALL=(ALL:ALL) ALL\n",
            mode=0o440,
        )
