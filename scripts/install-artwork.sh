#!/usr/bin/env bash
# Install optional DebLite artwork into a live-build configuration tree.
#
# Wallpapers are not committed to this repository. Drop images into
# ../deblite-artwork/wallpapers (or set DEBLITE_ARTWORK_DIR) before building
# and this script copies them into the image and makes one of them the default
# for KDE Plasma, GNOME, XFCE or Cinnamon. Without artwork every edition keeps
# its built-in wallpaper.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTWORK_DIR=${DEBLITE_ARTWORK_DIR:-$ROOT/../deblite-artwork/wallpapers}
WALLPAPER=${DEBLITE_WALLPAPER:-}
FLAVOR=""
CONFIG=""

usage() {
    cat <<EOF
usage: $0 --flavor FLAVOR --config DIR

Copies wallpapers from \$DEBLITE_ARTWORK_DIR
(default: $ROOT/../deblite-artwork/wallpapers) into the live-build
configuration at DIR and selects a default wallpaper for the edition.

Environment:
  DEBLITE_ARTWORK_DIR   wallpaper directory
  DEBLITE_WALLPAPER     file name (or absolute path) to use as the default;
                        defaults to the first image in sort order
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --flavor)
            FLAVOR=$2
            shift 2
            ;;
        --config)
            CONFIG=$2
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$FLAVOR" ] || [ -z "$CONFIG" ]; then
    usage >&2
    exit 2
fi
if [ ! -d "$CONFIG" ]; then
    echo "error: configuration directory not found: $CONFIG" >&2
    exit 2
fi

case "$FLAVOR" in
    kde|gnome|gnome-backports|xfce|cinnamon) ;;
    *)
        echo "error: unsupported flavor for artwork: $FLAVOR" >&2
        exit 2
        ;;
esac

if [ ! -d "$ARTWORK_DIR" ]; then
    echo "artwork: $ARTWORK_DIR not found; keeping the default wallpaper" >&2
    exit 0
fi

images=()
while IFS= read -r image; do
    images+=("$image")
done < <(
    find "$ARTWORK_DIR" -maxdepth 1 -type f \
        \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \
           -o -iname '*.webp' -o -iname '*.svg' \) |
        LC_ALL=C sort
)

if [ "${#images[@]}" -eq 0 ]; then
    echo "artwork: no images in $ARTWORK_DIR; keeping the default wallpaper" >&2
    exit 0
fi

if [ -n "$WALLPAPER" ]; then
    case "$WALLPAPER" in
        /*)
            chosen=$WALLPAPER
            ;;
        *)
            chosen=$ARTWORK_DIR/$WALLPAPER
            ;;
    esac
    if [ ! -f "$chosen" ]; then
        echo "error: DEBLITE_WALLPAPER not found: $WALLPAPER" >&2
        exit 2
    fi
else
    chosen=${images[0]}
fi

name=$(basename "$chosen")
case "${name,,}" in
    *.jpg|*.jpeg|*.png|*.webp|*.svg) ;;
    *)
        echo "error: unsupported wallpaper type: $name" >&2
        exit 2
        ;;
esac
case "$name" in
    *\'*|*\"*|*\\*|*\#*|*%*|*\?*|*\|*|*\&*|*\<*|*\>*|*[[:cntrl:]]*)
        echo "error: wallpaper name contains an unsupported character: $name" >&2
        exit 2
        ;;
esac

dest="$CONFIG/includes.chroot/usr/share/backgrounds/deblite"
install -d -m 0755 "$dest"

for image in "${images[@]}"; do
    install -m 0644 "$image" "$dest/$(basename "$image")"
done
# Copy the selected file last so an absolute DEBLITE_WALLPAPER outside the
# artwork directory wins even when its basename collides with another image.
install -m 0644 "$chosen" "$dest/$name"

target="/usr/share/backgrounds/deblite/$name"
uri="file://$target"
uri=${uri// /%20}

echo "artwork: installed $(du -sh "$dest" | cut -f1) from $ARTWORK_DIR"
echo "artwork: default wallpaper $name"

# The chroot hook uses this to configure components whose packaged files
# cannot be overridden from includes.chroot.
install -d -m 0755 "$CONFIG/includes.chroot/etc"
printf '%s\n' "$target" >"$CONFIG/includes.chroot/etc/deblite-wallpaper"

write_dconf() {
    local dconf_dir="$CONFIG/includes.chroot/etc/dconf/db/local.d"
    local profile="$CONFIG/includes.chroot/etc/dconf/profile/user"
    install -d -m 0755 "$dconf_dir"
    install -d -m 0755 "$(dirname "$profile")"
    if [ ! -f "$profile" ]; then
        printf 'user-db:user\nsystem-db:local\n' >"$profile"
    fi

    {
        if [ "$FLAVOR" = "cinnamon" ]; then
            cat <<EOF
[org/cinnamon/desktop/background]
picture-uri='$uri'
picture-options='zoom'

EOF
        fi
        cat <<EOF
[org/gnome/desktop/background]
picture-uri='$uri'
picture-options='zoom'
picture-uri-dark='$uri'
EOF
    } >"$dconf_dir/10-deblite-wallpaper"
}

write_xfce() {
    local dir="$CONFIG/includes.chroot/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
    local helper="$CONFIG/includes.chroot/usr/libexec/deblite-wallpaper-xfce"
    local autostart="$CONFIG/includes.chroot/etc/xdg/autostart/50-deblite-wallpaper.desktop"
    local monitor
    install -d -m 0755 "$dir" "$(dirname "$helper")" "$(dirname "$autostart")"
    {
        cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
EOF
        for monitor in 0 1 2 3; do
            cat <<EOF
      <property name="monitor$monitor" type="empty">
        <property name="image-path" type="string" value="$target"/>
        <property name="last-image" type="string" value="$target"/>
        <property name="last-single-image" type="string" value="$target"/>
        <property name="image-style" type="int" value="5"/>
        <property name="image-show" type="bool" value="true"/>
      </property>
EOF
        done
        cat <<EOF
    </property>
  </property>
</channel>
EOF
    } >"$dir/xfce4-desktop.xml"

    # Xfconf defaults only cover the monitor names we can predict. On the
    # first login, rewrite every last-image property xfdesktop actually
    # created, plus the monitors xrandr reports, then leave the user's choice
    # alone.
    cat >"$helper" <<EOF
#!/bin/sh
set -eu
marker="\${XDG_CONFIG_HOME:-\$HOME/.config}/deblite/wallpaper-applied"
[ -e "\$marker" ] && exit 0
command -v xfconf-query >/dev/null 2>&1 || exit 0

set_wallpaper() {
    base=\$1
    xfconf-query -c xfce4-desktop -p "\$base/last-image" -n -t string -s '$target' >/dev/null 2>&1 || true
    xfconf-query -c xfce4-desktop -p "\$base/image-style" -n -t int -s 5 >/dev/null 2>&1 || true
    xfconf-query -c xfce4-desktop -p "\$base/image-show" -n -t bool -s true >/dev/null 2>&1 || true
}

props=\$(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep '/last-image\$' || true)
for prop in \$props; do
    set_wallpaper "\${prop%/last-image}"
done

monitors=""
if command -v xrandr >/dev/null 2>&1; then
    monitors=\$(xrandr --listmonitors 2>/dev/null | awk 'NR > 1 {print \$NF}' || true)
fi
for monitor in \$monitors; do
    set_wallpaper "/backdrop/screen0/monitor\$monitor"
    set_wallpaper "/backdrop/screen0/monitor\$monitor/workspace0"
done
if [ -z "\$props" ] && [ -z "\$monitors" ]; then
    set_wallpaper /backdrop/screen0/monitor0
    set_wallpaper /backdrop/screen0/monitor0/workspace0
fi

command -v xfdesktop >/dev/null 2>&1 && xfdesktop --reload >/dev/null 2>&1 || true
mkdir -p "\$(dirname "\$marker")"
: >"\$marker"
EOF
    chmod 0755 "$helper"

    cat >"$autostart" <<EOF
[Desktop Entry]
Type=Application
Name=DebLite Wallpaper
Comment=Apply the DebLite wallpaper on first login
Exec=/usr/libexec/deblite-wallpaper-xfce
OnlyShowIn=XFCE;
NoDisplay=true
EOF
}

write_xfce_greeter() {
    local greeter="$CONFIG/includes.chroot/etc/lightdm/lightdm-gtk-greeter.conf"
    install -d -m 0755 "$(dirname "$greeter")"
    if [ ! -f "$greeter" ]; then
        printf '[greeter]\n' >"$greeter"
    fi
    if grep -q '^background=' "$greeter"; then
        sed -i "s|^background=.*|background=$target|" "$greeter"
    elif grep -q '^\[greeter\]$' "$greeter"; then
        sed -i "/^\[greeter\]$/a background=$target" "$greeter"
    else
        printf '\n[greeter]\nbackground=%s\n' "$target" >>"$greeter"
    fi
}

write_kde() {
    local helper="$CONFIG/includes.chroot/usr/libexec/deblite-wallpaper"
    local autostart="$CONFIG/includes.chroot/etc/xdg/autostart/50-deblite-wallpaper.desktop"
    install -d -m 0755 "$(dirname "$helper")" "$(dirname "$autostart")"

    cat >"$helper" <<EOF
#!/bin/sh
# Apply the DebLite wallpaper on the first login, then leave the user's
# choice alone.
set -eu
marker="\${XDG_CONFIG_HOME:-\$HOME/.config}/deblite/wallpaper-applied"
[ -e "\$marker" ] && exit 0
command -v plasma-apply-wallpaperimage >/dev/null 2>&1 || exit 0
plasma-apply-wallpaperimage '$target' || exit 0
mkdir -p "\$(dirname "\$marker")"
: >"\$marker"
EOF
    chmod 0755 "$helper"

    cat >"$autostart" <<EOF
[Desktop Entry]
Type=Application
Name=DebLite Wallpaper
Comment=Apply the DebLite wallpaper on first login
Exec=/usr/libexec/deblite-wallpaper
OnlyShowIn=KDE;
NoDisplay=true
X-KDE-autostart-after=panel
EOF
}

case "$FLAVOR" in
    cinnamon)
        write_dconf
        greeter="$CONFIG/includes.chroot/etc/lightdm/slick-greeter.conf"
        if [ -f "$greeter" ]; then
            if grep -q '^background=' "$greeter"; then
                sed -i "s|^background=.*|background=$target|" "$greeter"
            else
                sed -i "/^\[Greeter\]/a background=$target" "$greeter"
            fi
        else
            echo "artwork: no Slick Greeter configuration; greeter background unchanged" >&2
        fi
        ;;
    gnome|gnome-backports)
        write_dconf
        ;;
    xfce)
        write_xfce
        write_xfce_greeter
        ;;
    kde)
        write_kde
        ;;
esac
