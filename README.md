# DebLite

DebLite is a lean Debian 13 (Trixie) desktop distribution with a custom
installer. It is built with Debian's own `live-build`, ships one ISO per
edition, and deliberately installs **no recommends and no suggests**.

The original Arch installer in `arch-installer/` is kept as the reference
implementation. The production installer lives in `installer/` and targets
Debian.

## Editions

| Edition | Desktop | Display manager | Theme |
|---|---|---|---|
| `kde` | KDE Plasma 6 | SDDM | Breeze |
| `gnome` | GNOME 48 | GDM3 | Adwaita |
| `xfce` | XFCE 4.20 | LightDM GTK | Greybird |
| `cinnamon` | Cinnamon 6.4 | LightDM + Slick Greeter | Mint-Y |
| `gnome-backports` | *scaffolded, not built* | — | — |

`gnome-backports` is deferred because official `trixie-backports` does not
contain `gnome-shell`/`mutter`. See
[`config/flavors/gnome-backports/README.md`](config/flavors/gnome-backports/README.md).

## What is in every edition

- Linux 6.12, firmware, microcode
- NetworkManager + **firewalld**
- PipeWire/WirePlumber, Bluetooth, zram
- **Neovim**, **GIMP**, **ONLYOFFICE Desktop Editors**, **Helium**
- LUKS2 + initramfs-tools, GRUB for BIOS and UEFI
- The DebLite installer (GTK4/libadwaita + CLI + headless JSON)

## What is deliberately absent

LibreOffice, Thunderbird/Evolution, GNOME Software, GNOME Maps/Weather/
Contacts/Calendar/Clocks, games, `xfce4-goodies`, `kde-applications` and the
other heavy meta-packages. `scripts/audit-bloat.sh` fails the build if one of
them sneaks in through a dependency.

## Repository layout

```
installer/                  UI-agnostic core + CLI + GTK4 frontend
packaging/deblite-installer/  the .deb installed into the live ISO
config/common/              shared package lists, hooks, includes
config/flavors/<name>/      per-edition packages, theming, autologin
scripts/                    build, verify, audit, release helpers
tests/                      pytest suite (including a full dry-run)
.github/workflows/          CI, ISO matrix, Debian point-release watcher
docs/                       build, installer, flavors and CI notes
```

## Quick start

Build prerequisites on Debian 13:

```sh
sudo apt-get install live-build debootstrap xorriso squashfs-tools \
    syslinux syslinux-common isolinux \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
    rsync curl ca-certificates gnupg python3-pytest shellcheck
```

Run the tests and build one edition:

```sh
make test
sudo make iso FLAVOR=kde
```

The ISO, its SHA256 and a manifest land in `out/`:

```
out/deblite-13-kde-amd64.iso
out/deblite-13-kde-amd64.iso.sha256
out/deblite-13-kde-amd64.iso.manifest.json
```

Build all four:

```sh
sudo make all
```

Release builds use xz instead of zstd and enforce GitHub's 2 GiB asset limit:

```sh
sudo ./scripts/build-iso.sh cinnamon --release
```

## Installer

The live session logs in automatically as `user` and starts the GTK4 wizard.
The GUI is unprivileged; it sends a JSON config to the privileged helper:

```sh
sudo -n /usr/bin/deblite-installer --headless --config - --yes
```

Text mode:

```sh
sudo deblite-installer
```

Headless (CI / automation):

```sh
sudo deblite-installer --headless --config install.json --yes
```

Dry-run anywhere (no root, no disk writes):

```sh
./bin/deblite-installer --headless --config install.json --debug
```

See [`docs/INSTALLER.md`](docs/INSTALLER.md) for the JSON schema, partition
layout, LUKS behaviour and the de-live cleanup.

## CI/CD

- `.github/workflows/ci.yml` — tests, lint, `.deb` build.
- `.github/workflows/build.yml` — matrix build of all editions on pushes,
  tags and manual runs; publishes a GitHub Release on tags.
- `.github/workflows/check-debian.yml` — daily check for a new Debian 13
  point release; tags it so the build workflow publishes it.

See [`docs/CI.md`](docs/CI.md).

## Known limitations

- **GitHub release assets are capped at 2 GiB per file.** Release builds use
  xz and a size guard. If a future ISO exceeds the limit, the release job
  stops before uploading; splitting or external storage is then required.
- **ONLYOFFICE still declares pre-t64 dependency names.** Trixie's `t64`
  packages provide those names, so apt resolves them. If the repository still
  fails, the build hook falls back to the official `.deb`.
- **GNOME 49 on stable is not possible from official repositories today.**
  The `gnome-backports` flavor is scaffolded and documented but not built.
- The installer currently supports **erase-disk** partitioning only. Manual
  and existing-layout modes are planned.

## License

MIT. See [`LICENSE`](LICENSE).
