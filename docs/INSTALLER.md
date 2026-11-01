# The DebLite installer

The installer is a port of the Arch installer in `arch-installer/`, but it
does not use `debootstrap` or `pacstrap`. It copies the live ISO's
`filesystem.squashfs` onto the target, then removes the live-session bits and
reconfigures the system for first boot.

All destructive work goes through `installer/core/executor.py`. With
`--debug` no command that changes a disk or the target system is executed; the
whole pipeline can be walked safely on a normal workstation.

## Pipeline

| Step | What it does |
|---|---|
| `partition` | GPT layout with `sgdisk` (ESP / BIOS boot / optional /boot / optional swap / root) |
| `luks` | Optional LUKS2 root; opens it as `/dev/mapper/cryptroot` |
| `format_mount` | `mkfs.fat`, `mkfs.ext4|btrfs|xfs`, `mkswap`, mounts under `/mnt` |
| `copy_rootfs` | `unsquashfs` the live squashfs into the target (rsync fallback) |
| `mount_pseudo` | Bind-mounts `/dev`, `/dev/pts`, `/proc`, `/sys`, `/run`, efivars |
| `delive` | Purges live packages, removes live user/autologin, resets machine-id and SSH host keys |
| `fstab` | Writes `/etc/fstab`, `/etc/crypttab`, `cryptsetup-initramfs` config |
| `system` | Hostname, locale, keymap, timezone, users, sudo, services, autologin, lean apt policy |
| `bootloader` | Writes GRUB defaults, runs `grub-install`, `update-grub`, `update-initramfs` |
| `unmount_pseudo` | Unmounts the bind mounts |
| `unmount` | Unmounts the target and closes LUKS |

If a step raises, the pipeline makes a best-effort attempt to unmount and
close LUKS before re-raising.

## Partition layout

UEFI:

```
1  ESP            512 MiB (configurable)   ef00   /boot/efi
2  /boot          1024 MiB, only with LUKS 8300   /boot
3  swap           optional                8200
N  /               rest                  8300   /
```

BIOS:

```
1  BIOS boot      1 MiB                   ef02
2  /boot          only with LUKS          8300
3  swap           optional                8200
N  /              rest                    8300
```

`/boot` is a separate unencrypted ext4 partition **only when LUKS is enabled**,
so GRUB can load the kernel and initramfs without unlocking the root. Without
LUKS, `/boot` lives on the root filesystem.

The ESP is always mounted at `/boot/efi`. GRUB is installed for
`x86_64-efi` (with a removable `EFI/BOOT/BOOTX64.EFI` fallback) or
`i386-pc`, depending on the firmware.

## Root filesystem

`ext4` (default), `btrfs` and `xfs` are supported. Btrfs is created as a
single filesystem; subvolumes are not used yet.

## LUKS

- LUKS2, `aes-xts-plain64`, 512-bit key, Argon2id.
- `/etc/crypttab` maps `cryptroot` to the container UUID.
- `GRUB_CMDLINE_LINUX="root=/dev/mapper/cryptroot"`.
- `cryptsetup-initramfs` is installed and `CRYPTSETUP=y` is written, so the
  initramfs prompts for the passphrase.
- `discard` is enabled in crypttab; adjust it if you do not want TRIM to leak
  usage patterns.

## De-live cleanup

The copied rootfs contains the live stack. The installer:

- purges `live-boot`, `live-boot-initramfs-tools`, `live-config`,
  `live-config-systemd`, `live-tools`, `user-setup` and `deblite-installer`;
- removes `/etc/live`, `/lib/live`, `/usr/lib/live`, `/var/lib/live`;
- removes live autologin drop-ins for SDDM, GDM and LightDM;
- removes the live `user` account when the chosen username differs;
- truncates `/etc/machine-id`, removes `/var/lib/dbus/machine-id` and
  `/etc/ssh/ssh_host_*`;
- clears apt lists/cache and logs.

`skip_delive: true` exists only for rescue/debug work. Do not use it for a
normal install.

## Users and services

- The user is created with `useradd -m`, added to `sudo` (plus `audio`,
  `video`, `plugdev`, `netdev`, `bluetooth`, `lpadmin` when present).
- Root is locked unless `user.root_password` is set.
- `NetworkManager`, `firewalld`, `bluetooth`, `fstrim.timer`,
  `systemd-timesyncd` and `zramswap` are enabled when present.
- The display manager is enabled based on the edition
  (`sddm`/`gdm3`/`lightdm`).
- `/etc/apt/apt.conf.d/99deblite` keeps `Install-Recommends` and
  `Install-Suggests` off in the installed system too.

## Privilege model

The GTK wizard runs as the unprivileged live user. It serialises the config to
stdin and runs:

```sh
sudo -n /usr/bin/deblite-installer --headless --config - --yes
```

The live ISO ships a scoped sudoers rule for exactly that command
(`/etc/sudoers.d/deblite-installer`). The package is removed from the target,
so the rule does not survive installation.

## JSON config

```json
{
  "flavor": "kde",
  "disk": {
    "device": "/dev/nvme0n1",
    "mode": "erase_disk",
    "firmware": "auto",
    "esp_size_mib": 512,
    "boot_size_mib": 1024,
    "swap_size_mib": 0,
    "filesystem": "ext4"
  },
  "luks": {
    "enabled": true,
    "passphrase": "correct horse battery staple"
  },
  "user": {
    "username": "alice",
    "full_name": "Alice",
    "password": "hunter2",
    "is_admin": true,
    "root_password": "",
    "autologin": false
  },
  "locale": {
    "locale": "en_US.UTF-8",
    "keymap": "us",
    "timezone": "Europe/Berlin"
  },
  "network": {
    "hostname": "deblite"
  },
  "source": "",
  "skip_delive": false,
  "keep_live_user": false
}
```

`firmware` is `auto`, `uefi` or `bios`. `mode` is currently limited to
`erase_disk`. `source` can point at a specific `filesystem.squashfs`;
otherwise the installer searches the standard live-medium paths.

## CLI

```sh
sudo deblite-installer                  # interactive wizard
sudo deblite-installer --headless -c install.json --yes
sudo deblite-installer --headless -c - --yes < install.json
sudo deblite-installer --list-disks      # JSON for scripts
sudo deblite-installer --debug ...       # dry-run, no root required
```

Exit codes: `0` success, `1` install/privilege failure, `2` invalid config or
usage, `130` interrupted.

## Recovery

If the installed system does not boot:

1. Boot the ISO again.
2. Open a terminal and mount the target manually.
3. Run `deblite-installer --debug` to inspect the generated commands, or
   `arch-chroot`-style with `chroot /mnt` after bind-mounting `/dev`, `/proc`,
   `/sys` and `/run`.
4. Re-run `grub-install` and `update-initramfs` inside the chroot.
