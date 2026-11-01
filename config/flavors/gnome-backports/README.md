# Backported GNOME — deferred

The goal of this edition is "the newest GNOME that can run on a Debian 13
(Trixie) base".

**Blocker (verified):** official `trixie-backports` does not contain
`gnome-shell`, `mutter` or `gnome-control-center`. Trixie ships GNOME 48.7,
and Debian does not backport entire desktop environments. As a result there is
no supported way to get GNOME 49 on a stock Trixie base from official Debian
repositories.

The package list and the rest of the flavor scaffold are kept here so the
edition can be enabled as soon as Debian starts backporting the shell. The
build script refuses to build it unless `DEBLITE_EXPERIMENTAL=1` is set.

Options if this is needed sooner:

1. **Pin GNOME 49 from Debian unstable** — a frankendebian. Pinning can pull a
   newer glibc and core libraries, and is not supported. Only do this if you
   accept that upgrades may break.
2. **Ship newer GNOME apps as Flatpaks** — keeps the supported GNOME 48 shell
   but adds a Flatpak runtime and network access at build time.
3. **Wait for official backports** — the clean option.

When enabling, add `gnome-backports` to the CI matrix and verify that
`gnome-shell`, `mutter` and `gnome-control-center` resolve to the intended
version with `apt-cache policy` inside the build chroot.
