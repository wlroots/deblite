from __future__ import annotations

from .config import InstallConfig, PartitionMode
from .executor import Executor

LUKS_MAPPER_NAME = "cryptroot"


def _part_suffix(device: str, index: int) -> str:
    """nvme0n1 -> nvme0n1p1, sda -> sda1"""
    if device[-1].isdigit():
        return f"{device}p{index}"
    return f"{device}{index}"


def partition_disk(cfg: InstallConfig, ex: Executor) -> dict[str, str]:
    """
    Размечает диск (если mode == ERASE_DISK) и возвращает словарь путей:
    {"esp": ..., "root": ...}
    В USE_EXISTING/MANUAL предполагается, что разделы уже размечены
    вручную на предыдущем шаге UI и переданы через cfg (расширение на будущее).
    """
    dev = cfg.disk.device

    if cfg.disk.mode == PartitionMode.ERASE_DISK:
        ex.run(["sgdisk", "--zap-all", dev])
        ex.run([
            "sgdisk",
            "-n", f"1:0:+{cfg.disk.esp_size_mib}MiB", "-t", "1:ef00", "-c", "1:ESP",
            dev,
        ])
        root_part_index = 2
        if cfg.disk.swap_size_mib:
            ex.run([
                "sgdisk",
                "-n", f"2:0:+{cfg.disk.swap_size_mib}MiB", "-t", "2:8200", "-c", "2:swap",
                dev,
            ])
            root_part_index = 3
        ex.run([
            "sgdisk",
            "-n", f"{root_part_index}:0:0", "-t", f"{root_part_index}:8300", "-c", f"{root_part_index}:root",
            dev,
        ])
        ex.run(["partprobe", dev], check=False)

        esp = _part_suffix(dev, 1)
        root = _part_suffix(dev, root_part_index)
        result = {"esp": esp, "root": root}
        if cfg.disk.swap_size_mib:
            result["swap"] = _part_suffix(dev, 2)
        return result

    raise NotImplementedError(f"Режим разметки {cfg.disk.mode} пока не реализован в этом каркасе")


def setup_luks(cfg: InstallConfig, ex: Executor, root_partition: str) -> str:
    """
    Если LUKS включён — шифрует root-раздел и открывает его в /dev/mapper/cryptroot.
    Возвращает путь, который дальше нужно форматировать/монтировать как root
    (либо сам root_partition, либо /dev/mapper/cryptroot).
    """
    if not cfg.luks.enabled:
        return root_partition

    ex.run([
        "cryptsetup", "luksFormat",
        "--type", "luks2",
        "--cipher", cfg.luks.cipher,
        "--key-size", str(cfg.luks.key_size),
        "--batch-mode",
        root_partition,
    ], input=cfg.luks.passphrase)

    ex.run(
        ["cryptsetup", "open", root_partition, LUKS_MAPPER_NAME],
        input=cfg.luks.passphrase,
    )
    return f"/dev/mapper/{LUKS_MAPPER_NAME}"


def format_and_mount(cfg: InstallConfig, ex: Executor, parts: dict[str, str], root_device: str) -> None:
    fs = cfg.disk.filesystem
    mkfs_cmd = {
        "ext4": ["mkfs.ext4", "-F"],
        "btrfs": ["mkfs.btrfs", "-f"],
        "xfs": ["mkfs.xfs", "-f"],
    }[fs]

    ex.run(["mkfs.fat", "-F32", "-n", "ESP", parts["esp"]])
    ex.run([*mkfs_cmd, root_device])
    if "swap" in parts:
        ex.run(["mkswap", parts["swap"]])

    ex.mkdir(cfg.mount_root)
    ex.run(["mount", root_device, cfg.mount_root])
    ex.mkdir(f"{cfg.mount_root}/boot")
    ex.run(["mount", parts["esp"], f"{cfg.mount_root}/boot"])
    if "swap" in parts:
        ex.run(["swapon", parts["swap"]])
