#!/bin/bash
# Generuje ikony aplikacji z jednego pliku PNG.
#
# Uzycie (z dowolnego miejsca):
#    bash pyinstaller_system_exe_binary/make_icons.sh
#    bash pyinstaller_system_exe_binary/make_icons.sh sciezka/do/logo.png
#
# Domyslnie szuka grafika/logo.png w katalogu projektu.
# Tworzy: grafika/icon.icns (macOS) oraz grafika/icon.ico (Windows)

set -e

KATALOG_SKRYPTU="$(cd "$(dirname "$0")" && pwd)"
KATALOG_PROJEKTU="$(dirname "$KATALOG_SKRYPTU")"
cd "$KATALOG_PROJEKTU"

ZRODLO="${1:-grafika/logo.png}"

if [ ! -f "$ZRODLO" ]; then
    echo "Nie znaleziono pliku: $ZRODLO"
    echo "Wrzuc logo do grafika/logo.png albo podaj sciezke jako argument."
    echo "Najlepiej PNG 1024x1024 z przezroczystym tlem."
    exit 1
fi

mkdir -p grafika

# --- macOS .icns ---
if command -v iconutil > /dev/null 2>&1; then
    echo "== generuje grafika/icon.icns (macOS) =="
    ICONSET="icon.iconset"
    rm -rf "$ICONSET"; mkdir "$ICONSET"
    for R in 16 32 128 256 512; do
        sips -z $R $R "$ZRODLO" --out "$ICONSET/icon_${R}x${R}.png" > /dev/null 2>&1
        D=$((R*2))
        sips -z $D $D "$ZRODLO" --out "$ICONSET/icon_${R}x${R}@2x.png" > /dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "grafika/icon.icns"
    rm -rf "$ICONSET"
    echo "   grafika/icon.icns"
else
    echo "== pomijam .icns (iconutil dostepny tylko na macOS) =="
fi

# --- Windows .ico ---
echo "== generuje grafika/icon.ico (Windows) =="
python3 - "$ZRODLO" << 'PYEOF'
import sys
try:
    from PIL import Image
except ImportError:
    print("   Pillow niezainstalowane - pomijam .ico  (pip install pillow)")
    sys.exit(0)
img = Image.open(sys.argv[1]).convert("RGBA")
img.save("grafika/icon.ico", format="ICO",
         sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("   grafika/icon.ico")
PYEOF

echo
echo "Gotowe. Teraz zbuduj aplikacje:"
echo "   bash pyinstaller_system_exe_binary/build.sh"