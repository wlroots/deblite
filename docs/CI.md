# CI/CD

The Debian images and the installer have independent release cycles and
repositories.

## ISO repository workflows

### `ci.yml`

Runs on every push and pull request:

- `shellcheck scripts/*.sh`
- `scripts/fetch-installer-deb.sh` against the pinned installer release, then
  `dpkg-deb --info`/`--contents` on the result
- `scripts/fetch-artwork.sh` against the pinned artwork release, which also
  checks its `SHA256SUMS`

The release-check jobs deliberately fail if the pinned `installer-vX.Y.Z` or
`artwork-vX.Y.Z` release or its `SHA256SUMS` asset is missing, because
`build.yml` would fail the same way.

### `build.yml`

Runs on:

- pushes to `main` and tags `v*`
- pull requests (zstd builds, no release)
- `workflow_dispatch` (optional `flavor`, `debian_version`, `release`)
- tags created by the point-release watcher

Matrix: `kde`, `gnome`, `xfce`, `cinnamon`. `gnome-backports` is deliberately
absent.

Each job runs inside `debian:trixie` with `--privileged` (live-build needs
mounts, loop devices and chroot). Steps:

1. Install `live-build` and friends.
2. Download the installer `.deb` pinned in `installer-release.env` and verify
   its checksum. `DEBLITE_INSTALLER_REPO` is set to
   `<repository owner>/deblite-installer`.
3. Download the artwork tarball pinned in `artwork-release.env` and verify its
   checksum. `DEBLITE_ARTWORK_REPO` is set to
   `<repository owner>/deblite-artwork`.
4. `scripts/build-iso.sh <flavor> --release` (xz) or zstd for PRs.
5. `verify-iso.sh` and `audit-bloat.sh`.
6. Upload the ISO, `.sha256` and `.manifest.json` as artifacts.

The release job runs on tags or `release=true`, downloads all artifacts and
publishes one GitHub Release with all four ISOs.

### `check-debian.yml`

Daily at 05:17 UTC:

1. `scripts/check-debian-release.sh` scrapes
   `https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/` for
   `debian-13.X.0-amd64-netinst.iso`.
2. If the version differs from `debian-version.txt`, it commits the new
   version, pushes a `v13.X` tag, and dispatches `build.yml` with
   `release=true`. Pushes made with `GITHUB_TOKEN` do not start other
   workflows, so the explicit `workflow_dispatch` is required.

## Installer repository workflows

The installer lives in `deblite-installer`.

### `ci.yml`

Runs on pushes to `main` and pull requests: `ruff`, `pytest`, `shellcheck` and
a test `.deb` build.

### `release.yml`

Runs when a tag matching `installer-v*` is pushed:

1. Runs the same tests as `ci.yml`.
2. Rejects the tag unless it matches `__version__` in
   `installer/__init__.py` and the version in `pyproject.toml`.
3. Builds `deblite-installer_<version>_amd64.deb`.
4. Publishes a GitHub Release with the `.deb` and `SHA256SUMS`.

To ship an installer update:

```sh
cd deblite-installer
# bump installer/__init__.py and pyproject.toml, commit
git tag installer-v0.2.0
git push origin main installer-v0.2.0
```

Then update `DEBLITE_INSTALLER_VERSION` in `installer-release.env` here and
commit. The next ISO build downloads and verifies the new package.

## Artwork repository workflows

Artwork lives in `deblite-artwork`.

### `ci.yml`

Runs on pushes to `main` and pull requests: `shellcheck`, a test archive build
and a contents check.

### `release.yml`

Runs when a tag matching `artwork-v*` is pushed:

1. Rejects the tag unless it matches `VERSION`.
2. Builds `deblite-artwork-<version>.tar.gz`.
3. Publishes a GitHub Release with the tarball and `SHA256SUMS`.

To ship new wallpapers:

```sh
cd deblite-artwork
# add images, bump VERSION, commit
git tag artwork-v0.2.0
git push origin main artwork-v0.2.0
```

Then update `DEBLITE_ARTWORK_VERSION` in `artwork-release.env` here and commit.

## Release assets

Each ISO release contains:

```
deblite-13-kde-amd64.iso
deblite-13-kde-amd64.iso.sha256
deblite-13-kde-amd64.iso.manifest.json
deblite-13-gnome-amd64.iso
...
```

Each installer release contains:

```
deblite-installer_<version>_amd64.deb
SHA256SUMS
```

Each artwork release contains:

```
deblite-artwork-<version>.tar.gz
SHA256SUMS
```

GitHub's hard limit is **2 GiB per asset**. `build-iso.sh --release` checks
the measured size and exits non-zero before upload if it is at or above the
limit. If that happens, the options are:

1. Split the ISO into `<2 GiB` parts and ship a `join-iso.sh`.
2. Upload to external storage (S3/R2/your server) and link from the release.

Both require a workflow change; the guard is there to make the failure
obvious and early.

## Required permissions

- ISO repo: `contents: write` for the release job and the point-release tag.
- ISO repo: `actions: write` if the watcher uses `gh workflow run`.
- Installer repo: `contents: write` for `release.yml`.
- Artwork repo: `contents: write` for `release.yml`.
- `GITHUB_TOKEN` is sufficient; no extra secrets are needed.

## Local reproduction

```sh
make check
sudo ./scripts/build-iso.sh kde --release
```

The ISO scripts are the same ones CI uses, so a local green build is a good
predictor of a green workflow. Installer work uses its own repository:

```sh
cd ../deblite-installer
make test
make deb
```

Artwork work uses its own repository too:

```sh
cd ../deblite-artwork
make check
make dist
```
