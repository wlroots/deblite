from __future__ import annotations

import dataclasses
from typing import Callable

from . import bootloader, desktop, disk, pacstrap, software
from .config import InstallConfig
from .executor import Executor
from ..i18n import tr


@dataclasses.dataclass
class Step:
    id: str
    title_key: str
    run: Callable[[InstallConfig, Executor, dict], None]

    @property
    def title(self) -> str:
        # Переводится "лениво", в момент обращения — если язык сменили
        # посреди визарда (см. cli/wizard.py, gui_gnome/main.py), заголовки
        # уже идущих шагов будут на актуальном языке.
        return tr(self.title_key)


def _step_partition(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    state["parts"] = disk.partition_disk(cfg, ex)


def _step_luks(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    root_part = state["parts"]["root"]
    state["root_device"] = disk.setup_luks(cfg, ex, root_part)


def _step_format_mount(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    disk.format_and_mount(cfg, ex, state["parts"], state["root_device"])


def _step_pacstrap(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    extra = software.collect_extra_packages(cfg) + desktop.desktop_packages(cfg)
    pacstrap.run_pacstrap(cfg, ex, extra)


def _step_fstab(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    pacstrap.generate_fstab(cfg, ex)


def _step_base_config(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    pacstrap.configure_base_system(cfg, ex)


def _step_bootloader(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    bootloader.install_bootloader(cfg, ex, state["parts"]["esp"], state["parts"]["root"])


def _step_desktop(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    desktop.install_desktop(cfg, ex)


def _step_software(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    software.configure_software(cfg, ex)


def _step_unmount(cfg: InstallConfig, ex: Executor, state: dict) -> None:
    ex.run(["umount", "-R", cfg.mount_root], check=False)
    if cfg.luks.enabled:
        ex.run(["cryptsetup", "close", "cryptroot"], check=False)


PIPELINE: list[Step] = [
    Step("partition", "step.partition", _step_partition),
    Step("luks", "step.luks", _step_luks),
    Step("format_mount", "step.format_mount", _step_format_mount),
    Step("pacstrap", "step.pacstrap", _step_pacstrap),
    Step("fstab", "step.fstab", _step_fstab),
    Step("base_config", "step.base_config", _step_base_config),
    Step("bootloader", "step.bootloader", _step_bootloader),
    Step("desktop", "step.desktop", _step_desktop),
    Step("software", "step.software", _step_software),
    Step("unmount", "step.unmount", _step_unmount),
]


def run_pipeline(cfg: InstallConfig, ex: Executor, on_step=None) -> dict:
    """
    Выполняет все шаги по порядку. on_step(step, index, total) вызывается
    перед каждым шагом — удобно для прогресс-бара в GUI.
    Возвращает общий state-словарь (пути к разделам и т.п.), полезно для отладки.
    """
    errors = cfg.validate()
    if errors:
        raise ValueError("Конфигурация невалидна: " + "; ".join(errors))

    state: dict = {}
    total = len(PIPELINE)
    for i, step in enumerate(PIPELINE, start=1):
        if on_step:
            on_step(step, i, total)
        step.run(cfg, ex, state)
    return state
