"""Remove live-session packages, users and state from the copied rootfs."""
from __future__ import annotations

import os
from pathlib import Path

from .config import InstallConfig
from .executor import Executor, InstallerError

LIVE_PACKAGES = (
    "live-boot",
    "live-boot-initramfs-tools",
    "live-config",
    "live-config-systemd",
    "live-tools",
    "user-setup",
    "deblite-installer",
)

LIVE_PATHS = (
    "/etc/live",
    "/lib/live",
    "/usr/lib/live",
    "/var/lib/live",
    "/var/log/live",
    "/etc/xdg/autostart/deblite-installer.desktop",
    "/etc/sudoers.d/deblite-live",
    "/etc/sudoers.d/deblite-installer",
    "/etc/sddm.conf.d/autologin.conf",
    "/etc/sddm.conf.d/50-deblite-autologin.conf",
    "/etc/lightdm/lightdm.conf.d/50-deblite-autologin.conf",
    "/etc/gdm3/daemon.conf.d/50-deblite-autologin.conf",
    "/var/lib/dbus/machine-id",
)

# GDM has no drop-in directory; its autologin keys live in daemon.conf.
GDM_CONF = "/etc/gdm3/daemon.conf"
GDM_AUTOLOGIN_KEYS = frozenset(
    {
        "AutomaticLoginEnable",
        "AutomaticLogin",
        "TimedLoginEnable",
        "TimedLogin",
        "TimedLoginDelay",
    }
)


def purge_live(cfg: InstallConfig, ex: Executor) -> None:
    if cfg.skip_delive:
        ex._emit("[delive] skipped by configuration")
        return

    root = cfg.mount_root
    env = {"DEBIAN_FRONTEND": "noninteractive"}

    ex.chroot_run(
        root,
        ["apt-get", "purge", "-y", "--no-install-recommends", *LIVE_PACKAGES],
        check=False,
        env=env,
    )
    # apt can refuse to purge in a chroot with stale metadata. dpkg is the
    # authoritative fallback; leaving live-boot behind makes the target unbootable.
    ex.chroot_run(root, ["dpkg", "--purge", "--force-all", *LIVE_PACKAGES], check=False, env=env)
    ex.chroot_run(root, ["apt-get", "clean"], check=False, env=env)

    if not ex.debug:
        status = Path(root, "var/lib/dpkg/status")
        if status.exists():
            installed = _installed_packages(status)
            leftovers = sorted(set(LIVE_PACKAGES) & installed)
            if leftovers:
                raise InstallerError(
                    "live packages could not be removed: " + ", ".join(leftovers)
                )

    for rel in LIVE_PATHS:
        _remove(cfg, ex, rel)

    # Live boot config may be spread over a few drop-in directories.
    _remove_glob(cfg, ex, "/etc/systemd/system/*live*")
    _remove_glob(cfg, ex, "/lib/systemd/system/live-*")
    _reset_gdm_autologin(cfg, ex)

    # Reset identity: a cloned machine must generate fresh IDs and host keys.
    _write(cfg, ex, "/etc/machine-id", "")
    _remove_glob(cfg, ex, "/etc/ssh/ssh_host_*")
    _write(cfg, ex, "/etc/hostname", "")

    # Drop build-time apt metadata and logs; they are useless and bulky.
    _remove_glob(cfg, ex, "/var/lib/apt/lists/*")
    _remove_glob(cfg, ex, "/var/cache/apt/archives/*.deb")
    ex.chroot_run(
        root,
        ["/bin/sh", "-c", "find /var/log -type f -exec truncate -s 0 {} + 2>/dev/null || true"],
        check=False,
    )

    # Debian live creates a throw-away account called "user". Keep it only if
    # the operator chose the same name for the real account.
    if not cfg.keep_live_user and cfg.user.username != "user":
        ex.chroot_run(root, ["deluser", "--remove-home", "user"], check=False, env=env)
        _remove(cfg, ex, "/home/user")


def _host_path(cfg: InstallConfig, rel: str) -> str:
    return os.path.join(cfg.mount_root, rel.lstrip("/"))


def _installed_packages(status: Path) -> set[str]:
    packages: set[str] = set()
    current: str | None = None
    for line in status.read_text(errors="replace").splitlines():
        if line.startswith("Package:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("Status:") and current:
            fields = line.split()
            if fields and fields[-1] == "installed":
                packages.add(current)
    return packages


def _remove(cfg: InstallConfig, ex: Executor, rel: str) -> None:
    ex.remove(_host_path(cfg, rel), recursive=True)


def _remove_glob(cfg: InstallConfig, ex: Executor, pattern: str) -> None:
    base = Path(_host_path(cfg, pattern))
    for match in base.parent.glob(base.name):
        ex.remove(str(match), recursive=True)


def _reset_gdm_autologin(cfg: InstallConfig, ex: Executor) -> None:
    """Drop the live autologin keys from GDM's single configuration file."""
    path = Path(_host_path(cfg, GDM_CONF))
    if not path.exists():
        return
    kept = [
        line
        for line in path.read_text().splitlines()
        if line.split("=", 1)[0].strip() not in GDM_AUTOLOGIN_KEYS
    ]
    _write(cfg, ex, GDM_CONF, "\n".join(kept) + "\n")


def _write(cfg: InstallConfig, ex: Executor, rel: str, content: str) -> None:
    ex.write_file(_host_path(cfg, rel), content)
