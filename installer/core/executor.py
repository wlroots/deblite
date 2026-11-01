"""Single choke point for every destructive operation.

In dry-run mode no command that changes the disk or the target system is
executed; it is only logged. Read-only helpers (``lsblk``, ``blkid``, ...)
must be called with ``destructive=False`` so the UI can still show real data.
"""
from __future__ import annotations

import dataclasses
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path


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
    """A real command failed (never raised for a dry-run)."""


class Executor:
    def __init__(
        self,
        debug: bool = False,
        log_callback: Callable[[str], None] | None = None,
        echo: bool = True,
    ) -> None:
        self.debug = debug
        self.log: list[str] = []
        self._log_callback = log_callback
        self._echo = echo

    def _emit(self, line: str) -> None:
        self.log.append(line)
        if self._log_callback is not None:
            self._log_callback(line)
        if self._echo:
            print(line, file=sys.stderr, flush=True)

    # -- commands -------------------------------------------------------
    def run(
        self,
        args: Sequence[str],
        *,
        check: bool = True,
        input: str | None = None,
        destructive: bool = True,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        args = [str(a) for a in args]
        printable = " ".join(shlex.quote(a) for a in args)

        if self.debug and destructive:
            self._emit(f"[DRY-RUN] $ {printable}")
            return CommandResult(args=args, returncode=0, dry_run=True)

        self._emit(f"$ {printable}")
        try:
            proc = subprocess.run(
                args,
                input=input,
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, **(env or {})},
                cwd=cwd,
            )
        except FileNotFoundError as exc:
            raise InstallerError(f"command not found: {args[0]}") from exc

        result = CommandResult(
            args=args,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
        if proc.stdout:
            self._emit(proc.stdout.rstrip())
        if proc.stderr:
            self._emit(proc.stderr.rstrip())

        if check and not result.ok:
            raise InstallerError(
                f"command failed ({proc.returncode}): {printable}\n{proc.stderr or ''}".rstrip()
            )
        return result

    def chroot_run(self, root: str, args: Sequence[str], **kw) -> CommandResult:
        """Run a command inside the target root (pseudo-filesystems must be mounted)."""
        env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
        env.update(kw.pop("env", None) or {})
        return self.run(["chroot", root, *args], env=env, **kw)

    def run_script(self, root: str, script: str, **kw) -> CommandResult:
        return self.chroot_run(root, ["/bin/sh", "-c", script], **kw)

    # -- files ----------------------------------------------------------
    def write_file(
        self,
        path: str,
        content: str,
        *,
        mode: int | None = None,
        destructive: bool = True,
    ) -> None:
        if self.debug and destructive:
            preview = content if len(content) < 300 else content[:300] + "…"
            self._emit(f"[DRY-RUN] write_file({path}):\n{preview}")
            return
        self._emit(f"write_file({path})")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        if mode is not None:
            p.chmod(mode)

    def mkdir(self, path: str, *, mode: int | None = None, destructive: bool = True) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] mkdir -p {path}")
            return
        Path(path).mkdir(parents=True, exist_ok=True)
        if mode is not None:
            Path(path).chmod(mode)

    def symlink(self, target: str, link: str, *, destructive: bool = True) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] ln -sfn {target} {link}")
            return
        Path(link).parent.mkdir(parents=True, exist_ok=True)
        if Path(link).is_symlink() or Path(link).exists():
            Path(link).unlink()
        Path(link).symlink_to(target)

    def remove(self, path: str, *, recursive: bool = False, destructive: bool = True) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] rm {'-rf' if recursive else '-f'} {path}")
            return
        p = Path(path)
        if not p.exists() and not p.is_symlink():
            return
        if recursive and p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()

    def chmod(self, path: str, mode: int, *, destructive: bool = True) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] chmod {mode:o} {path}")
            return
        Path(path).chmod(mode)

    def chown(
        self, path: str, uid: int, gid: int, *, recursive: bool = False, destructive: bool = True
    ) -> None:
        if self.debug and destructive:
            self._emit(f"[DRY-RUN] chown {uid}:{gid} {path}")
            return
        if recursive:
            for base, dirs, files in os.walk(path):
                os.chown(base, uid, gid)
                for name in dirs + files:
                    os.chown(os.path.join(base, name), uid, gid)
        else:
            os.chown(path, uid, gid)
