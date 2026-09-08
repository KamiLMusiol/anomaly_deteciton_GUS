"""
Drobne funkcje pomocnicze uzywane w wielu miejscach, ktore nie pasuja
nigdzie indziej - eksport do CSV, sprawdzanie Ollamy, probkowanie
wykresow przy duzych zbiorach.
"""

import io
import os
import subprocess
import sys

import requests
import streamlit as st


class Narzedzia:
    """Zbiorka funkcji bez wlasnego stanu - stad staticmethod wszedzie,
    tak samo jak w anomaly_d.py i mistral_raport_generator.py."""

    @staticmethod
    def to_csv_bytes(df):
        buf = io.StringIO()  # wirtualny plik tekstowy
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")  # zamienia na surowe bajty
        # TODO zapytac sie kierownika czy moze byc ten utf-8 bo windows-1250

    @staticmethod
    def get_ollama_models():
        """llmowskie guano - tutaj mamy podglad jakie modele sa dostepne lokalnie"""
        try:
            # TODO pobawic sie modelami, moze jakis excel - bawic sie tym potem
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]  # wraca po prostu wszystkie dostepne modele
        except Exception:
            return []

    @staticmethod
    def downsample(df, max_points=None):
        """Co n-ty wiersz, zeby wykres liniowy pozostal czytelny i szybki.
        Limit 0 (domyslnie) oznacza brak probkowania - rysowane sa wszystkie punkty."""
        if max_points is None:
            max_points = st.session_state.get("limit_punktow", 0)
        if not max_points or len(df) <= max_points:
            return df, 1
        step = len(df) // max_points + 1
        return df.iloc[::step], step  # ma skakac co step wiersz, przydaje sie w szczegolnosci
        # do rollbackow sredniej kroczacej itp

    @staticmethod
    def domyslny_katalog():
        """Folder, do ktorego domyslnie zapisujemy pliki. Pobrane u wiekszosci
        ludzi istnieje, wiec zaczynamy od niego."""
        pobrane = os.path.join(os.path.expanduser("~"), "Downloads")
        return pobrane if os.path.isdir(pobrane) else os.path.expanduser("~")

    @staticmethod
    def zapisz_plik(dane, nazwa, katalog):
        """Zapisuje bajty na dysk. Zwraca (czy_sie_udalo, komunikat)."""
        try:
            katalog = os.path.expanduser(katalog.strip())
            if not os.path.isdir(katalog):
                return False, f"Katalog nie istnieje: {katalog}"
            sciezka = os.path.join(katalog, nazwa)
            with open(sciezka, "wb") as f:
                f.write(dane)
            return True, sciezka
        except PermissionError:
            return False, "Brak uprawnien do zapisu w tym katalogu."
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    @staticmethod
    def wybierz_folder():
        """
        Natywne okno wyboru folderu. Zwraca (sciezka, komunikat_bledu).

        Dialog uruchamiany jest jako OSOBNY PROCES, ktory ma wlasny watek glowny.
        To omija problem, przez ktory tkinter wywolany prosto z kodu aplikacji
        zawiesza sie na macOS - tam okna systemowe musza powstawac na watku
        glownym, a ten jest zajety przez okno aplikacji.

        Uzywamy narzedzi wbudowanych w system, wiec nie ma dodatkowych zaleznosci:
        osascript na macOS, PowerShell na Windows, zenity albo kdialog na Linuksie.
        """
        try:
            if sys.platform == "darwin":
                skrypt = (
                    'tell application "System Events" to activate\n'
                    'set wybrany to choose folder with prompt "Wybierz folder do zapisu"\n'
                    'POSIX path of wybrany'
                )
                r = subprocess.run(["osascript", "-e", skrypt],
                                   capture_output=True, text=True, timeout=180)
                if r.returncode != 0:
                    # kod 1 to zwykle anulowanie przez uzytkownika, nie blad
                    return None, None if "User canceled" in r.stderr else r.stderr.strip()
                return r.stdout.strip(), None

            if sys.platform == "win32":
                ps = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "$d.Description = 'Wybierz folder do zapisu'; "
                    "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
                )
                r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                   capture_output=True, text=True, timeout=180)
                sciezka = r.stdout.strip()
                return (sciezka, None) if sciezka else (None, None)

            # Linux - zenity albo kdialog, zaleznie od tego co jest
            for polecenie in (["zenity", "--file-selection", "--directory",
                               "--title=Wybierz folder do zapisu"],
                              ["kdialog", "--getexistingdirectory", "."]):
                try:
                    r = subprocess.run(polecenie, capture_output=True, text=True, timeout=180)
                    sciezka = r.stdout.strip()
                    return (sciezka, None) if sciezka else (None, None)
                except FileNotFoundError:
                    continue
            return None, "Brak narzedzia do wyboru folderu (zainstaluj zenity albo kdialog)."

        except subprocess.TimeoutExpired:
            return None, "Okno wyboru folderu nie zostalo zamkniete w ciagu 3 minut."
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    @staticmethod
    def tryb_desktopowy():
        """Czy aplikacja dziala w oknie desktopowym (pywebview), a nie w przegladarce.
        Znacznik ustawia desktop.py przed uruchomieniem serwera."""
        return os.environ.get("DETEKTOR_DESKTOP") == "1"

    @staticmethod
    def przycisk_pobierania(etykieta, dane, nazwa_pliku, mime, key):
        """
        Zapisanie pliku - inaczej w przegladarce, inaczej w oknie desktopowym.

        st.download_button korzysta z mechanizmu pobierania PRZEGLADARKI. W oknie
        aplikacji (pywebview) osadzona przegladarka tego nie obsluguje i zamiast
        zapisac plik PRZEKIEROWUJE OKNO pod adres z danymi - aplikacja znika
        z ekranu, a zostaje surowa tresc pliku. Dlatego w trybie desktopowym ten
        przycisk jest calkowicie ukryty, a plik zapisuje bezposrednio Python.
        """
        if not Narzedzia.tryb_desktopowy():
            # przegladarka - zwykle pobieranie dziala normalnie
            st.download_button(etykieta, dane, file_name=nazwa_pliku,
                               mime=mime, key=f"{key}_dl")
            return

        # okno desktopowe - zapis bezposrednio na dysk
        st.markdown(f"**{etykieta}**")

        # okno desktopowe - jeden przycisk do wyboru folderu i zapisu
        if st.button(f"{etykieta} (wybierz folder i zapisz)", key=f"{key}_btn", type="primary"):
            sciezka, blad = Narzedzia.wybierz_folder()

            if blad:
                st.error(blad)
            elif sciezka:
                ok, info = Narzedzia.zapisz_plik(dane, nazwa_pliku, sciezka)
                if ok:
                    st.success(f"Zapisano: {info}")
                else:
                    st.error(info)

