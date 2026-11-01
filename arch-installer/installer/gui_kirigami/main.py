"""
Kirigami-фронтенд (PySide6 + QML) для установщика.

Требует: PySide6, PySide6-Addons (Kirigami2 QML модуль).
    pip install PySide6

Архитектура: тонкий Python-бэкенд (InstallerBackend) экспортируется в QML
как контекстное свойство. QML (Main.qml) рисует Kirigami-визард поверх
той же InstallConfig/steps.py, что использует CLI — никакой логики
установки в QML нет, только UI.

Запуск:
    python -m installer.gui_kirigami.main [--debug]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from ..core.config import InstallConfig
from ..core.executor import Executor, InstallerError
from ..core.steps import PIPELINE, run_pipeline
from ..frontend_common.summary import summarize
from ..frontend_common.wizard_model import WIZARD_SCREENS, get_by_path, set_by_path
from ..i18n import language_for_locale, set_language, tr

QML_DIR = Path(__file__).parent / "qml"


class InstallerBackend(QObject):
    logLine = Signal(str)
    stepStarted = Signal(str, int, int)   # title, index, total
    finished = Signal(bool, str)          # success, message

    def __init__(self):
        super().__init__()
        self.cfg = InstallConfig()
        self._debug = False

    # --- debug flag, доступен из QML как installerBackend.debug ---
    def _get_debug(self) -> bool:
        return self._debug

    def _set_debug(self, value: bool) -> None:
        self._debug = value

    debug = Property(bool, _get_debug, _set_debug)

    @Slot(str, "QVariant")
    def setField(self, key: str, value) -> None:
        set_by_path(self.cfg, key, value)
        # Локаль — первое поле первого экрана визарда. Как только она
        # известна, переключаем язык самого установщика: каждая следующая
        # страница создаётся заново через pageStack.push(url), поэтому её
        # тексты, читающие tr() при создании, сразу окажутся на новом языке.
        if key == "locale.locale" and value:
            set_language(language_for_locale(str(value)))

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        return tr(key)

    @Slot(str, result="QVariant")
    def getField(self, key: str):
        return get_by_path(self.cfg, key)

    @Slot(result=list)
    def validate(self) -> list[str]:
        return self.cfg.validate()

    @Slot(result=str)
    def getSummary(self) -> str:
        return summarize(self.cfg)

    @Slot()
    def startInstall(self) -> None:
        ex = Executor(debug=self._debug, log_callback=self.logLine.emit)

        def on_step(step, i, total):
            self.stepStarted.emit(step.title, i, total)

        try:
            run_pipeline(self.cfg, ex, on_step=on_step)
        except InstallerError as exc:
            self.finished.emit(False, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — показываем пользователю любую ошибку
            self.finished.emit(False, f"Неожиданная ошибка: {exc}")
            return
        self.finished.emit(True, "Готово" if not self._debug else "Dry-run завершён")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "--dry-run", dest="debug", action="store_true")
    args, qt_args = parser.parse_known_args(argv)

    app = QGuiApplication(sys.argv[:1] + qt_args)
    QCoreApplication.setApplicationName("arch-installer")
    QCoreApplication.setOrganizationName("arch-installer")

    engine = QQmlApplicationEngine()
    backend = InstallerBackend()
    backend._set_debug(args.debug)

    engine.rootContext().setContextProperty("installerBackend", backend)
    engine.rootContext().setContextProperty("debugMode", args.debug)

    engine.load(str(QML_DIR / "Main.qml"))
    if not engine.rootObjects():
        print("Не удалось загрузить QML (проверьте, что PySide6 + Kirigami установлены).",
              file=sys.stderr)
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
