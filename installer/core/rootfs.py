"""Copy the live system's squashfs onto the target root."""
from __future__ import annotations

from pathlib import Path

from .config import InstallConfig
from .executor import Executor, InstallerError
from .util import resolve_squashfs, which

# Used only by the rsync fallback. unsquashfs is the primary path.
EXCLUDES = (
    "--exclude=/proc/*",
    "--exclude=/sys/*",
    "--exclude=/dev/*",
    "--exclude=/run/*",
    "--exclude=/tmp/*",
    "--exclude=/var/tmp/*",
    "--exclude=/var/cache/apt/archives/*.deb",
    "--exclude=/var/lib/apt/lists/*",
    "--exclude=/etc/machine-id",
    "--exclude=/var/lib/dbus/machine-id",
    "--exclude=/etc/ssh/ssh_host_*",
)


def copy_rootfs(cfg: InstallConfig, ex: Executor) -> str:
    source = resolve_squashfs(cfg.source)
    if source is None:
        if ex.debug:
            ex.run(["unsquashfs", "-f", "-d", cfg.mount_root, "<squashfs>"])
            return ""
        raise InstallerError(
            "cannot find the live filesystem.squashfs; pass --source or run from the DebLite ISO"
        )

    ex.mkdir(cfg.mount_root)

    if which("unsquashfs"):
        ex.run(["unsquashfs", "-f", "-d", cfg.mount_root, "-no-progress", source])
    else:
        if not which("rsync"):
            raise InstallerError("neither unsquashfs nor rsync is available in the live system")
        mountpoint = "/run/deblite-squashfs"
        ex.mkdir(mountpoint)
        ex.run(["mount", "-o", "loop,ro", source, mountpoint])
        try:
            ex.run(
                [
                    "rsync",
                    "-aHAX",
                    "--one-file-system",
                    "--numeric-ids",
                    *EXCLUDES,
                    f"{mountpoint}/",
                    f"{cfg.mount_root}/",
                ]
            )
        finally:
            ex.run(["umount", mountpoint], check=False)

    verify_rootfs(cfg, ex)
    return source


def verify_rootfs(cfg: InstallConfig, ex: Executor) -> None:
    if ex.debug:
        return
    required = ("etc/os-release", "etc/passwd", "usr/bin/apt", "usr/bin/dpkg")
    missing = [rel for rel in required if not Path(cfg.mount_root, rel).exists()]
    if missing:
        raise InstallerError("copied rootfs is incomplete; missing: " + ", ".join(missing))
