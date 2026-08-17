#!/bin/bash
# Buduje samodzielna aplikacje (macOS/Linux) - dziala bez zainstalowanego Pythona.
# Uruchom z aktywnym venv:  source venv/bin/activate && bash build.sh

set -e

NAZWA="DetektorAnomalii"

echo "== czyszczenie poprzedniego builda =="
rm -rf build dist "$NAZWA.spec"

echo "== sprawdzanie pyinstallera =="
pip show pyinstaller > /dev/null 2>&1 || pip install pyinstaller

# ikona, jesli jest
IKONA=""
if [ -f "grafika/icon.icns" ]; then
    IKONA="--icon grafika/icon.icns"
    echo "== uzywam ikony grafika/icon.icns =="
elif [ -f "icon.icns" ]; then
    IKONA="--icon icon.icns"
    echo "== uzywam ikony icon.icns =="
else
    echo "== brak icon.icns - domyslna ikona (patrz make_icons.sh) =="
fi

echo "== budowanie =="
pyinstaller --noconfirm --clean --windowed --name "$NAZWA" \
  $IKONA \
  --add-data "app.py:." \
  --add-data "anomaly_d.py:." \
  --add-data "mistral_raport_generator.py:." \
  --add-data ".streamlit:.streamlit" \
  --collect-all streamlit \
  --collect-all plotly \
  --collect-all sklearn \
  --collect-all scipy \
  --collect-data pandas \
  --copy-metadata streamlit \
  --copy-metadata pandas \
  --copy-metadata numpy \
  --copy-metadata scikit-learn \
  --copy-metadata plotly \
  --copy-metadata requests \
  --copy-metadata pyarrow \
  --copy-metadata altair \
  --hidden-import streamlit.web.bootstrap \
  --hidden-import streamlit.runtime.scriptrunner.magic_funcs \
  --hidden-import sklearn.utils._typedefs \
  --hidden-import sklearn.neighbors._partition_nodes \
  desktop.py

echo
echo "== gotowe =="
if [ -d "dist/$NAZWA.app" ]; then
    echo "Aplikacja: dist/$NAZWA.app"
    du -sh "dist/$NAZWA.app"
else
    echo "Aplikacja: dist/$NAZWA/"
    du -sh "dist/$NAZWA"
fi
echo
echo "Jesli aplikacja nie startuje, zbuduj bez --windowed i uruchom z terminala,"
echo "zeby zobaczyc blad:  ./dist/$NAZWA/$NAZWA"