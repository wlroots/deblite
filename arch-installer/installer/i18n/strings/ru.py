"""Русский перевод. Отсутствующие ключи автоматически берутся из en.py —
переводить нужно только то, что реально хочется перевести."""

STRINGS = {
    # --- приветствие ---
    "welcome.title": "Установка Arch Linux",
    "welcome.body": "Этот мастер поможет разметить диск, установить базовую "
                     "систему и настроить рабочий стол, загрузчик и сеть.",
    "welcome.body.debug": "Включён режим отладки: ни одна операция не будет "
                           "выполнена на реальном диске — можно спокойно пройти все шаги.",
    "welcome.body.warning": "Внимание: установка уничтожит данные на выбранном диске.",
    "welcome.start": "Начать",

    # --- экраны ---
    "screen.locale.title": "Язык и регион",
    "screen.disk.title": "Диск и разметка",
    "screen.luks.title": "Шифрование",
    "screen.bootloader.title": "Загрузчик",
    "screen.desktop.title": "Рабочий стол",
    "screen.user.title": "Пользователь",
    "screen.software.title": "Дополнительный софт",
    "screen.confirm.title": "Подтверждение",

    # --- экран локали ---
    "field.locale.locale.label": "Локаль системы",
    "field.locale.keymap.label": "Раскладка консоли",
    "field.locale.timezone.label": "Часовой пояс",
    "field.network.hostname.label": "Имя компьютера",

    # --- диск ---
    "field.disk.device.label": "Диск",
    "field.disk.filesystem.label": "Файловая система",
    "field.disk.esp_size_mib.label": "ESP, МиБ",
    "field.disk.swap_size_mib.label": "Swap, МиБ (0 = без свопа)",

    # --- luks ---
    "field.luks.enabled.label": "Включить полнодисковое шифрование (LUKS)",
    "field.luks.passphrase.label": "Парольная фраза",

    # --- загрузчик ---
    "field.bootloader.kind.label": "Загрузчик",
    "bootloader.hint": "grub — самый распространённый, поддерживает всё.\n"
                        "limine — лёгкий и быстрый, конфиг проще grub.\n"
                        "uki-efistub — без отдельного загрузчика: ядро+initramfs "
                        "собираются в единый EFI-образ и грузятся напрямую через efibootmgr.",

    # --- рабочий стол ---
    "field.desktop.kind.label": "Окружение",

    # --- пользователь ---
    "field.user.username.label": "Имя пользователя",
    "field.user.password.label": "Пароль",
    "field.user.is_admin.label": "Права администратора (sudo)",
    "field.user.root_password.label": "Пароль root",

    # --- софт ---
    "field.software.enable_ufw.label": "Файрвол (UFW)",
    "field.software.enable_zram.label": "zram (сжатая память)",
    "field.software.install_flatpak.label": "Flatpak",
    "field.software.install_pipewire.label": "PipeWire (аудио)",
    "field.software.enable_bluetooth.label": "Bluetooth",
    "field.software.install_common_apps.label": "Базовые приложения (Firefox, htop, git...)",

    # --- подтверждение ---
    "confirm.debug_notice": "Режим отладки: ниже будет выполнен полный прогон "
                             "без единой реальной записи на диск.",
    "confirm.install": "Установить",
    "confirm.install_dryrun": "Пройти шаги (dry-run)",
    "confirm.log": "Журнал",

    # --- навигация ---
    "nav.next": "Далее",
    "nav.step": "Шаг {index} из {total}",
    "nav.review_and_install": "Просмотреть и установить",

    # --- сводка ---
    "summary.disk": "Диск: {device} ({fs}{esp}{swap})",
    "summary.swap": ", swap {size} МиБ",
    "summary.esp": ", ESP {size} МиБ",
    "summary.encryption": "Шифрование: {status}",
    "summary.encryption.on": "LUKS включён",
    "summary.encryption.off": "без шифрования",
    "summary.bootloader": "Загрузчик: {kind}",
    "summary.desktop": "Рабочий стол: {kind}",
    "summary.locale": "Локаль: {locale}, часовой пояс {timezone}, раскладка {keymap}",
    "summary.hostname": "Имя компьютера: {hostname}",
    "summary.user": "Пользователь: {username}{admin}",
    "summary.user.admin": " (администратор)",
    "summary.software": "Софт: {list}",
    "summary.software.none": "ничего дополнительного",

    # --- cli ---
    "cli.title": "=== Установщик Arch Linux ===",
    "cli.debug_banner": ">>> DEBUG / DRY-RUN режим: на диск ничего не будет записано <<<",
    "cli.config_errors": "Ошибки конфигурации:",
    "cli.final_config": "--- Итоговая конфигурация ---",
    "cli.confirm_prompt": "Начать установку? Это уничтожит данные на выбранном диске! [y/N]: ",
    "cli.cancelled": "Отменено.",
    "cli.step": "[{index}/{total}] {title}...",
    "cli.error": "Ошибка установки: {message}",
    "cli.done": "Готово.",
    "cli.done_dryrun": "Dry-run завершён без ошибок.",

    # --- названия шагов пайплайна (лог CLI/Kirigami/GNOME) ---
    "step.partition": "Разметка диска",
    "step.luks": "Настройка шифрования LUKS",
    "step.format_mount": "Форматирование и монтирование",
    "step.pacstrap": "Установка базовой системы (pacstrap)",
    "step.fstab": "Генерация fstab",
    "step.base_config": "Локаль, хостнейм, пользователи",
    "step.bootloader": "Установка загрузчика",
    "step.desktop": "Установка окружения рабочего стола",
    "step.software": "Пост-установочный софт и службы",
    "step.unmount": "Размонтирование",
}
