@echo off
REM Buduje samodzielny plik .exe (Windows) - dziala bez zainstalowanego Pythona.
REM
REM Skrypt lezy w podfolderze, ale PyInstaller musi widziec caly projekt,
REM dlatego najpierw przechodzi do katalogu nadrzednego.
REM Uruchamiac z aktywnym venv:  venv\Scripts\activate

setlocal

REM %~dp0 = katalog tego skryptu, %~dp0.. = katalog projektu
cd /d "%~dp0.."
echo == katalog projektu: %CD% ==

set NAZWA=DetektorAnomalii

echo == czyszczenie poprzedniego builda ==
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del %NAZWA%.spec 2>nul

echo == sprawdzanie pyinstallera ==
pip show pyinstaller >nul 2>&1 || pip install pyinstaller

set IKONA=
if exist grafika\icon.ico set IKONA=--icon grafika\icon.ico

echo == budowanie (jeden plik .exe) ==
REM UWAGA: na Windowsie separator w --add-data to SREDNIK, nie dwukropek.
REM Cale foldery zamiast pojedynczych plikow - Streamlit wykonuje app.py jako
REM skrypt, wiec PyInstaller sam nie widzi frontend_streamlit ani backend_ml_llm.
pyinstaller --noconfirm --clean --onefile --windowed --name %NAZWA% ^
  %IKONA% ^
  --add-data "app.py;." ^
  --add-data "frontend_streamlit;frontend_streamlit" ^
  --add-data "backend_ml_llm;backend_ml_llm" ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit ^
  --collect-all plotly ^
  --collect-all sklearn ^
  --collect-all scipy ^
  --collect-all openpyxl ^
  --collect-all duckdb ^
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
  --copy-metadata duckdb ^
  --hidden-import streamlit.web.bootstrap ^
  --hidden-import streamlit.runtime.scriptrunner.magic_funcs ^
  --hidden-import sklearn.utils._typedefs ^
  --hidden-import sklearn.neighbors._partition_nodes ^
  backend_ml_llm\desktop.py

echo.
echo == gotowe ==
echo Aplikacja: dist\%NAZWA%.exe
echo (jeden plik - mozna go kopiowac bez dodatkowych folderow)
pause