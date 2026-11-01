"""The installation pipeline shared by the CLI and the GTK frontend."""
from __future__ import annotations

import dataclasses
from collections.abc import Callable

from ..i18n import tr
from . import bootloader, delive, disk, rootfs, system
from .config import InstallConfig
from .executor import Executor, InstallerError


@dataclasses.dataclass
class Step:
    id: str
    title_key: str
    run: Callable[[InstallConfig, Executor, dict], None]

    @property
    def title(self) -> str:
        return tr(self.title_key)


def _partition(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    state["parts"] = disk.partition_disk(cfg, ex)


def _luks(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    state["root_dev"] = disk.setup_luks(cfg, ex, state["parts"]["root"])


def _format_mount(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.format_and_mount(cfg, ex, state["parts"], state["root_dev"])


def _copy_rootfs(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    state["squashfs"] = rootfs.copy_rootfs(cfg, ex)


def _mount_pseudo(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.mount_pseudo(cfg, ex)


def _delive(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    delive.purge_live(cfg, ex)


def _fstab(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.generate_fstab(cfg, ex, state["parts"], state["root_dev"])


def _system(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    system.configure(cfg, ex)


def _bootloader(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    bootloader.install_bootloader(cfg, ex, state["parts"])


def _unmount_pseudo(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.unmount_pseudo(cfg, ex)


def _unmount(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.unmount(cfg, ex)


PIPELINE: list[Step] = [
    Step("partition", "step.partition", _partition),
    Step("luks", "step.luks", _luks),
    Step("format_mount", "step.format_mount", _format_mount),
    Step("copy_rootfs", "step.copy_rootfs", _copy_rootfs),
    Step("mount_pseudo", "step.mount_pseudo", _mount_pseudo),
    Step("delive", "step.delive", _delive),
    Step("fstab", "step.fstab", _fstab),
    Step("system", "step.system", _system),
    Step("bootloader", "step.bootloader", _bootloader),
    Step("unmount_pseudo", "step.unmount_pseudo", _unmount_pseudo),
    Step("unmount", "step.unmount", _unmount),
]


def run_pipeline(
    cfg: InstallConfig,
    ex: Executor,
    on_step: Callable[[Step, int, int], None] | None = None,
) -> dict:
    errors = cfg.validate()
    if errors:
        raise ValueError("invalid configuration: " + "; ".join(errors))

    state: dict = {}
    total = len(PIPELINE)
    started = False
    try:
        for index, step in enumerate(PIPELINE, start=1):
            if on_step:
                on_step(step, index, total)
            started = True
            step.run(cfg, ex, state)
    except Exception:
        if started:
            _best_effort_cleanup(cfg, ex)
        raise
    return state


def _best_effort_cleanup(cfg: InstallConfig, ex: Executor) -> None:
    try:
        disk.unmount_pseudo(cfg, ex)
    except InstallerError:
        pass
    try:
        disk.unmount(cfg, ex)
    except InstallerError:
        pass
