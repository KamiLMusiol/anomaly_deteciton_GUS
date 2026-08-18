#!/bin/bash
# Skrypt do generowania ikony .ico dla Windows z pliku PNG.
# Użycie: bash make_icons_win.sh grafika/logo.png

set -e

ZRODLO="${1:-grafika/logo.png}"

if [ ! -f "$ZRODLO" ]; then
    echo "Nie znaleziono pliku źródłowego: $ZRODLO"
    exit 1
fi

echo "== Generowanie icon.ico dla Windows z $ZRODLO =="

python3 - "$ZRODLO" << 'PYEOF'
import sys
try:
    from PIL import Image
except ImportError:
    print("Błąd: Biblioteka Pillow nie jest zainstalowana.")
    print("Zainstaluj ją poleceniem: pip install pillow")
    sys.exit(1)

img = Image.open(sys.argv[1]).convert("RGBA")
# Standardowe rozmiary dla ikony Windows
rozmiary = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
img.save("icon.ico", format="ICO", sizes=rozmiary)
print("Sukces: Utworzono plik 'icon.ico' w katalogu głównym.")
PYEOF
