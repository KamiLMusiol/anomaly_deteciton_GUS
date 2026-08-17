#!/bin/bash
# Generuje ikony aplikacji z jednego pliku PNG.
# Uzycie:  bash make_icons.sh grafika/logo.png
#
# Tworzy:
#   grafika/icon.icns  - macOS (.app)
#   grafika/icon.ico   - Windows (.exe)
#   icon.png           - kopia dla make_app.sh

set -e

ZRODLO="${1:-grafika/logo.png}"

if [ ! -f "$ZRODLO" ]; then
    echo "Nie znaleziono pliku: $ZRODLO"
    echo "Uzycie: bash make_icons.sh sciezka/do/logo.png"
    echo "Najlepiej PNG 1024x1024 z przezroczystym tlem."
    exit 1
fi

mkdir -p grafika

# --- macOS .icns ---
if command -v iconutil > /dev/null 2>&1; then
    echo "== generuje icon.icns (macOS) =="
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
echo "== generuje icon.ico (Windows) =="
python3 - "$ZRODLO" << 'PYEOF'
import sys
try:
    from PIL import Image
except ImportError:
    print("   Pillow niezainstalowane - pomijam .ico")
    print("   pip install pillow, a potem uruchom skrypt ponownie")
    sys.exit(0)

img = Image.open(sys.argv[1]).convert("RGBA")
rozmiary = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
img.save("grafika/icon.ico", format="ICO", sizes=rozmiary)
print("   grafika/icon.ico")
PYEOF

# --- kopia dla make_app.sh (szuka icon.png w katalogu glownym) ---
cp "$ZRODLO" icon.png
echo "   icon.png (dla make_app.sh)"

echo
echo "Gotowe. Teraz zbuduj aplikacje:"
echo "   bash build.sh      # samodzielna binarka"
echo "   bash make_app.sh   # lekki bundle wskazujacy na projekt"
