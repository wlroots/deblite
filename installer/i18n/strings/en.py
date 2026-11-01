"""English strings (default/fallback language)."""

STRINGS = {
    # --- application ---
    "app.name": "DebLite Installer",
    "app.subtitle": "Install DebLite on this computer",
    "app.version": "Version {version}",

    # --- welcome ---
    "welcome.title": "Install DebLite",
    "welcome.body": "This wizard partitions a disk, copies the DebLite system "
                    "onto it, and configures GRUB, users and the network.",
    "welcome.body.debug": "Debug mode is on: nothing will be written to disk. "
                          "Feel free to walk through every step.",
    "welcome.body.warning": "Warning: installing destroys all data on the selected disk.",
    "welcome.start": "Start",

    # --- screens ---
    "screen.locale.title": "Language & Region",
    "screen.disk.title": "Disk & Partitioning",
    "screen.luks.title": "Disk Encryption",
    "screen.user.title": "User Account",
    "screen.confirm.title": "Confirm",
    "screen.progress.title": "Installing",

    # --- locale ---
    "field.locale.locale.label": "Locale",
    "field.locale.keymap.label": "Keyboard layout",
    "field.locale.timezone.label": "Timezone",

    # --- disk ---
    "field.disk.device.label": "Target disk",
    "field.disk.mode.label": "Partitioning",
    "field.disk.esp_size_mib.label": "EFI system partition (MiB)",
    "field.disk.boot_size_mib.label": "Separate /boot partition (MiB)",
    "field.disk.swap_size_mib.label": "Swap partition (MiB, 0 = none)",
    "field.disk.filesystem.label": "Root filesystem",
    "field.disk.firmware.label": "Firmware",
    "disk.warning": "Everything on {device} will be erased.",
    "disk.none": "No disks found",
    "disk.size_model": "{size} — {model}",
    "disk.firmware.auto": "Auto-detect",
    "disk.firmware.uefi": "UEFI",
    "disk.firmware.bios": "BIOS",

    # --- luks ---
    "field.luks.enabled.label": "Encrypt the root partition (LUKS2)",
    "field.luks.passphrase.label": "Encryption passphrase",
    "field.luks.passphrase_confirm.label": "Repeat passphrase",
    "luks.body": "A separate unencrypted /boot partition is created automatically "
                 "so GRUB can load the kernel.",

    # --- user ---
    "field.user.username.label": "Username",
    "field.user.full_name.label": "Full name",
    "field.user.password.label": "Password",
    "field.user.password_confirm.label": "Repeat password",
    "field.user.root_password.label": "Root password (empty = locked)",
    "field.user.is_admin.label": "Allow administrative commands (sudo)",
    "field.user.autologin.label": "Log in automatically",
    "field.network.hostname.label": "Computer name",

    # --- confirm ---
    "confirm.title": "Ready to install",
    "confirm.body": "Review the summary below. This cannot be undone.",
    "confirm.install": "Install",
    "summary.disk": "Disk: {device} ({firmware})",
    "summary.filesystem": "Filesystem: {filesystem}",
    "summary.esp": "EFI partition: {size} MiB",
    "summary.boot": "Separate /boot: {size} MiB",
    "summary.swap": "Swap: {size} MiB",
    "summary.no_swap": "Swap: none",
    "summary.luks": "Encryption: LUKS2",
    "summary.no_luks": "Encryption: none",
    "summary.user": "User: {username} ({full_name})",
    "summary.admin": "Administrator: {value}",
    "summary.yes": "yes",
    "summary.no": "no",
    "summary.hostname": "Hostname: {hostname}",
    "summary.locale": "Locale: {locale} / {keymap} / {timezone}",

    # --- steps ---
    "step.partition": "Partitioning the disk",
    "step.luks": "Setting up encryption",
    "step.format_mount": "Creating filesystems",
    "step.copy_rootfs": "Copying the DebLite system",
    "step.mount_pseudo": "Preparing the chroot",
    "step.delive": "Removing live-session files",
    "step.fstab": "Writing /etc/fstab",
    "step.system": "Configuring users and services",
    "step.bootloader": "Installing GRUB",
    "step.unmount_pseudo": "Cleaning up mounts",
    "step.unmount": "Finishing",

    # --- progress / result ---
    "progress.step": "Step {index} of {total}: {title}",
    "progress.done": "Installation finished",
    "progress.failed": "Installation failed",
    "progress.reboot": "You can now reboot into the installed system.",
    "progress.log": "Details",

    # --- CLI ---
    "cli.choose": "Choose",
    "cli.invalid_choice": "Invalid choice, try again.",
    "cli.confirm_password": "Passwords do not match, try again.",
    "cli.required": "This value is required.",
    "cli.dry_run": "Dry run: no changes will be made.",
    "cli.need_root": "The installer must run as root (use sudo).",
    "cli.invalid_config": "Invalid configuration:\n{errors}",
    "cli.installing": "Installing DebLite…",
    "cli.success": "Installation completed successfully.",
    "cli.failure": "Installation failed: {error}",

    # --- GUI ---
    "gui.back": "Back",
    "gui.next": "Next",
    "gui.cancel": "Cancel",
    "gui.quit": "Quit",
    "gui.install": "Install",
    "gui.close": "Close",
    "gui.error": "Error",
    "gui.root_required": "The installer needs administrator rights.",
    "gui.select_disk": "Select a disk",
    "gui.log": "Log",

    # --- validation ---
    "error.no_disk": "Select a target disk.",
    "error.password": "The password cannot be empty.",
    "error.password_mismatch": "Passwords do not match.",
    "error.luks_passphrase": "Enter an encryption passphrase.",
    "error.username": "Enter a valid username.",
    "error.hostname": "Enter a valid hostname.",
}
