#!/bin/sh
# Build helper for the EssoraFM internal picom binary.
# Author: josejp2424
# Usage:
#   ./build-essorafm-picom.sh /path/to/picom-source

set -eu

SRC="${1:-}"
if [ -z "$SRC" ]; then
    echo "Uso: $0 /ruta/al/source/picom" >&2
    exit 1
fi

SRC="$(readlink -f "$SRC")"
if [ ! -f "$SRC/meson.build" ]; then
    echo "No parece ser el source de picom: $SRC" >&2
    exit 1
fi

if ! command -v meson >/dev/null 2>&1; then
    echo "Falta meson. En Devuan/Debian instala: meson ninja-build pkg-config gcc libev-dev libconfig-dev libx11-xcb-dev libxcb1-dev libxcb-composite0-dev libxcb-damage0-dev libxcb-glx0-dev libxcb-present-dev libxcb-randr0-dev libxcb-render0-dev libxcb-shape0-dev libxcb-sync-dev libxcb-xfixes0-dev libxcb-image0-dev libxcb-render-util0-dev libxcb-util-dev libpixman-1-dev libpcre2-dev libepoxy-dev uthash-dev" >&2
    exit 1
fi
if ! command -v ninja >/dev/null 2>&1; then
    echo "Falta ninja. En Devuan/Debian instala: ninja-build" >&2
    exit 1
fi

BUILD="$SRC/build-essorafm"
DEST="$SRC/pkg-essorafm"
rm -rf "$BUILD" "$DEST"

meson setup "$BUILD" "$SRC" \
    --prefix=/usr/local/essorafm \
    --bindir=bin \
    --buildtype=release \
    -Dwith_docs=false \
    -Dcompton=false \
    -Ddbus=false \
    -Dopengl=true

ninja -C "$BUILD"
DESTDIR="$DEST" ninja -C "$BUILD" install

mkdir -p /usr/local/essorafm/bin /usr/local/essorafm/licenses/picom

if [ -f "$DEST/usr/local/essorafm/bin/picom" ]; then
    install -m 0755 "$DEST/usr/local/essorafm/bin/picom" /usr/local/essorafm/bin/essorafm-picom
else
    echo "No se encontró el binario picom compilado." >&2
    exit 1
fi

# No queremos autostart ni desktop externos de picom: EssoraFM lo controla.
rm -f /usr/local/essorafm/bin/picom 2>/dev/null || true
rm -f /usr/local/essorafm/bin/compton 2>/dev/null || true

[ -f "$SRC/COPYING" ] && cp -a "$SRC/COPYING" /usr/local/essorafm/licenses/picom/
[ -f "$SRC/LICENSE.spdx" ] && cp -a "$SRC/LICENSE.spdx" /usr/local/essorafm/licenses/picom/
[ -d "$SRC/LICENSES" ] && cp -a "$SRC/LICENSES" /usr/local/essorafm/licenses/picom/

echo "Listo: /usr/local/essorafm/bin/essorafm-picom"
