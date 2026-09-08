#!/bin/bash
# Buduje LEKKI pakiet .app dla macOS (kilka KB) - tylko skrot uruchamiajacy
# projekt z jego obecnej lokalizacji. NIE jest przenosny na inny komputer,
# do tego sluzy build.sh.
#
# Uzycie:  bash pyinstaller_system_exe_binary/make_app.sh

set -e

KATALOG_SKRYPTU="$(cd "$(dirname "$0")" && pwd)"
KATALOG_PROJEKTU="$(dirname "$KATALOG_SKRYPTU")"
cd "$KATALOG_PROJEKTU"

APP_NAME="Detektor Anomalii"
BUNDLE="$APP_NAME.app"
PYTHON_BIN="$(which python3)"

echo "Katalog projektu: $KATALOG_PROJEKTU"
echo "Python:           $PYTHON_BIN"

rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"

cat > "$BUNDLE/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleDisplayName</key><string>$APP_NAME</string>
    <key>CFBundleIdentifier</key><string>pl.gus.detektoranomalii</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>CFBundleIconFile</key><string>icon</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
PLIST

cat > "$BUNDLE/Contents/MacOS/launcher" << LAUNCHER
#!/bin/bash
cd "$KATALOG_PROJEKTU"
exec "$PYTHON_BIN" backend_ml_llm/desktop.py
LAUNCHER
chmod +x "$BUNDLE/Contents/MacOS/launcher"

if [ -f "grafika/icon.icns" ]; then
    cp "grafika/icon.icns" "$BUNDLE/Contents/Resources/icon.icns"
    echo "Ikona dodana z grafika/icon.icns"
else
    echo "Brak grafika/icon.icns - domyslna ikona (uruchom najpierw make_icons.sh)"
fi

echo
echo "Gotowe: $BUNDLE"
echo "Uruchom dwuklikiem albo przenies do /Applications"