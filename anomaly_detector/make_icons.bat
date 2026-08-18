@echo off
REM ============================================================
REM Tworzy ikone Windows (.ico) z pliku PNG.
REM
REM Uzycie:
REM    make_icons.bat                     - szuka grafika\logo.png
REM    make_icons.bat sciezka\do\logo.png - konkretny plik
REM
REM Najlepiej PNG 1024x1024 z przezroczystym tlem.
REM Wynik: grafika\icon.ico (rozmiary od 16 do 256 px)
REM ============================================================

setlocal

if "%~1"=="" (
    set ZRODLO=grafika\logo.png
) else (
    set ZRODLO=%~1
)

if not exist "%ZRODLO%" (
    echo.
    echo Nie znaleziono pliku: %ZRODLO%
    echo.
    echo Wrzuc logo do grafika\logo.png albo podaj sciezke:
    echo    make_icons.bat sciezka\do\logo.png
    echo.
    pause
    exit /b 1
)

if not exist grafika mkdir grafika

echo == sprawdzanie biblioteki Pillow ==
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Instaluje Pillow...
    pip install pillow
    if errorlevel 1 (
        echo.
        echo Nie udalo sie zainstalowac Pillow.
        echo Sprawdz czy venv jest aktywny: venv\Scripts\activate
        pause
        exit /b 1
    )
)

echo == generuje grafika\icon.ico ==
python -c "from PIL import Image; img = Image.open(r'%ZRODLO%').convert('RGBA'); img.save(r'grafika\icon.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]); print('   gotowe: grafika\\icon.ico')"

if errorlevel 1 (
    echo.
    echo Blad podczas generowania ikony.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Ikona gotowa. Teraz zbuduj aplikacje:
echo    build.bat
echo.
echo build.bat sam znajdzie grafika\icon.ico i doklei ja do .exe
echo ============================================================
echo.
pause