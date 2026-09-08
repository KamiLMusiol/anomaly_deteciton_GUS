# pyinstaller_system_exe_binary

Skrypty budujace samodzielna wersje aplikacji - taka, ktora dziala bez
zainstalowanego Pythona.

**Wszystkie skrypty same przechodza do katalogu projektu**, wiec mozna je
uruchamiac z dowolnego miejsca:

```bash
bash pyinstaller_system_exe_binary/build.sh
```

## Pliki

| Plik | System | Co robi |
|---|---|---|
| `build.sh` | macOS, Linux | jeden plik binarny w `dist/DetektorAnomalii` |
| `build.bat` | Windows | jeden plik `dist\DetektorAnomalii.exe` |
| `make_icons.sh` | macOS, Linux | generuje `.icns` i `.ico` z `grafika/logo.png` |
| `make_icons.bat` | Windows | generuje `.ico` |
| `make_app.sh` | macOS | lekki pakiet `.app` (kilka KB), tylko na ten komputer |

## Kolejnosc

```bash
source venv/bin/activate                              # zawsze z aktywnym venv
bash pyinstaller_system_exe_binary/make_icons.sh      # raz, albo po zmianie logo
bash pyinstaller_system_exe_binary/build.sh           # przy kazdej zmianie kodu
```

## build.sh vs make_app.sh

| | `make_app.sh` | `build.sh` |
|---|---|---|
| Rozmiar | kilka KB | okolo 240 MB |
| Czas | sekunda | 2-5 minut |
| Wymaga Pythona u odbiorcy | tak | nie |
| Przenosny na inny komputer | nie | tak |
| Do czego | wlasny komputer, prezentacja | oddanie komus |

`make_app.sh` tworzy tylko skrot wskazujacy na projekt w jego obecnej
lokalizacji - przeniesienie folderu projektu psuje go i trzeba zbudowac na nowo.

## Dlaczego tyle flag w build.sh

Streamlit nie daje sie spakowac przy domyslnych ustawieniach:

| Flaga | Po co |
|---|---|
| `--onefile` | wszystko w jednym pliku, bez folderu `_internal` obok |
| `--add-data "frontend_streamlit:frontend_streamlit"` | **kluczowe** - Streamlit *wykonuje* `app.py` jako skrypt, a nie importuje, wiec PyInstaller sam nie widzi tych folderow jako zaleznosci |
| `--collect-all streamlit` | pliki interfejsu JS/CSS, bez nich biala pusta strona |
| `--collect-all plotly, sklearn, scipy, openpyxl, duckdb` | moduly ladowane dynamicznie |
| `--copy-metadata (10 pakietow)` | Streamlit sprawdza wersje przez `importlib.metadata`, brak = blad przy starcie |
| `--hidden-import` | moduly importowane przez nazwe w postaci tekstu |

## Roznice miedzy systemami

- W `--add-data` Windows uzywa **srednika**, reszta **dwukropka**. `build.bat`
  juz to uwzglednia.
- PyInstaller **nie buduje miedzyplatformowo** - `.exe` musi powstac na Windowsie,
  binarka macOS na Macu.

## Typowe problemy

**Biala pusta strona** - brakuje `--collect-all streamlit`.

**`ModuleNotFoundError: No module named 'frontend_streamlit'`** - brakuje
`--add-data` dla tego folderu.

**`PackageNotFoundError`** - dopisz pakiet do `--copy-metadata`.

**Ostrzezenia o `torch`** - nieszkodliwe, sklearn i scipy szukaja opcjonalnego
backendu, ktorego projekt nie uzywa.

**macOS blokuje aplikacje** - prawy przycisk > Otworz > Otworz, tylko raz.

## Ollama nie jest pakowana

Binarka zawiera aplikacje i biblioteki Pythona, ale **nie Ollame ani modelu**
(4-7 GB). Odbiorca musi zainstalowac ja osobno, jesli chce korzystac z zakladek
Raport i Pytanie. Reszta dziala bez niej.