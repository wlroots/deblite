"""
Executor — единственная точка, через которую ядро трогает диск/систему.

В debug/dry-run режиме ни одна деструктивная команда реально не выполняется:
она только логируется. Это даёт возможность "протыкать" весь визард (любой
UI — Kirigami, GNOME, CLI) без риска что-либо сломать на реальном диске.

Правило простое: если код в core/* хочет запустить shell-команду, записать
файл в /mnt, отформатировать раздел и т.д. — он ОБЯЗАН делать это через
Executor, а не напрямую через subprocess/open(). Тогда dry-run гарантированно
покрывает всё.
"""
from __future__ import annotations

import dataclasses
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence


@dataclasses.dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class InstallerError(RuntimeError):
    """Ошибка в процессе установки (реальный сбой команды, не dry-run)."""


class Executor:
    """
    Обёртка над subprocess / файловыми операциями.

    debug=True  -> ничего не выполняется на диске, всё только логируется
                   и возвращает "успешный" фиктивный результат.
    debug=False -> команды реально выполняются.

    Все "опасные" операции (форматирование, запись разделов, chroot-запись
    файлов, systemctl enable и т.п.) должны идти через run()/write_file()/
    mkdir()/chroot_run(), а не напрямую.
    """

    def __init__(self, debug: bool = False, log_callback=None):
        self.debug = debug
        self.log: list[str] = []
        self._log_callback = log_callback or (lambda line: None)

    def _emit(self, line: str) -> None:
        self.log.append(line)
        self._log_callback(line)
        print(line, file=sys.stderr)

    def run(
        self,
        args: Sequence[str],
        *,
        check: bool = True,
        input: str | None = None,
        destructive: bool = True,
    ) -> CommandResult:
        """
        Запускает команду. destructive=True (по умолчанию) означает, что
        команда что-то меняет на диске/в системе — такие команды в
        debug-режиме НЕ выполняются, только логируются.

        destructive=False используется для безобидных read-only команд
        (lsblk, blkid и т.п.), которые можно реально выполнить даже в
        debug-режиме, чтобы UI мог показать пользователю честные данные
        (список дисков и т.д.).
        """
        printable = " ".join(shlex.quote(a) for a in args)

        if self.debug and destructive:
            self._emit(f"[DRY-RUN] $ {printable}")
            return CommandResult(args=list(args), returncode=0, dry_run=True)

        self._emit(f"$ {printable}")
        try:
            proc = subprocess.run(
                list(args),
                input=input,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise InstallerError(f"Команда не найдена: {args[0]}") from exc

        result = CommandResult(
            args=list(args),
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if proc.stdout:
            self._emit(proc.stdout.rstrip())
        if proc.stderr:
            self._emit(proc.stderr.rstrip())

        if check and not result.ok:
            raise InstallerError(
                f"Команда завершилась с ошибкой ({proc.returncode}): {printable}\n{proc.stderr}"
            )
        return result

    def chroot_run(self, root: str, args: Sequence[str], **kw) -> CommandResult:
        """arch-chroot <root> <args...>"""
        return self.run(["arch-chroot", root, *args], **kw)

    def write_file(self, path: str, content: str, *, destructive: bool = True) -> None:
        if self.debug and destructive:
            preview = content if len(content) < 300 else content[:300] + "…"
            self._emit(f"[DRY-RUN] write_file({path}):\n{preview}")
            return
        self._emit(f"write_file({path})")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)

    def mkdir(self, path: str, *, destructive: bool = True) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] mkdir -p {path}")
            return
        self._emit(f"mkdir -p {path}")
        Path(path).mkdir(parents=True, exist_ok=True)
