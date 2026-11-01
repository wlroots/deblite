# arch-installer

Установщик Arch Linux (через `pacstrap`) с двумя нативными UI —
**Kirigami** (Qt/KDE) и **libadwaita** (GTK4/GNOME) — плюс текстовый
CLI-визард, который работает вообще без графики.

## Архитектура

```
installer/
  core/                  # вся логика установки, НЕ знает про UI
    executor.py          # запуск команд + dry-run (--debug)
    config.py            # InstallConfig и все под-конфиги (диск, LUKS, DE, софт...)
    disk.py              # sgdisk-разметка, LUKS (cryptsetup)
    pacstrap.py           # pacstrap, fstab, локаль/хостнейм/пользователи
    bootloader.py         # GRUB / Limine / UKI+efistub
    desktop.py             # KDE / GNOME пакеты и display manager
    software.py             # ufw, zram, flatpak, pipewire, bluetooth, базовые приложения
    steps.py                 # единый pipeline из 10 шагов — использует ЛЮБОЙ UI

  frontend_common/
    wizard_model.py       # общее описание экранов/полей визарда (id, тип, choices)
    detect_de.py           # определение текущего DE по XDG_CURRENT_DESKTOP

  cli/wizard.py            # текстовый визард (работает везде, удобен для отладки)
  gui_kirigami/             # PySide6 + QML (Kirigami.ApplicationWindow)
  gui_gnome/                 # GTK4 + libadwaita (Adw.ApplicationWindow)

bin/arch-installer           # точка входа: автоопределяет KDE/GNOME/безголовое окружение
```

Главный принцип: **вся логика установки лежит в `installer/core` и не знает
о существовании Qt или GTK**. Оба GUI и CLI — это просто разные способы
заполнить один и тот же `InstallConfig` и вызвать `steps.run_pipeline()`.
Это значит, что новый UI (например, TUI на textual) добавляется без
дублирования логики установки.

## Debug / dry-run режим

Ключевая фича: флаг `--debug` (синоним `--dry-run`), доступный во всех
трёх UI. В этом режиме `Executor` **не выполняет ни одной деструктивной
команды** (sgdisk, mkfs, cryptsetup, pacstrap, arch-chroot, systemctl
enable и т.д.) — только логирует, что было бы выполнено. Это позволяет:

- пройти весь визард целиком (диск → LUKS → загрузчик → DE → софт),
- увидеть итоговый список команд для любой комбинации опций,
- тестировать UI и логику ветвления без риска для диска, даже не на Arch.

Не-деструктивные read-only команды (в теории — `lsblk`, `blkid` и т.п.,
если их добавить для отображения списка дисков в UI) можно пометить
`destructive=False` в `Executor.run()` — тогда они выполняются по-настоящему
даже в debug-режиме, чтобы UI показывал честные данные.

```bash
# текстовый визард, полностью безопасный прогон
python -m installer.cli.wizard --debug --non-interactive --yes

# автоопределение UI + debug
./bin/arch-installer --debug
```

## Запуск

```bash
# CLI (работает без каких-либо доп. зависимостей)
python -m installer.cli.wizard

# Kirigami (нужен PySide6 + Kirigami QML-модуль, обычно часть KDE)
pip install PySide6
python -m installer.gui_kirigami.main

# GNOME (нужны python-gobject, gtk4, libadwaita)
python -m installer.gui_gnome.main

# автоопределение окружения (для live-ISO)
./bin/arch-installer
```

## Что уже реализовано

- Разметка GPT-диска (ESP + опциональный swap + root) через `sgdisk`
- LUKS2 на root-разделе (`cryptsetup`), автоматический `encrypt` hook в
  `mkinitcpio.conf` и `cryptdevice=` в cmdline загрузчика
- `pacstrap` с базовым набором + пакетами DE + пакетами дополнительного софта
  одним вызовом (меньше точек отказа без сети в chroot)
- Загрузчики: **GRUB**, **Limine**, **UKI + efistub** (без отдельного
  загрузчика — Unified Kernel Image грузится напрямую через `efibootmgr`)
- DE: **KDE Plasma** (+ SDDM) и **GNOME** (+ GDM)
- Пост-установочный софт: `ufw` (с базовыми правилами и автовключением),
  `zram-generator`, `flatpak`, `pipewire`, `bluez`, набор базовых приложений
- Локаль, часовой пояс, раскладка, хостнейм, пользователь с sudo, root-пароль
- Полный dry-run для всех 9 комбинаций (3 загрузчика × 3 DE), проверено

## Что стоит доделать дальше (осознанно оставлено как заглушки)

- `disk.py`: режимы `MANUAL` / `USE_EXISTING` (сейчас только `ERASE_DISK`)
- Btrfs-сабволюмы (@ / @home / @snapshots) — сейчас btrfs форматируется
  плоско, без сабволюмов
- Secure Boot (подпись shim/загрузчика) — поле `secure_boot` в конфиге есть,
  логики пока нет
- `bootloader.py` для UKI использует `dracut` для сборки образа — на чистом
  Arch обычно используется `mkinitcpio` + hook `mkinitcpio-uki` (сейчас как
  более простой/распространённый путь взят dracut; переключить на нативный
  mkinitcpio-путь — отдельная небольшая задача)
- Список дисков в GUI (сейчас поле — обычный текст, стоит добавить
  `lsblk`-вызов с `destructive=False`, чтобы показать реальные диски даже
  в debug-режиме)
- Экран "подтверждение" в `wizard_model.py` (`id="confirm"`) сейчас пустой —
  в GUI стоит показать финальное summary перед `startInstall()`
