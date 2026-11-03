# DebLite

**A lean Debian 13 desktop, without the bloat.**

DebLite is an independent Debian 13 (Trixie) based desktop distribution. It
ships four polished editions, a small custom installer, and a deliberately
minimal set of preinstalled software: no recommends, no suggests, no
heavyweight suites you did not ask for.

- **Debian stable underneath** — the same packages, security updates and
  repositories you already trust.
- **Four editions** — KDE Plasma, GNOME, XFCE and Cinnamon.
- **Lean by default** — Neovim, GIMP, ONLYOFFICE and Helium are included;
  LibreOffice, games and heavyweight meta-packages are not.
- **Custom installer** — a GTK4 wizard, a text-mode wizard and a headless JSON
  mode. No Calamares and no Debian installer.
- **Encryption when you want it** — optional LUKS2 full-disk encryption with a
  separate `/boot`, ext4, Btrfs or XFS.

DebLite is not affiliated with or endorsed by the Debian Project.

## Contents

- [Editions](#editions)
- [Requirements](#requirements)
- [Download](#download)
- [Verify the download](#verify-the-download)
- [Write a USB stick](#write-a-usb-stick)
- [Boot the live system](#boot-the-live-system)
- [Install DebLite](#install-deblite)
- [First boot](#first-boot)
- [Included software](#included-software)
- [Troubleshooting](#troubleshooting)
- [Recovery](#recovery)
- [Getting help](#getting-help)
- [Building from source](#building-from-source)
- [Contributing](#contributing)
- [License](#license)

## Editions

Every edition uses the same Debian base, kernel, firmware and core
applications. Pick the desktop you like; the underlying system is identical.

| Edition | Desktop | Login screen | Theme | ISO | Best for |
|---|---|---|---|---|---|
| **KDE Plasma** | Plasma 6 | SDDM | Breeze | `deblite-13-kde-amd64.iso` | A full-featured, highly configurable desktop |
| **GNOME** | GNOME 48 | GDM3 | Adwaita | `deblite-13-gnome-amd64.iso` | A clean, modern, keyboard-friendly workflow |
| **XFCE** | XFCE 4.20 | LightDM GTK | Greybird | `deblite-13-xfce-amd64.iso` | The lightest footprint and the fastest start |
| **Cinnamon** | Cinnamon 6.4 | LightDM + Slick Greeter | Mint-Y | `deblite-13-cinnamon-amd64.iso` | A familiar, traditional desktop layout |

A `gnome-backports` edition is scaffolded in the source tree but is not built:
official `trixie-backports` does not provide the modern GNOME shell, mutter or
control center. Use the regular GNOME 48 edition.

## Requirements

| | Minimum | Recommended |
|---|---|---|
| CPU | 64-bit x86 (amd64), 2 cores | Any recent x86-64 CPU |
| RAM | 2 GB for XFCE, 4 GB for KDE/GNOME/Cinnamon | 8 GB |
| Disk | 12 GB free | 25 GB or more |
| USB stick | 4 GB | 8 GB |
| Firmware | BIOS or UEFI | UEFI |

- **Secure Boot must be disabled.** DebLite uses unsigned GRUB. See
  [Troubleshooting](#troubleshooting).
- **Only 64-bit x86 is supported.** There are no ARM or 32-bit images.
- **The installer erases the selected disk.** There is currently no
  alongside-Windows or manual-partition mode. Back up first, and double-check
  the target disk.
- **An internet connection is recommended** so you can install updates after
  the first boot. Installation itself works offline.
- **NVIDIA:** the open-source `nouveau` driver and NVIDIA firmware are
  included. The proprietary NVIDIA driver is not preinstalled; install it from
  Debian's `non-free` repository if you need it.
- **Wi-Fi and graphics firmware** for common Intel, AMD, Realtek, Broadcom,
  Atheros and MediaTek hardware is included.

## Download

Download the edition you want from the
[latest DebLite release](https://github.com/wlroots/deblite/releases/latest).
Release tags follow Debian point releases, for example `v13.7`.

Each release provides, per edition:

```
deblite-13-kde-amd64.iso              the bootable image
deblite-13-kde-amd64.iso.sha256       SHA-256 checksum
deblite-13-kde-amd64.iso.manifest.json  build and version metadata
```

The manifest records the edition, Debian point release, compression, git
commit, build time and ISO checksum. Keep it with the ISO if you archive the
image.

## Verify the download

A corrupt or truncated ISO is the most common cause of a failed USB write.
Check the checksum before writing.

**Linux**

```sh
cd ~/Downloads
sha256sum -c deblite-13-kde-amd64.iso.sha256
```

**macOS**

```sh
shasum -a 256 deblite-13-kde-amd64.iso
```

**Windows (PowerShell)**

```powershell
Get-FileHash .\deblite-13-kde-amd64.iso -Algorithm SHA256
```

Compare the printed hash with the first field of the `.sha256` file. If they
differ, download the ISO again.

## Write a USB stick

> **Warning:** this erases the entire USB stick. Make sure you identify the
> right device; `/dev/sda` is often your system disk, not your USB stick.

**Linux**

```sh
lsblk                         # find the USB device, e.g. /dev/sdb
sudo dd if=deblite-13-kde-amd64.iso of=/dev/sdb \
    bs=4M status=progress oflag=sync
sync
```

Use the whole-disk device (`/dev/sdb`), not a partition (`/dev/sdb1`).

**macOS**

> [!NOTE]
> DebLite doesn't support ARM64 (Apple Silicon based) devices.
>
> It supports only legacy Intel-based devices, if you want Linux on your MacBook, use [Asahi Linux](https://asahilinux.org/), sorry for inconvinience

```sh
diskutil list                 # find the USB disk, e.g. /dev/disk4
diskutil unmountDisk /dev/disk4
sudo dd if=deblite-13-kde-amd64.iso of=/dev/rdisk4 bs=4m
```

**Windows**

Use [Rufus](https://rufus.ie/)
In Rufus, select the ISO, choose **GPT** for UEFI systems, and write in **DD
mode** if prompted.

**System-independent (recommended)**

Use [balenaEtcher](https://etcher.balena.io/). Its available for Linux, Windows, macOS

You can also use [Ventoy](https://ventoy.net/). It supports Linux, Windows and can be installed from LiveUSB and you can write files on a flash drive, or have multiple ISOs

## Boot the live system

1. Insert the USB stick and reboot.
2. Open the firmware boot menu (often `F12`, `F11`, `F10`, `Esc` or `Del`) and
   select the USB device.
3. **Disable Secure Boot** in the firmware settings if the USB entry refuses to
   start. See [Troubleshooting](#troubleshooting).
4. Choose the UEFI entry for best results; BIOS/legacy boot also works.

The live session logs in automatically as `user` and starts the graphical
installer. The live user has passwordless `sudo`; nothing is written to your
disk until you confirm the installation.

If the wizard does not appear, open a terminal and run:

```sh
sudo deblite-installer --gui     # graphical wizard
sudo deblite-installer           # text-mode wizard
```

The live session is not persistent. Any files you create there disappear on
reboot, so copy anything you need to another drive before rebooting.

The same ISO also boots in VirtualBox, VMware, QEMU and other hypervisors,
which is a convenient way to try an edition before installing it.

## Install DebLite

The wizard walks through six screens:

1. **Welcome** — review the warning and choose **Start**.
2. **Locale** — language, keyboard layout and timezone (for example
   `Europe/Berlin`).
3. **Disk & Partitioning** — choose the target disk, firmware mode (leave
   **Auto-detect** unless you have a reason not to), root filesystem
   (`ext4`, `btrfs` or `xfs`), and the sizes of the EFI system partition,
   optional separate `/boot` and optional swap. `0` MiB swap means no swap
   partition; zram swap is enabled regardless.
4. **Encryption** — optionally enable LUKS2 full-disk encryption and enter a
   passphrase twice. With encryption on, a separate unencrypted `/boot`
   partition is created automatically so GRUB can load the kernel.
5. **User** — username, full name, password, optional root password,
   administrator privileges, autologin and hostname. Most desktop users want
   administrator privileges on and autologin off.
6. **Confirm** — review the summary, choose **Install**, and wait for the
   progress screen.

> **Everything on the selected disk is erased.** That includes other operating
> systems, their boot loaders and all data. Disconnect drives you do not want to
> touch, and verify the disk model and size on the disk screen.

When the install finishes, shut down, remove the USB stick, and boot the
machine. GRUB starts the installed system.

### Partition layout

The installer creates a GPT layout:

- an EFI system partition (UEFI) or a 1 MiB BIOS boot partition (BIOS);
- an optional `/boot` partition, only when LUKS is enabled;
- an optional swap partition;
- the root filesystem.

GRUB is installed for UEFI (`x86_64-efi`, with a removable
`EFI/BOOT/BOOTX64.EFI` fallback) or BIOS (`i386-pc`) automatically. The
installed boot loader is unsigned.

### What the installer changes

The installed system is a copy of the live root filesystem with the live
session removed: live packages are purged, live autologin is cleared, the live
`user` account is removed unless you chose the same name, machine-id and SSH
host keys are reset, and the target is reconfigured with your user, locale,
keymap, timezone, hostname, services, firewall, fstab and initramfs. The
installer package itself is removed from the target.

## First boot

Log in with the user you created (or let autologin take you straight to the
desktop).

1. **Connect to the network.** Use the NetworkManager applet in your desktop's
   system tray or settings.
2. **Update the system:**

   ```sh
   sudo apt update
   sudo apt full-upgrade
   ```

   Reboot if the kernel or graphics stack was updated.
3. **Check the firewall.** `firewalld` is installed and enabled:

   ```sh
   sudo firewall-cmd --state
   sudo firewall-cmd --list-all
   ```

4. **Check swap and trim.** zram swap, periodic TRIM (`fstrim.timer`) and
   network time sync (`systemd-timesyncd`) are enabled by default:

   ```sh
   zramctl
   systemctl status fstrim.timer
   ```

5. **Install what you need.** DebLite keeps Debian's no-recommends policy on
   the installed system:

   ```sh
   sudo apt install --no-install-recommends <package>
   ```

   If you prefer the full dependency set for a package, drop
   `--no-install-recommends`.

DebLite does not add telemetry or require an account. ONLYOFFICE and Helium
update from their own official repositories, which are already configured.

## Included software

**Every edition**

| Category | Software |
|---|---|
| Kernel and hardware | Linux 6.12, desktop firmware, Intel/AMD microcode |
| Desktop core | NetworkManager, PipeWire/WirePlumber, Bluetooth, zram, timesync |
| Virtual machines | QEMU guest agent, `open-vm-tools` |
| Security | `firewalld`, LUKS2, `sudo`, GRUB (BIOS + UEFI) |
| Applications | **Neovim**, **GIMP**, **ONLYOFFICE Desktop Editors**, **Helium** |
| Utilities | `htop`, `less`, `curl`, `wget`, `gnupg`, standard CLI tools, Noto fonts |

**Desktop extras**

- **KDE Plasma** — Dolphin, Konsole, Kate, Ark, Spectacle, system settings,
  Breeze icons and theme.
- **GNOME** — Nautilus, GNOME Terminal, Text Editor, Disk Utility, System
  Monitor, Calculator, Logs, Loupe, Papers, Tweaks.
- **XFCE** — Thunar, XFCE Terminal, screenshooter, task manager, clipman,
  Greybird theme and Elementary XFCE icons.
- **Cinnamon** — Nemo, Cinnamon settings, GNOME Terminal, file roller,
  Mint-Y theme and Mint-X/Mint-Y icons.

**Deliberately absent:** LibreOffice, Thunderbird/Evolution, GNOME Software,
GNOME Maps/Weather/Contacts/Calendar/Clocks, games, `xfce4-goodies`,
`kde-applications` and other heavy meta-packages. Install them later if you
want them; DebLite will not pull them in for you.

## Troubleshooting

**The USB stick will not boot / "Verification failed" / Secure Boot error**

Secure Boot is not supported. Enter the firmware settings and disable Secure
Boot (sometimes called "UEFI Secure Boot", "Platform Key", "Windows UEFI
mode" or "OS Mode: Windows 8 or 10"), then boot the USB again. If the USB entry is missing, try the
legacy/BIOS entry or rewrite the stick in DD mode.

**UEFI boot panics with "VFS: Unable to mount root fs on unknown-block(0,0)"**

The kernel did not get the initramfs, so it has no live root filesystem to
mount. On UEFI, GRUB hands the initramfs over through the firmware's EFI
services, and some older firmware loses it. Boot the stick again and pick
"Live system (amd64, UEFI compatibility mode)" in the GRUB menu: that entry
uses the same kernel with GRUB's classic loader, which places the initramfs in
memory itself. The entry only appears on UEFI boots. Booting the legacy/BIOS
entry works too, but then the installer can only install in BIOS mode.

**The graphical installer does not start**

Open a terminal in the live session and run `sudo deblite-installer --gui`.
If the GUI cannot start, use the text wizard: `sudo deblite-installer`.

**"No disks found"**

Check that the drive is not hidden behind Intel RST/RAID or a firmware
"RAID On" SATA mode. Switch the controller to AHCI if you do not need the RAID
array. Also confirm the disk is properly seated and detected in the firmware.

**No Wi-Fi**

Most common Wi-Fi firmware is included, but some chips need extra packages.
Identify the chip and install the matching firmware after connecting by
Ethernet or USB tethering:

```sh
lspci -k | grep -A3 -i network
sudo apt install --no-install-recommends firmware-iwlwifi    # Intel
sudo apt install --no-install-recommends firmware-realtek    # Realtek
sudo apt install --no-install-recommends firmware-brcm80211  # Broadcom
```

**Black screen after installing (NVIDIA)**

DebLite includes `nouveau` and NVIDIA firmware, not the proprietary driver.
If the desktop does not start, boot with `nomodeset` added to the kernel
command line, then install `nvidia-driver` from Debian's `non-free` repository.
For hybrid Intel/NVIDIA laptops, check the firmware's graphics mode.

**The installer stopped or failed**

Re-run it from the live session:

```sh
sudo deblite-installer            # text wizard, shows the failing command
sudo deblite-installer --debug    # dry run: prints commands, writes nothing
```

The GUI shows the command log on its progress screen. For a reproducible
report, include that log with your issue.

**The installed system does not boot**

Boot the ISO again and use the [recovery](#recovery) steps below.

## Recovery

The simplest recovery for an erased-disk install is to boot the ISO and install
again. If you need to repair the existing system:

1. Boot the live ISO.
2. Open a terminal and identify the target partitions with `lsblk -f`.
3. Open LUKS if used: `sudo cryptsetup open /dev/<partition> cryptroot`.
4. Mount the root filesystem, plus the ESP at `/boot/efi` when present.
5. Bind-mount `/dev`, `/dev/pts`, `/proc`, `/sys` and `/run` into the target.
6. `chroot` into it and re-run:

   ```sh
   grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=DebLite
   update-grub
   update-initramfs -u -k all
   ```

Use `--target=i386-pc` on BIOS systems. See the
[installer documentation](https://github.com/wlroots/deblite-installer/blob/main/docs/INSTALLER.md)
for the full partition layout, LUKS details and de-live cleanup.

## Getting help

- **Issues:** <https://github.com/wlroots/deblite/issues>
- **Installer project:** <https://github.com/wlroots/deblite-installer>

When reporting a problem, include:

- the edition and ISO file name;
- the checksum or the contents of the `.manifest.json`;
- your hardware (CPU, GPU, Wi-Fi chip, firmware mode: UEFI or BIOS);
- what you did, what you expected, and the exact error message or screenshot;
- the installer output from the progress screen if the install failed.

Please verify the ISO checksum and try the text-mode installer before filing a
bug; those two steps resolve many reports.

## Building from source

Building DebLite requires Debian 13 (Trixie) and root, because `live-build`
creates chroots, mounts filesystems and writes loop devices.

```sh
sudo apt-get install live-build debootstrap xorriso squashfs-tools \
    syslinux syslinux-common isolinux \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
    rsync curl ca-certificates gnupg shellcheck

make check
sudo make iso FLAVOR=kde      # one edition, zstd
sudo make all                 # all four release ISOs, xz
```

Output lands in `out/` as the ISO, its `.sha256` and a `.manifest.json`.
Release builds enforce GitHub's 2 GiB per-asset limit.

Every edition uses the wallpapers from the separate
[`deblite-artwork`](https://github.com/wlroots/deblite-artwork) repository,
pinned and checksum-verified by the build. For local builds, point
`DEBLITE_ARTWORK_DIR` at a checkout or `DEBLITE_ARTWORK_ARCHIVE` at a release
tarball and use `sudo -E`. KDE, GNOME, XFCE and Cinnamon each receive a
system-wide default; without artwork they keep their built-in wallpaper. See
[`docs/BUILD.md`](docs/BUILD.md#artwork).

The installer is a separate project,
[`deblite-installer`](https://github.com/wlroots/deblite-installer). ISO builds
consume a pinned installer `.deb` release listed in `installer-release.env`;
they never compile the installer from source.

See [`docs/BUILD.md`](docs/BUILD.md) for the full build and installer-pinning
guide, and [`docs/CI.md`](docs/CI.md) for the CI/CD workflows.

## Contributing

Contributions are welcome, including those made with AI assistance. Using AI
is **not prohibited**. What matters is the result: the code and docs must be
clean, minimal, tested, and consistent with the project's conventions.

If you use an AI tool, you are still responsible for the change. Review every
line, run the relevant checks, and do not submit generated code you cannot
explain. Report what you actually built and tested. Fabricated test results,
invented links and unverified claims are not acceptable.

Before opening a pull request:

```sh
make check
sudo ./scripts/build-iso.sh <edition>
./scripts/verify-iso.sh out/deblite-13-<edition>-amd64.iso
./scripts/audit-bloat.sh out/deblite-13-<edition>-amd64.iso
```

See [`AGENTS.md`](AGENTS.md) for the full contributor and agent guidelines,
including the project invariants and testing matrix.

## License

MIT. See [`LICENSE`](LICENSE).
