# Detektor anomalii

Aplikacja desktopowa do wykrywania anomalii w plikach CSV i Excel. Laczy trzy
modele uczenia maszynowego glosujace nad kazdym wierszem z warstwa przygotowania
danych (tabele przestawne, SQL, laczenie tabel) i lokalnym modelem jezykowym,
ktory opisuje wyniki po polsku.

Wszystko dziala offline - zadne dane nie opuszczaja komputera.

---

## Struktura projektu

```
anomaly_detector/
├── app.py                        # punkt wejscia, spina reszte (70 linii)
├── requirements.txt
├── test.ipynb                    # notatnik do testow poza aplikacja
├── Readme.md
│
├── .streamlit/
│   └── config.toml               # jasny motyw, ukryty przycisk Deploy
│
├── backend_ml_llm/               # warstwa obliczeniowa (bez Streamlita)
│   ├── anomaly_d.py              # cechy, trzy modele ML, glosowanie
│   ├── mistral_raport_generator.py  # raport i pytania przez Ollama
│   └── desktop.py                # launcher w natywnym oknie
│
├── frontend_streamlit/           # warstwa interfejsu
│   ├── styles.py                 # kolory, CSS
│   ├── pola.py                   # pola liczbowe, zakresy osi
│   ├── narzedzia.py              # CSV, Ollama, probkowanie
│   ├── wykresy.py                # wykresy Plotly
│   ├── magazyn_danych.py         # zbiory w pamieci sesji
│   ├── panel_boczny.py           # wgrywanie plikow
│   └── zakladka_*.py             # siedem zakladek
│
├── data/                         # pliki testowe
├── grafika/                      # logo i ikony
└── pyinstaller_system_exe_binary/  # skrypty budujace
```

Kazdy folder ma wlasny `Readme.md` z opisem zawartosci.

---

## Instalacja

```bash
cd anomaly_detector
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Wszystkie kolejne polecenia wykonuj z aktywnym venv** - inaczej pakiety trafia
do Pythona systemowego, a aplikacja ich nie znajdzie.

### Ollama (opcjonalnie)

Potrzebna tylko dla zakladek Raport i Pytanie:

```bash
brew install ollama       # macOS
ollama serve
ollama pull qwen3:8b
```

Bez niej reszta aplikacji dziala normalnie, te dwie zakladki pokaza ostrzezenie.

---

## Uruchamianie

```bash
streamlit run app.py                    # w przegladarce, do pracy nad kodem
python backend_ml_llm/desktop.py        # natywne okno bez przegladarki
```

**Uruchamiac z katalogu projektu**, nie z podfolderu - `app.py` i `.streamlit/`
musza byc widoczne w katalogu roboczym.

---

## Budowanie wersji samodzielnej

```bash
source venv/bin/activate
bash pyinstaller_system_exe_binary/make_icons.sh    # raz, albo po zmianie logo
bash pyinstaller_system_exe_binary/build.sh
```

Wynik: `dist/DetektorAnomalii` - jeden plik, dziala bez Pythona, mozna przeniesc
na inny komputer.

Na Windowsie odpowiednio `make_icons.bat` i `build.bat`, wynik `dist\DetektorAnomalii.exe`.

Szczegoly w `pyinstaller_system_exe_binary/Readme.md`.

---

## Jak to dziala

### Przeplyw danych

```
pliki CSV / XLSX  (mozna wiele naraz)
     |
     v  wczytanie                     panel_boczny.py
     |
     +--> przygotowanie danych        zakladka_dane.py
     |      porownanie zbiorow
     |      laczenie (union / join)
     |      tabela przestawna
     |      zapytanie SQL (duckdb)
     |         kazdy wynik = nowy zbior, mozna analizowac dalej
     |
     v  wybor kolumn i trybu          zakladka_detekcja.py
     |
     v  cechy pochodne                anomaly_d.py
     |     z-score, srednie kroczace, roznice, flagi IQR
     |
     v  standaryzacja + trzy modele   anomaly_d.py -> run_models
     |     IF + LOF + SVM,  prog >=2 z 3
     |
     v  wykresy i tabela wynikow      zakladka_anomalie.py
     |
     v  fakty liczone w Pythonie      mistral_raport_generator.py
     |
     v  model jezykowy formatuje      Ollama, localhost:11434
     |
     v  raport TXT / odpowiedz
```

### Trzy modele

| Model | Zasada | Wychwytuje |
|---|---|---|
| Isolation Forest | losowe podzialy, anomalie izoluja sie szybciej | wartosci skrajne w pojedynczych kolumnach |
| Local Outlier Factor | porownanie gestosci z sasiadami | anomalie kontekstowe |
| One-Class SVM | granica wokol obszaru normalnego | odstepstwa od ksztaltu rozkladu |

Wiersz jest anomalia, gdy zaglosuja **co najmniej dwa z trzech**.

### Dlaczego liczby licza sie w Pythonie, a nie w modelu jezykowym

Pierwsza wersja wysylala do modelu cala tabele z prosba o analize. Modele mylily
numery wierszy, przypisywaly wartosci do zlych kolumn i zawyzaly liczbe glosow -
niezaleznie od tego, czy byl to Mistral 7B, NeMo 12B czy Qwen3 8B.

Rozwiazanie: cala analiza w pandas, model dostaje gotowe fakty i ma je tylko
sformulowac w zdania. Dzieki temu **liczbom w raporcie mozna ufac**, a jakosc
przestala zalezec od wielkosci modelu.

---

## Parametr odsetka anomalii - najwazniejsza rzecz do zrozumienia

Modele nie wiedza, co jest anomalia. Licza ciagla miare nietypowosci i musza
dostac informacje, gdzie postawic granice.

**Przy wartosci 0.05 kazdy model wskaze okolo 5 procent wierszy - niezaleznie od
tego, ile anomalii jest naprawde.** Jesli zbior jest idealnie czysty, i tak
dostaniesz 5 procent "najmniej normalnych sposrod normalnych".

Gorna granica to 0.5 - Isolation Forest i LOF odrzucaja wyzsze wartosci. Ma to
tez sens logiczny: gdyby ponad polowa wierszy byla anomaliami, to one bylyby
norma.

Jak dobrac: zacznij od 0.05, obejrzyj wykres z-score w zakladce Anomalie. Jesli
oznaczone anomalie maja z-score bliski zeru - obniz. Jesli cos ewidentnego
pominieto - podnies. Dla wykrywania naduzyc realistyczne wartosci to 0.01-0.02.

---

## Ograniczenia

- **Nie odrozni bledu danych od prawdziwej anomalii** - wiek 999 i duza
  transakcja to dla modelu to samo.
- **Nie wie, ktore kolumny sa wazne** - dlatego mozna je recznie wybrac.
- **Nie wykryje anomalii niewidocznych w liczbach.**
- **Nie zastepuje weryfikacji przez czlowieka** - wynik to lista wierszy do
  sprawdzenia, nie werdykt.
- **Ponizej okolo 100 wierszy** wyniki sa malo wiarygodne.

---

## Licencje

Wszystkie uzywane modele jezykowe sa na **Apache 2.0** - pelne prawa komercyjne,
bez oplat, bez limitu uzytkownikow, bez wymogu oznaczania produktu:

Qwen3, Mistral NeMo, Bielik 3.0, Gemma 4.

Swiadomie pominieto modele Llama - wlasna licencja producenta wymaga oznaczenia
"Built with Llama" i osobnej umowy powyzej 700 mln uzytkownikow miesiecznie.

### Prywatnosc

Modele dzialaja lokalnie przez Ollame, wiec dane nigdy nie opuszczaja komputera.
Nie ma serwera zewnetrznego ani telemetrii tresci. `.gitignore` wyklucza dane
wejsciowe, wyniki detekcji i raporty z kontroli wersji.