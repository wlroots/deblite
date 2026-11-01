"""English strings — the default/fallback language. Every other language file
only needs to cover the keys it wants to translate; anything missing falls
back to this file automatically (see installer/i18n/translator.py)."""

STRINGS = {
    # --- welcome ---    "welcome.title": "Install Arch Linux",
    "welcome.body": "This wizard will help you partition a disk, install the base "
                     "system, and configure the desktop, bootloader and network.",
    "welcome.body.debug": "Debug mode is on: nothing will actually be written to "
                           "disk — feel free to click through every step.",
    "welcome.body.warning": "Warning: installing will destroy all data on the "
                             "selected disk.",
    "welcome.start": "Start",

    # --- screens ---
    "screen.locale.title": "Language & Region",
    "screen.disk.title": "Disk & Partitioning",
    "screen.luks.title": "Encryption",
    "screen.bootloader.title": "Bootloader",
    "screen.desktop.title": "Desktop Environment",
    "screen.user.title": "User Account",
    "screen.software.title": "Additional Software",
    "screen.confirm.title": "Confirm & Install",

    # --- locale screen ---
    "field.locale.locale.label": "System locale",
    "field.locale.keymap.label": "Console keymap",
    "field.locale.timezone.label": "Timezone",
    "field.network.hostname.label": "Computer name",

    # --- disk screen ---
    "field.disk.device.label": "Disk",
    "field.disk.filesystem.label": "Filesystem",
    "field.disk.esp_size_mib.label": "ESP size (MiB)",
    "field.disk.swap_size_mib.label": "Swap size (MiB, 0 = no swap)",

    # --- luks screen ---
    "field.luks.enabled.label": "Enable full-disk encryption (LUKS)",
    "field.luks.passphrase.label": "Passphrase",

    # --- bootloader screen ---
    "field.bootloader.kind.label": "Bootloader",
    "bootloader.hint": "grub — most common, supports everything.\n"
                        "limine — lightweight and fast, simpler config than grub.\n"
                        "uki-efistub — no separate bootloader: kernel+initramfs are "
                        "combined into a single EFI image booted directly via efibootmgr.",

    # --- desktop screen ---
    "field.desktop.kind.label": "Environment",

    # --- user screen ---
    "field.user.username.label": "Username",
    "field.user.password.label": "Password",
    "field.user.is_admin.label": "Administrator (sudo) privileges",
    "field.user.root_password.label": "Root password",

    # --- software screen ---
    "field.software.enable_ufw.label": "Firewall (UFW)",
    "field.software.enable_zram.label": "zram (compressed memory)",
    "field.software.install_flatpak.label": "Flatpak",
    "field.software.install_pipewire.label": "PipeWire (audio)",
    "field.software.enable_bluetooth.label": "Bluetooth",
    "field.software.install_common_apps.label": "Basic applications (Firefox, htop, git...)",

    # --- confirm screen ---
    "confirm.debug_notice": "Debug mode: a full dry-run will follow with no real "
                             "writes to disk.",
    "confirm.install": "Install",
    "confirm.install_dryrun": "Run steps (dry-run)",
    "confirm.log": "Log",

    # --- navigation ---
    "nav.next": "Next",
    "nav.step": "Step {index} of {total}",
    "nav.review_and_install": "Review & install",

    # --- summary (confirm screen text) ---
    "summary.disk": "Disk: {device} ({fs}{esp}{swap})",
    "summary.swap": ", swap {size} MiB",
    "summary.esp": ", ESP {size} MiB",
    "summary.encryption": "Encryption: {status}",
    "summary.encryption.on": "LUKS enabled",
    "summary.encryption.off": "no encryption",
    "summary.bootloader": "Bootloader: {kind}",
    "summary.desktop": "Desktop: {kind}",
    "summary.locale": "Locale: {locale}, timezone {timezone}, keymap {keymap}",
    "summary.hostname": "Computer name: {hostname}",
    "summary.user": "User: {username}{admin}",
    "summary.user.admin": " (administrator)",
    "summary.software": "Software: {list}",
    "summary.software.none": "nothing extra",

    # --- cli ---
    "cli.title": "=== Arch Linux Installer ===",
    "cli.debug_banner": ">>> DEBUG / DRY-RUN mode: nothing will be written to disk <<<",
    "cli.config_errors": "Configuration errors:",
    "cli.final_config": "--- Final configuration ---",
    "cli.confirm_prompt": "Start installation? This will destroy data on the "
                           "selected disk! [y/N]: ",
    "cli.cancelled": "Cancelled.",
    "cli.step": "[{index}/{total}] {title}...",
    "cli.error": "Installation error: {message}",
    "cli.done": "Done.",
    "cli.done_dryrun": "Dry-run finished without errors.",

    # --- pipeline step titles (shown in logs across CLI/Kirigami/GNOME) ---
    "step.partition": "Partitioning disk",
    "step.luks": "Setting up LUKS encryption",
    "step.format_mount": "Formatting and mounting",
    "step.pacstrap": "Installing base system (pacstrap)",
    "step.fstab": "Generating fstab",
    "step.base_config": "Locale, hostname, users",
    "step.bootloader": "Installing bootloader",
    "step.desktop": "Installing desktop environment",
    "step.software": "Post-install software and services",
    "step.unmount": "Unmounting",
}
