@echo off
REM Buduje samodzielny plik .exe (Windows) - dziala bez zainstalowanego Pythona.
REM Uruchom z aktywnym venv:  venv\Scripts\activate && build.bat

set NAZWA=DetektorAnomalii

echo == czyszczenie poprzedniego builda ==
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del %NAZWA%.spec 2>nul

echo == sprawdzanie pyinstallera ==
pip show pyinstaller >nul 2>&1 || pip install pyinstaller

set IKONA=
if exist grafika\icon.ico set IKONA=--icon grafika\icon.ico
if exist icon.ico set IKONA=--icon icon.ico

echo == budowanie ==
REM UWAGA: na Windowsie separator w --add-data to srednik, nie dwukropek
pyinstaller --noconfirm --clean --windowed --name %NAZWA% ^
  %IKONA% ^
  --add-data "app.py;." ^
  --add-data "anomaly_d.py;." ^
  --add-data "mistral_raport_generator.py;." ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit ^
  --collect-all plotly ^
  --collect-all sklearn ^
  --collect-all scipy ^
  --collect-all openpyxl ^
  --collect-data pandas ^
  --copy-metadata streamlit ^
  --copy-metadata pandas ^
  --copy-metadata numpy ^
  --copy-metadata scikit-learn ^
  --copy-metadata plotly ^
  --copy-metadata requests ^
  --copy-metadata pyarrow ^
  --copy-metadata altair ^
  --copy-metadata openpyxl ^
  --hidden-import streamlit.web.bootstrap ^
  --hidden-import streamlit.runtime.scriptrunner.magic_funcs ^
  --hidden-import sklearn.utils._typedefs ^
  --hidden-import sklearn.neighbors._partition_nodes ^
  desktop.py

echo.
echo == gotowe ==
echo Aplikacja: dist\%NAZWA%\%NAZWA%.exe
echo.
echo Jesli nie startuje, zbuduj bez --windowed i uruchom z wiersza polecen,
echo zeby zobaczyc blad.
pause