# CI/CD

## Workflows

### `ci.yml`

Runs on every push and pull request:

- `ruff check installer tests`
- `pytest -q`
- `shellcheck scripts/*.sh bin/deblite-installer`
- builds `out/deblite-installer_<version>_amd64.deb`

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
2. Build the installer `.deb`.
3. `scripts/build-iso.sh <flavor> --release` (xz) or zstd for PRs.
4. `verify-iso.sh` and `audit-bloat.sh`.
5. Upload the ISO, `.sha256` and `.manifest.json` as artifacts.

The release job runs on tags or `release=true`, downloads all artifacts and
publishes one GitHub Release with all four ISOs.

### `check-debian.yml`

Daily at 05:17 UTC:

1. `scripts/check-debian-release.sh` scrapes
   `https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/` for
   `debian-13.X.0-amd64-netinst.iso`.
2. If the version differs from `debian-version.txt`, it commits the new
   version and pushes a `v13.X` tag.
3. The tag triggers `build.yml`, which publishes the release.

## Release assets

Each release contains:

```
deblite-13-kde-amd64.iso
deblite-13-kde-amd64.iso.sha256
deblite-13-kde-amd64.iso.manifest.json
deblite-13-gnome-amd64.iso
...
```

GitHub's hard limit is **2 GiB per asset**. `build-iso.sh --release` checks
the measured size and exits non-zero before upload if it is at or above the
limit. If that happens, the options are:

1. Split the ISO into `<2 GiB` parts and ship a `join-iso.sh`.
2. Upload to external storage (S3/R2/your server) and link from the release.

Both require a workflow change; the guard is there to make the failure
obvious and early.

## Required permissions

- `contents: write` for the release job and the point-release tag.
- `actions: write` if the watcher uses `gh workflow run` instead of tags.
- `GITHUB_TOKEN` is sufficient; no extra secrets are needed.

## Local reproduction

```sh
make test
make lint
make deb
sudo ./scripts/build-iso.sh kde --release
```

The same scripts are used by CI, so a local green build is a good predictor of
a green workflow.
