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
    python3-pytest shellcheck
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
reuses an existing directory for debugging.

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
`config/common/package-lists/00-base.list.chroot`, which avoids pulling
`firmware-nvidia-tesla-*`, `dahdi-firmware-nonfree`, `atmel-firmware` and
similar packages that are not needed on a desktop.

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

Debian ships `mint-y-icons` but not `mint-themes`. For the Cinnamon edition,
`scripts/fetch-vendor-debs.sh` downloads the pinned upstream
`packages.tar.gz`, extracts `mint-themes_*_all.deb` and places it in
`config/packages.chroot/`.

The DebLite installer itself is built by
`scripts/build-installer-deb.sh` and also placed in `packages.chroot`.

## Verification

Every build runs:

```sh
./scripts/verify-iso.sh out/deblite-13-<flavor>-amd64.iso
./scripts/audit-bloat.sh out/deblite-13-<flavor>-amd64.iso
```

`verify-iso.sh` checks the squashfs for the kernel, initrd, apt, GRUB modules,
the installer, the baked edition (`/etc/deblite-flavor`), the core applications
(Neovim, GIMP, ONLYOFFICE, firewalld) and the lean apt policy, and confirms
that d-i/Calamares are absent. `audit-bloat.sh` parses `var/lib/dpkg/status`
and fails on the denylist (LibreOffice, Thunderbird, GNOME extras, games,
heavy meta-packages).

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

This only checks that the ISO reaches a Linux/systemd boot banner. For a real
install test, run the installer against a loop-backed disk image:

```sh
sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso
sudo ./scripts/test-install.sh out/deblite-13-xfce-amd64.iso --luks
```

The script partitions a sparse image, copies the ISO's squashfs, runs the
headless installer, then mounts the result and checks GRUB, fstab, the user
account, the hostname and that the live packages are gone. It forces the BIOS
layout so it cannot write NVRAM entries on the build host. Test UEFI boot and
the GRUB menu in a VM.
