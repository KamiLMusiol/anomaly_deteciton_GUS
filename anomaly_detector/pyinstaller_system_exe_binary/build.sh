#!/bin/bash
# Buduje samodzielny plik binarny (macOS/Linux) - dziala bez zainstalowanego Pythona.
#
# Skrypt lezy w podfolderze, ale PyInstaller musi widziec caly projekt,
# dlatego pierwsza rzecza jaka robi jest przejscie do katalogu nadrzednego.
# Dzieki temu mozna go uruchomic z dowolnego miejsca:
#     bash pyinstaller_system_exe_binary/build.sh
# albo
#     cd pyinstaller_system_exe_binary && bash build.sh

set -e

# katalog projektu = jeden poziom wyzej niz ten skrypt
KATALOG_SKRYPTU="$(cd "$(dirname "$0")" && pwd)"
KATALOG_PROJEKTU="$(dirname "$KATALOG_SKRYPTU")"
cd "$KATALOG_PROJEKTU"
echo "== katalog projektu: $KATALOG_PROJEKTU =="

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
else
    echo "== brak grafika/icon.icns - domyslna ikona (patrz make_icons.sh) =="
fi

echo "== budowanie (jeden plik binarny) =="
# Cale foldery jako --add-data zamiast wypisywania kazdego pliku z osobna.
# Streamlit wykonuje app.py jako skrypt (nie importuje go), wiec PyInstaller
# sam z siebie NIE widzi frontend_streamlit ani backend_ml_llm jako zaleznosci.
pyinstaller --noconfirm --clean --onefile --name "$NAZWA" \
  $IKONA \
  --add-data "app.py:." \
  --add-data "frontend_streamlit:frontend_streamlit" \
  --add-data "backend_ml_llm:backend_ml_llm" \
  --add-data ".streamlit:.streamlit" \
  --collect-all streamlit \
  --collect-all plotly \
  --collect-all sklearn \
  --collect-all scipy \
  --collect-all openpyxl \
  --collect-all duckdb \
  --collect-data pandas \
  --copy-metadata streamlit \
  --copy-metadata pandas \
  --copy-metadata numpy \
  --copy-metadata scikit-learn \
  --copy-metadata plotly \
  --copy-metadata requests \
  --copy-metadata pyarrow \
  --copy-metadata altair \
  --copy-metadata openpyxl \
  --copy-metadata duckdb \
  --hidden-import streamlit.web.bootstrap \
  --hidden-import streamlit.runtime.scriptrunner.magic_funcs \
  --hidden-import sklearn.utils._typedefs \
  --hidden-import sklearn.neighbors._partition_nodes \
  backend_ml_llm/desktop.py

echo
echo "== gotowe =="
echo "Plik binarny: dist/$NAZWA"
du -sh "dist/$NAZWA"
echo
echo "Uruchomienie:  ./dist/$NAZWA"
echo
echo "To jeden samodzielny plik - mozna go kopiowac/przenosic bez zadnych"
echo "dodatkowych folderow obok. Pierwsze uruchomienie po zbudowaniu bywa"
echo "wolniejsze (plik rozpakowuje sam siebie do katalogu tymczasowego)."