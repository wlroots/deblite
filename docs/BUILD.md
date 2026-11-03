# Building DebLite

## Prerequisites

On Debian 13 (Trixie):

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools \
    syslinux syslinux-common isolinux \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
    rsync curl ca-certificates gnupg \
    shellcheck
```

`live-build` must run as root because it creates chroots, mounts filesystems
and writes loop devices. `scripts/build-iso.sh` re-executes itself with
`sudo` when needed.

## One edition

```sh
sudo ./scripts/build-iso.sh kde
```

Output:

```
out/deblite-13-kde-amd64.iso
out/deblite-13-kde-amd64.iso.sha256
out/deblite-13-kde-amd64.iso.manifest.json
```

Build directories are kept under `build/<flavor>/`. They contain
`build.log`, the generated live-build config and the chroot; `--no-clean`
reuses an existing directory for debugging. A clean build keeps live-build's
`cache/` directory (packages, bootstrap), so rebuilding an edition after a
config change does not re-download everything.

## All editions

```sh
sudo make all
```

or directly:

```sh
for flavor in kde gnome xfce cinnamon; do
    sudo ./scripts/build-iso.sh "$flavor" --release
done
```

## Compression

- `zstd` (default) — fast, larger. Good for PRs and local testing.
- `xz` (`--release`) — smaller, slower. Used for published ISOs.

Both are passed to live-build as `--chroot-squashfs-compression-type`.

## live-build options

`scripts/build-iso.sh` configures:

```
--distribution trixie
--architectures amd64
--binary-images iso-hybrid
--archive-areas "main contrib non-free non-free-firmware"
--apt-recommends false
--apt-options "--yes --no-install-recommends --no-install-suggests"
--apt-indices false
--debootstrap-options "--variant=minbase"
--bootloaders "syslinux grub-efi"
--uefi-secure-boot auto
--debian-installer none
--memtest none
--firmware-chroot false
--bootappend-live "boot=live components quiet"
```

`--debian-installer none` guarantees that d-i is not on the medium. Calamares
is never added. The installer is the only install path.

`--firmware-chroot false` disables live-build's own firmware metapackage set.
DebLite curates firmware explicitly in
`config/common/package-lists/05-firmware.list.chroot`, which avoids pulling
`firmware-nvidia-tesla-*`, `dahdi-firmware-nonfree`, `atmel-firmware` and
similar packages that are not needed on a desktop.

## Firmware

`config/common/package-lists/05-firmware.list.chroot` lists the firmware for
hardware found in laptops, desktops and workstations: AMD, Intel and NVIDIA
graphics, Wi-Fi, Bluetooth, audio DSPs, card readers and capture cards.
`scripts/verify-iso.sh` parses the list and fails unless every package is
installed in the image.

The list deliberately excludes:

- `firmware-linux` and `firmware-linux-nonfree`, metapackages that duplicate
  entries already selected explicitly. Keeping the list explicit lets
  `verify-iso.sh` assert each package and keeps the exclusions documented.
  The full set of `firmware-*` packages is about 1.2 GiB installed; this
  curated list is about 620 MiB.
- `firmware-b43-installer` and `firmware-b43legacy-installer`, which download
  proprietary blobs during `postinst` and break reproducible offline builds.
- Server and enterprise network firmware (`firmware-bnx2*`, `firmware-cavium`,
  `firmware-marvell-prestera`, `firmware-myricom`, `firmware-netronome`,
  `firmware-netxen`, `firmware-qlogic`).
- Server BMC, ARM SoC and data-centre GPU firmware (`firmware-ast`,
  `firmware-samsung`, `firmware-qcom-soc`, `firmware-nvidia-tesla-535-gsp`).

Microcode (`intel-microcode`, `amd64-microcode`), `wireless-regdb` and
`bluez-firmware` stay in `00-base.list.chroot` because they are part of the
base system rather than device firmware.

## Virtual machine guest integration

Every edition ships `qemu-guest-agent` and `open-vm-tools`. The live root
filesystem is copied to the target, so the installed system keeps them.
`0400-guest-tools.hook.chroot` enables `open-vm-tools.service`;
`qemu-guest-agent` is started by its udev rule when the virtio-serial port is
present. `verify-iso.sh` checks for `/usr/sbin/qemu-ga`, `/usr/bin/vmtoolsd`
and the enabled VMware unit.

## Third-party repositories

`config/common/hooks/normal/0100-thirdparty.hook.chroot` adds:

- Helium: `https://pkg.helium.computer/deb stable main`
- ONLYOFFICE: `https://download.onlyoffice.com/repo/debian squeeze main`

Keys are dearmored into `/etc/apt/keyrings` and referenced with `signed-by=`.
This is required because `apt-key` was removed in Trixie and live-build's
`.key.chroot` support still calls it.

Both repositories stay enabled in the installed system so the applications
can update normally.

## Vendored packages

Debian ships `mint-y-icons` but neither `mint-themes` nor its
`mint-x-icons` dependency. For the Cinnamon edition,
`scripts/fetch-vendor-debs.sh` downloads the pinned upstream
`packages.tar.gz`, extracts `mint-themes_*_all.deb`, pulls
`mint-x-icons_*_all.deb` from the Linux Mint package repository and places
both in `config/packages.chroot/`.

## Artwork

Custom wallpapers are not stored in this repository. Drop images into
`../deblite-artwork/wallpapers` (a sibling of this checkout) before building,
or point `DEBLITE_ARTWORK_DIR` at another directory. `scripts/install-artwork.sh`
copies the supported images (`.jpg`, `.jpeg`, `.png`, `.webp`, `.svg`) into
`/usr/share/backgrounds/deblite/` and selects one as the default in every
edition:

- **KDE Plasma** — `/usr/libexec/deblite-wallpaper` runs
  `plasma-apply-wallpaperimage` on the first login and then leaves the user's
  choice alone. The hook also points the SDDM Breeze theme at the wallpaper.
- **GNOME** — a system dconf drop-in sets `picture-uri` and
  `picture-uri-dark`; the login screen is unchanged.
- **XFCE** — a system `xfce4-desktop` xfconf default covers four monitors,
  a first-login helper rewrites the monitor properties xfdesktop actually
  creates, and the LightDM GTK greeter background is updated.
- **Cinnamon** — a system dconf drop-in sets the desktop background and the
  Slick Greeter background.

`DEBLITE_WALLPAPER` selects the default by file name; without it the first
image in sort order wins. Both variables must survive `sudo`, so use
`sudo -E` or pass them inline. The script is a no-op when the directory or
the images are missing, and every edition then keeps its built-in wallpaper.

## Installer package

The installer lives in its own repository, `deblite-installer`, and is
published as a `.deb` on `installer-vX.Y.Z` tags. This repository pins the
release in `installer-release.env`:

```sh
DEBLITE_INSTALLER_REPO=          # <owner>/deblite-installer; empty derives from origin
DEBLITE_INSTALLER_VERSION=0.1.0
DEBLITE_INSTALLER_SHA256=
```

Leave `DEBLITE_INSTALLER_REPO` empty to derive `<owner>/deblite-installer`
from the git origin. `scripts/fetch-installer-deb.sh` downloads
`deblite-installer_<version>_amd64.deb` and verifies it against the release's
`SHA256SUMS`; set `DEBLITE_INSTALLER_SHA256` to hard-pin the checksum instead.
Set `DEBLITE_INSTALLER_BASE_URL` to mirror the release assets elsewhere (and
to exercise the download/checksum path in tests).

For offline development, use a package built from the installer checkout:

```sh
DEBLITE_INSTALLER_DEB=/path/to/deblite-installer_0.1.0_amd64.deb \
    sudo -E ./scripts/build-iso.sh kde
```

Publish the installer release first, then bump `DEBLITE_INSTALLER_VERSION`
here. ISO builds no longer compile the installer.

## Verification

Every build runs:

```sh
./scripts/verify-iso.sh out/deblite-13-<flavor>-amd64.iso
./scripts/audit-bloat.sh out/deblite-13-<flavor>-amd64.iso
```

`verify-iso.sh` checks the squashfs for the kernel, initrd, apt, GRUB modules,
the installer, the baked edition (`/etc/deblite-flavor`), the core applications
(Neovim, GIMP, ONLYOFFICE, firewalld), every firmware package in
`05-firmware.list.chroot`, the VM guest agents, and the lean apt policy. It also
confirms that d-i/Calamares are absent. `audit-bloat.sh` parses
`var/lib/dpkg/status` and fails on the denylist (LibreOffice, Thunderbird, GNOME
extras, games, heavy meta-packages).

Set `DEBLITE_ALLOW_BLOAT=1` to turn the audit into warnings while debugging.

## Size budget

GitHub release assets are limited to **2 GiB per file**. `--release` refuses
to publish an ISO at or above that size. Use the manifest to see the exact
byte count.

## QEMU smoke test

```sh
sudo apt-get install qemu-system-x86
./scripts/qemu-smoke.sh out/deblite-13-kde-amd64.iso
```

This extracts `/live/vmlinuz` and `/live/initrd.img`, boots them with QEMU's
serial console and waits for live-boot/systemd markers. It validates the live
rootfs, not the ISO's bootloader; test isolinux/GRUB and UEFI in a VM. For a
real install test, run the installer against a loop-backed disk image:

```sh
sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso
sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso --luks
sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso --boot
```

The script partitions a sparse image, copies the ISO's squashfs, extracts the
installer bundle from that squashfs, runs it in headless mode, then mounts the
result and checks GRUB, fstab, the user account, the hostname and that the
live packages are gone. `--boot` also starts the installed root filesystem in
QEMU with a serial console (non-LUKS only). It forces the BIOS layout so it
cannot write NVRAM entries on the build host. Test UEFI boot and the GRUB menu
in a VM.
