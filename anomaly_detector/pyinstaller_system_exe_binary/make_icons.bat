@echo off
REM Tworzy ikone Windows (.ico) z pliku PNG.
REM Uzycie:  make_icons.bat  albo  make_icons.bat sciezka\do\logo.png
REM Domyslnie szuka grafika\logo.png w katalogu projektu.

setlocal
cd /d "%~dp0.."

if "%~1"=="" (set ZRODLO=grafika\logo.png) else (set ZRODLO=%~1)

if not exist "%ZRODLO%" (
    echo Nie znaleziono pliku: %ZRODLO%
    echo Wrzuc logo do grafika\logo.png albo podaj sciezke jako argument.
    pause
    exit /b 1
)

if not exist grafika mkdir grafika

echo == sprawdzanie biblioteki Pillow ==
python -c "import PIL" 2>nul || pip install pillow

echo == generuje grafika\icon.ico ==
python -c "from PIL import Image; img = Image.open(r'%ZRODLO%').convert('RGBA'); img.save(r'grafika\icon.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]); print('   gotowe: grafika\\icon.ico')"

echo.
echo Ikona gotowa. Teraz zbuduj aplikacje:  build.bat
pause