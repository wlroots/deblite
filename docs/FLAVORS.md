# Editions

Every edition starts from `config/common` (kernel, firmware, NetworkManager,
firewalld, PipeWire, Bluetooth, zram, Neovim, GIMP, ONLYOFFICE, Helium) and
adds a curated desktop on top. No edition installs recommends or suggests.

## KDE Plasma (`kde`)

- `kde-plasma-desktop`, `plasma-desktop`, `plasma-workspace`
- `plasma-nm`, `plasma-pa`, `bluedevil`
- `dolphin`, `konsole`, `kate`, `ark`, `kde-spectacle`
- `kwin-x11`, `kwin-wayland`, `xwayland`
- `sddm` + `sddm-theme-breeze`, `polkit-kde-agent-1`,
  `xdg-desktop-portal-kde`
- Breeze icons and GTK style bridge

Autologin: `/etc/sddm.conf.d/50-deblite-autologin.conf` (`Session=plasmax11`).

## GNOME (`gnome`)

Curated package list instead of `gnome-core`, which would pull
`gnome-software`, Maps, Weather, Contacts, Calendar, Clocks, `simple-scan`,
`cups`, `evolution-data-server` and `orca`.

Included: `gnome-shell`, `gnome-session`, `gnome-settings-daemon`,
`gnome-control-center`, `nautilus`, `gnome-terminal`, `gnome-text-editor`,
`gnome-disk-utility`, `gnome-system-monitor`, `gnome-calculator`,
`gnome-font-viewer`, `gnome-logs`, `loupe`, `papers`, `file-roller`,
`gnome-tweaks`, `gvfs`, `gdm3`, `gnome-bluetooth-sendto`,
`network-manager-gnome`, `xdg-desktop-portal-gnome`, `power-profiles-daemon`.

Autologin: GDM has no drop-in directory, so the live hook edits
`/etc/gdm3/daemon.conf` directly (and the installer does the same for an
installed system).

## GNOME backports (`gnome-backports`, deferred)

Not buildable today: official `trixie-backports` has no `gnome-shell`,
`mutter` or `gnome-control-center`. The scaffold is kept, the build script
refuses it unless `DEBLITE_EXPERIMENTAL=1`, and the CI matrix does not include
it. See `config/flavors/gnome-backports/README.md`.

## XFCE + Greybird (`xfce`)

- `xfce4`, `xfce4-terminal`, `thunar`, `thunar-volman`
- `xfce4-power-manager`, `xfce4-pulseaudio-plugin`, `xfce4-screenshooter`,
  `xfce4-notifyd`, `xfce4-appfinder`, `xfce4-clipman-plugin`,
  `xfce4-taskmanager`, `xfce4-systemload-plugin`
- `network-manager-gnome` (nm-applet), `blueman`, `pavucontrol`
- `greybird-gtk-theme`, `elementary-xfce-icon-theme`, `tango-icon-theme`
- `lightdm` + `lightdm-gtk-greeter` + `mate-polkit`

Greybird is applied system-wide through
`/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/{xsettings,xfwm4}.xml`.

## Cinnamon + Mint-Y (`cinnamon`)

- `cinnamon`, `nemo`, `cinnamon-settings-daemon`,
  `cinnamon-control-center`, `cinnamon-session`, `muffin`
- `network-manager-gnome`, `blueman`, `pavucontrol`, `gnome-terminal`,
  `file-roller`
- `mint-y-icons` (Debian) and `mint-themes` plus its `mint-x-icons`
  dependency (vendored from upstream, because Debian packages neither)
- `lightdm` + `slick-greeter` + `mate-polkit`
- Cinnamon integration: `xdg-desktop-portal-gtk`,
  `xdg-desktop-portal-xapp`, `libxapp-gtk3-module`, `metacity-common`,
  `xapp-sn-watcher`, `libcanberra-pulse`

Mint-Y is applied through a system dconf database
(`/etc/dconf/db/local.d/00-deblite`) plus a Slick Greeter theme. The dconf
database is compiled by `config/flavors/cinnamon/hooks/normal/0500-dconf.hook.chroot`.

## Autologin and first boot

The live session autologs in as `user`. The installer removes the live
autologin settings and, if the operator asked for autologin, writes a fresh
one for the real account (SDDM and LightDM drop-ins; GDM's `daemon.conf`
directly). Otherwise the installed system shows the display manager's login
screen.

## Adding an edition

1. Create `config/flavors/<name>/package-lists/10-desktop.list.chroot`.
2. Add display-manager/autologin includes under
   `config/flavors/<name>/includes.chroot/`.
3. Add theming files and, if needed, a `hooks/normal/` hook.
4. Add `<name>` to the matrix in `.github/workflows/build.yml` and to
   `FLAVORS` in the `Makefile`.
5. Run `sudo ./scripts/build-iso.sh <name>` and check
   `verify-iso.sh` / `audit-bloat.sh`.
