#!/bin/bash
# Buduje DetektorAnomalii.app - natywny bundle macOS uruchamiany dwuklikiem.
# Uruchom raz, z katalogu projektu:  bash make_app.sh

set -e

APP_NAME="Detektor Anomalii"
BUNDLE="$APP_NAME.app"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$(which python3)"

echo "Katalog projektu: $PROJECT_DIR"
echo "Python:           $PYTHON_BIN"

# --- struktura bundla ---
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS"
mkdir -p "$BUNDLE/Contents/Resources"

# --- Info.plist ---
cat > "$BUNDLE/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>pl.gus.detektoranomalii</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
</dict>
</plist>
PLIST

# --- launcher ---
cat > "$BUNDLE/Contents/MacOS/launcher" << LAUNCHER
#!/bin/bash
cd "$PROJECT_DIR"
exec "$PYTHON_BIN" desktop.py
LAUNCHER

chmod +x "$BUNDLE/Contents/MacOS/launcher"

# --- ikona (opcjonalna) ---
for KANDYDAT in "grafika/icon.png" "icon.png" "grafika/logo.png"; do
    if [ -f "$KANDYDAT" ]; then ZRODLO_IKONY="$KANDYDAT"; break; fi
done

if [ -n "$ZRODLO_IKONY" ]; then
    echo "Generuje ikone z $ZRODLO_IKONY..."
    ICONSET="icon.iconset"
    rm -rf "$ICONSET"
    mkdir "$ICONSET"
    for SIZE in 16 32 128 256 512; do
        sips -z $SIZE $SIZE "$ZRODLO_IKONY" --out "$ICONSET/icon_${SIZE}x${SIZE}.png" > /dev/null 2>&1
        DOUBLE=$((SIZE * 2))
        sips -z $DOUBLE $DOUBLE "$ZRODLO_IKONY" --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" > /dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "$BUNDLE/Contents/Resources/icon.icns"
    rm -rf "$ICONSET"
    echo "Ikona dodana."
else
    echo "Brak ikony (szukano grafika/icon.png, icon.png, grafika/logo.png)."
fi

echo ""
echo "Gotowe: $BUNDLE"
echo ""
echo "Przetestuj dwuklikiem, a potem przenies do /Applications:"
echo "  mv \"$BUNDLE\" /Applications/"
