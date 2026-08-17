# Detektor anomalii w plikach CSV

Aplikacja desktopowa do wykrywania anomalii w dowolnym pliku CSV. Laczy trzy modele
uczenia maszynowego glosujace nad kazdym wierszem z interaktywnymi wykresami
i lokalnym modelem jezykowym, ktory opisuje wyniki i odpowiada na pytania o dane.
Wszystko dziala offline - zadne dane nie opuszczaja komputera.

---

## Spis tresci

1. [Co robi aplikacja](#co-robi-aplikacja)
2. [Struktura projektu](#struktura-projektu)
3. [Instalacja](#instalacja)
4. [Uruchamianie](#uruchamianie)
5. [Budowanie samodzielnej aplikacji](#budowanie-samodzielnej-aplikacji)
6. [Interfejs - opis zakladek](#interfejs---opis-zakladek)
7. [Jak dziala detekcja](#jak-dziala-detekcja)
8. [Tryb szeregow czasowych](#tryb-szeregow-czasowych)
9. [Raport i pytania (LLM)](#raport-i-pytania-llm)
10. [Ollama i modele jezykowe](#ollama-i-modele-jezykowe)
11. [Wydajnosc](#wydajnosc)
12. [Moduly - opis API](#moduly---opis-api)
13. [Rozwiazywanie problemow](#rozwiazywanie-problemow)
14. [Licencje i prywatnosc](#licencje-i-prywatnosc)

---

## Co robi aplikacja

Wgrywasz plik CSV, a aplikacja:

1. **Pozwala obejrzec dane** na interaktywnych wykresach przed jakakolwiek analiza.
2. **Liczy cechy pochodne** dla wybranych kolumn numerycznych - z-score, srednie
   kroczace, roznice miedzy wierszami, flagi outlierow IQR.
3. **Uruchamia trzy modele** wykrywania anomalii, ktore glosuja nad kazdym wierszem.
4. **Pokazuje wyniki na wykresach** - gdzie leza anomalie, ktora kolumna je wywolala,
   jak modele sie ze soba zgadzaja. Najechanie na anomalie pokazuje jej wartosci.
5. **Generuje raport tekstowy** po polsku przez lokalny model jezykowy.
6. **Odpowiada na pytania** o zbior danych zadawane wlasnymi slowami.
7. **Pozwala pobrac wyniki** jako CSV (pelne dane lub same anomalie), raport i rozmowe
   jako TXT.

Obsluguje dwa rodzaje danych: zwykly plik (jeden ciag obserwacji) oraz dane panelowe -
wiele jednostek obserwowanych w kolejnych okresach.

---

## Struktura projektu

```
anomaly_detector/
├── .streamlit/
│   └── config.toml              # motyw jasny, ukryty przycisk Deploy
├── grafika/                     # logo i wygenerowane ikony
├── venv/                        # srodowisko wirtualne
├── app.py                       # interfejs Streamlit - wszystkie zakladki i wykresy
├── anomaly_d.py                 # detekcja anomalii - cechy + modele ML
├── mistral_raport_generator.py  # raport i pytania przez Ollame
├── visualization.py             # wykresy do uzycia poza aplikacja (notebook)
├── desktop.py                   # launcher - natywne okno przez pywebview
├── make_app.sh                  # lekki bundle .app dla macOS
├── make_icons.sh                # generuje .icns i .ico z jednego PNG
├── build.sh                     # samodzielna binarka (macOS/Linux)
├── build.bat                    # samodzielny .exe (Windows)
├── test.ipynb                   # notebook do testow pipeline'u
├── test.csv                     # maly zbior testowy
├── bigger_test.csv              # wiekszy zbior testowy
├── requirements.txt
└── Readme.md
```

---

## Instalacja

### 1. Srodowisko wirtualne

```bash
cd anomaly_detector
python3 -m venv venv
source venv/bin/activate
```

Po aktywacji w terminalu pojawia sie `(venv)` na poczatku linii. **Wszystkie kolejne
polecenia wykonuj z aktywnym venv** - inaczej pakiety trafia do Pythona systemowego,
a aplikacja ich nie znajdzie.

### 2. Zaleznosci

```bash
pip install -r requirements.txt
```

```
pandas
numpy
scikit-learn
plotly
streamlit
requests
pywebview
```

### 3. Ollama (opcjonalnie)

Potrzebna tylko dla zakladek Raport i Pytanie:

```bash
brew install ollama
ollama serve
ollama pull qwen3:8b
```

Bez Ollamy reszta aplikacji dziala normalnie - te dwie zakladki pokaza ostrzezenie.

---

## Uruchamianie

### Tryb przegladarkowy (do rozwoju)

```bash
source venv/bin/activate
streamlit run app.py
```

### Tryb desktopowy - natywne okno

```bash
source venv/bin/activate
python desktop.py
```

Uruchamia Streamlit w tle i otwiera wlasne okno bez paska adresu. Zamkniecie okna
konczy proces serwera.

### Tryb desktopowy - dwuklik (macOS, lekki bundle)

```bash
source venv/bin/activate    # WAZNE: przed budowaniem
bash make_app.sh
```

Powstaje `Detektor Anomalii.app` do uruchamiania dwuklikiem.

**Dlaczego venv musi byc aktywny:** `make_app.sh` zapisuje w bundlu sciezke do Pythona
pobrana z `which python3`. Bez aktywnego venv zapisze sciezke do Pythona systemowego,
ktory nie ma zainstalowanych pakietow - aplikacja wywali sie przy starcie z bledem
`ModuleNotFoundError`.

**Uwaga:** ten bundle wazy kilka KB i tylko wskazuje na katalog projektu. Nie zadziala
na innym komputerze i przestanie dzialac po przeniesieniu projektu. Do rozdawania
sluzy binarka opisana nizej.

### Windows

`make_app.sh` dziala tylko na macOS, ale sama aplikacja jest wieloplatformowa.
Utworz `start.bat` w katalogu projektu:

```bat
@echo off
cd /d "%~dp0"
start "" pythonw desktop.py
```

`pythonw` uruchamia aplikacje bez czarnego okna konsoli.

---

## Budowanie samodzielnej aplikacji

Wersja dzialajaca **bez zainstalowanego Pythona** u odbiorcy.

| | `make_app.sh` | `build.sh` / `build.bat` |
|---|---|---|
| Rozmiar | kilka KB | okolo 580 MB |
| Czas budowania | sekunda | 2-5 minut |
| Wymaga Pythona u odbiorcy | tak | nie |
| Przenosny na inny komputer | nie | tak |
| Do czego | wlasny komputer, demo, obrona | oddanie komus |

### Krok 1: ikona

Wrzuc logo do `grafika/logo.png` - najlepiej PNG 1024x1024 z przezroczystym tlem.

```bash
pip install pillow
bash make_icons.sh grafika/logo.png
```

Skrypt tworzy `grafika/icon.icns` (macOS), `grafika/icon.ico` (Windows, siedem
rozmiarow od 16 do 256 px) oraz `icon.png` dla `make_app.sh`. Skrypty budujace same
znajduja te pliki.

### Krok 2: budowanie

```bash
source venv/bin/activate
pip install pyinstaller
bash build.sh              # macOS / Linux
```

```bat
venv\Scripts\activate
pip install pyinstaller
build.bat                  REM Windows
```

Wynik:

- macOS: `dist/DetektorAnomalii.app`
- Windows: `dist\DetektorAnomalii\DetektorAnomalii.exe`
- Linux: `dist/DetektorAnomalii/DetektorAnomalii`

### Co robia flagi PyInstallera

Streamlit nie daje sie spakowac domyslnymi ustawieniami - stad dluga lista:

| Flaga | Po co |
|---|---|
| `--collect-all streamlit` | pliki frontendu (JS/CSS). Bez tego biala pusta strona |
| `--collect-all plotly` | szablony i zasoby wykresow |
| `--collect-all sklearn` `--collect-all scipy` | moduly ladowane dynamicznie |
| `--copy-metadata ...` | Streamlit sprawdza wersje przez `importlib.metadata`. Brak = `PackageNotFoundError` |
| `--add-data ".streamlit:.streamlit"` | motyw jasny i ukryty przycisk Deploy |
| `--hidden-import ...` | moduly importowane napisami, niewidoczne dla analizy statycznej |

Na Windowsie separator w `--add-data` to **srednik**, nie dwukropek. `build.bat` juz
to uwzglednia.

### Dlaczego launcher dziala inaczej po spakowaniu

W zwyklym uruchomieniu `desktop.py` startuje Streamlit jako osobny proces przez
`subprocess.Popen([sys.executable, "-m", "streamlit", ...])`.

W binarce **`sys.executable` wskazuje na sama aplikacje**, nie na Pythona - ten sam
kod uruchamialby aplikacje w nieskonczonej petli. Dlatego w trybie spakowanym serwer
startuje w watku, wewnatrz tego samego procesu (`streamlit.web.bootstrap.run`).

Dochodzi jeszcze jeden szczegol: `bootstrap.run` instaluje obsluge sygnalu SIGTERM,
a `signal.signal` dziala tylko na glownym watku. Bez tymczasowego podmienienia tej
funkcji serwer w watku w ogole by nie wstal.

Oba tryby sa obslugiwane automatycznie - launcher sprawdza `sys.frozen`.

### Ollama nie zostanie spakowana

Binarka zawiera aplikacje i biblioteki Pythona, ale **nie Ollame ani modelu
jezykowego** (4-7 GB). Odbiorca musi zainstalowac ja osobno, jesli chce korzystac
z zakladek Raport i Pytanie.

---

## Interfejs - opis zakladek

### Dane

Podglad pierwszych 200 wierszy, liczba wierszy i kolumn, statystyki opisowe oraz
wykaz brakow danych. Zwroc uwage na liczbe kolumn numerycznych - jesli jest mniejsza
niz oczekujesz, ktoras kolumna zostala wczytana jako tekst (zwykle przez przecinek
dziesietny albo spacje w liczbach).

### Wykresy

Eksploracja surowych danych przed detekcja: wykres liniowy, histogram, boxplot
i macierz korelacji. Wszystkie sa interaktywne - mozna przyblizac, przesuwac
i najezdzac na punkty.

Kazdy wykres ma rozwijany panel **Zakres osi** z czterema polami (X od/do, Y od/do).
Puste pole oznacza zakres automatyczny - skasowanie wartosci przywraca stan domyslny.

Pola liczbowe zamiast suwakow przyjmuja dowolna wartosc i przycinaja ja do
dopuszczalnego zakresu, informujac co zostalo uzyte. Wpisanie `-1` przy liczbie
przedzialow da `5`, wpisanie `10000` da `200`.

Wykresy liniowe sa automatycznie probkowane powyzej 5000 punktow, zeby interfejs
pozostal plynny.

### Detekcja

**Wybor kolumn** - odznacz te, ktore nie niosa informacji: numery porzadkowe, ID,
kody. Trafiaja one do modeli tak samo jak reszta i psuja wynik (rosnacy licznik zawsze
wyglada jak idealny trend).

**Tryb analizy** - zwykly plik albo szereg czasowy z podzialem na jednostki. Aplikacja
nie zgaduje tego sama, bo bledne rozpoznanie dawaloby pewne siebie, ale bezsensowne
wyniki.

**Parametry:**

| Parametr | Zakres | Znaczenie |
|---|---|---|
| Okno sredniej kroczacej | 2 - liczba wierszy | ile ostatnich wierszy wchodzi do sredniej |
| Oczekiwany odsetek anomalii | 0.01 - 0.30 | zakladany udzial anomalii w danych |
| Szybki SVM | tak/nie | `SGDOneClassSVM` zamiast `OneClassSVM` |

Po detekcji: metryki per model, podzial na rodzaje anomalii (w trybie panelowym),
tabela wynikow i przyciski pobierania CSV.

### Anomalie

- **glosy modeli** - ile wierszy wykryl kazdy model i ile przeszlo finalne glosowanie
- **przyczyny wg kolumny** - w ktorej kolumnie najczesciej lezy zrodlo anomalii
- **szeregi wedlug jednostek** (tylko tryb panelowy) - kazda linia to jedna jednostka
- **srednia kroczaca** - wartosci z zaznaczonymi anomaliami
- **z-score** - z regulowanym progiem

Najechanie na anomalie pokazuje dymek z numerem wiersza, wartoscia, liczba glosow
modeli, z-score i rodzajem anomalii.

### Raport

Wybor modelu (lista pobierana automatycznie z Ollamy) i generowanie opisu wszystkich
wykrytych anomalii. Raport powstaje **partiami** - po kazdej mozna przerwac przyciskiem
**Zatrzymaj** i zachowac to, co juz powstalo. Pasek postepu pokazuje ile anomalii
opisano.

Bez podzialu na partie Streamlit bylby zablokowany do konca generowania i przycisk
zatrzymania nie moglby zadzialac. Mniejsza partia = szybsza reakcja na zatrzymanie.

### Pytanie

Pytania o zbior danych zadawane wlasnymi slowami. Model widzi strukture, statystyki,
braki danych, podsumowanie detekcji i opis najsilniejszych anomalii - podglad tego
kontekstu jest w rozwijanym panelu.

Historia rozmowy jest zachowywana (ostatnie trzy pary trafiaja do promptu, wiec mozna
dopytywac), da sie ja wyczyscic i pobrac jako TXT. Zakladka dziala tez przed detekcja -
wtedy model widzi tylko strukture i statystyki.

### Dobre praktyki

Poradnik w aplikacji: przygotowanie pliku CSV, kolejnosc pracy, dobor parametrow,
interpretacja wynikow z kazdej zakladki i ograniczenia metody.

---

## Jak dziala detekcja

### Krok 1: cechy statystyczne

Dla kazdej wybranej kolumny numerycznej:

- `{kol}_diff_mean` - odchylenie od sredniej calej kolumny
- `{kol}_zscore` - odchylenie w jednostkach odchylenia standardowego

### Krok 2: cechy kroczace

Z oknem `window` i `min_periods=1`, wiec pierwsze wiersze licza sie z tego co dostepne:

- `{kol}_rolling_mean` - srednia kroczaca
- `{kol}_rolling_std` - odchylenie kroczace
- `{kol}_diff_prev` - roznica z poprzednim wierszem
- `{kol}_diff_from_rolling_mean` - odstepstwo od lokalnej normy

**Wazne zalozenie:** kolejnosc wierszy jest traktowana jako kolejnosc w czasie.

### Krok 3: flagi outlierow (IQR)

`{kol}_is_outlier` - 1, gdy wartosc wykracza poza `Q1 - 1.5*IQR` / `Q3 + 1.5*IQR`.

Flagi **nie wycinaja** wierszy przed modelami. To swiadoma decyzja: prawdziwe anomalie
czesto same w sobie sa wartosciami skrajnymi, wiec usuwanie outlierow przed detekcja
usuwaloby dokladnie to, czego szukamy.

### Krok 4: standaryzacja

`StandardScaler` na wszystkich cechach. Wymagane przez LOF i SVM, ktore licza
odleglosci - bez tego kolumna w tysiacach zdominowalaby kolumne w ulamkach.
Isolation Forest jest na to niewrazliwy.

### Krok 5: modele i glosowanie

| Model | Zasada dzialania | Zlozonosc |
|---|---|---|
| Isolation Forest | losowe podzialy, anomalie izoluja sie szybciej | liniowa |
| Local Outlier Factor | porownanie gestosci z sasiadami | ~kwadratowa |
| One-Class SVM | granica wokol obszaru normalnego | kwadratowa do szesciennej |

Kolumny wynikowe:

- `Anomaly_IF`, `Anomaly_LOF`, `Anomaly_SVM` - glosy pojedynczych modeli (0/1)
- `Anomaly_Votes` - suma glosow (0-3)
- `Anomaly_Final` - 1, gdy **co najmniej 2 z 3** modeli wskazaly anomalie
- `Has_Outlier` - w ilu kolumnach wiersz jest outlierem IQR

### O parametrze "oczekiwany odsetek anomalii"

Modele nie maja wbudowanej wiedzy, co jest anomalia. Licza ciagly score dziwnosci
i musza wiedziec, gdzie postawic granice - wlasnie to robi ten parametr.

**Konsekwencja:** przy wartosci 0.05 kazdy model wskaze okolo 5 procent wierszy,
niezaleznie od tego, ile anomalii jest naprawde. Jesli dane sa idealnie czyste, i tak
dostaniesz 5 procent najmniej normalnych z normalnych. Jesli anomalii jest 15 procent,
model znajdzie tylko najsilniejsze 5 i reszte przepusci.

Finalna kolumna `Anomaly_Final` jest odporniejsza - jako przeciecie trzech list daje
zwykle **mniej** niz zadany odsetek.

**Jak dobrac:** zacznij od 0.05 i spojrz na wykres z-score. Jesli oznaczone anomalie
maja z-score bliski zeru - obniz. Jesli cos oczywistego zostalo pominiete - podnies.
Dla wykrywania naduzyc realistyczne wartosci to 0.01-0.02.

---

## Tryb szeregow czasowych

Dla danych panelowych - wiele jednostek (np. gospodarstw) obserwowanych w kolejnych
okresach. Kazdy wiersz to jedna jednostka w jednym momencie.

Wskazujesz kolumne z jednostka i kolumne z okresem. **Uklad pliku nie ma znaczenia** -
dane moga byc ulozone chronologicznie (A, B, C, A, B, C...) albo jednostka po
jednostce. Aplikacja sortuje je wewnetrznie na czas obliczen, a na koncu przywraca
pierwotna kolejnosc, zeby numery wierszy w eksporcie zgadzaly sie z plikiem zrodlowym.

### Dodatkowe cechy

Srednie kroczace i roznice licza sie **osobno dla kazdej jednostki** - bez tego
mieszalyby ze soba rozne gospodarstwa i byly bez sensu. Dochodza:

- `{kol}_jump_score` - o ile odchylen wlasnej historii skoczyla wartosc
- `{kol}_zscore_wlasny` - odchylenie od wlasnej historii jednostki
- `{kol}_zscore_miedzy` - odchylenie od pozostalych jednostek **w tym samym okresie**

### Rodzaje anomalii

Aplikacja rozroznia dwa wzorce i zapisuje wynik w kolumnie `Rodzaj_Anomalii`:

| Rodzaj | Co oznacza |
|---|---|
| nagla zmiana | skok wzgledem wlasnej historii jednostki |
| odstaje od innych | wartosc nietypowa na tle reszty jednostek w tym okresie |
| nagla zmiana + odstaje od innych | oba naraz - najsilniejszy przypadek |
| brak wyraznego wzorca | modele cos wykryly, ale zaden wzorzec nie dominuje |

Dodatkowo kolumny `Nagla_Zmiana` i `Odstaje_Od_Innych` zawieraja wartosci liczbowe
tych miar.

### Uwaga o echu po skoku

Skok w danym okresie zanieczyszcza srednia kroczaca na kolejne `window` okresow, wiec
kilka wierszy po prawdziwej anomalii tez bywa oznaczonych. Kolumna `Rodzaj_Anomalii`
pomaga je odsiac - dla takich ech pokazuje "brak wyraznego wzorca". To nieodlaczna
cecha cech kroczacych, nie usterka.

---

## Raport i pytania (LLM)

### Dlaczego cala analiza jest liczona w Pythonie

Pierwsze podejscie wysylalo do modelu cala tabele CSV z prosba o analize. Efekt byl
zly niezaleznie od modelu - mylil numeracje wierszy, przypisywal wartosci do zlych
kolumn, zawyzal liczbe glosujacych modeli. Male modele lokalne nie radza sobie
z precyzyjnym czytaniem danych tabelarycznych wklejonych jako tekst.

Rozwiazanie: **wszystko liczy pandas**, a model dostaje gotowe fakty:

```
Wiersz 97: glowna przyczyna anomalii to kolumna 'wartosc_1' (z-score=13.58,
roznica od sredniej kroczacej=234.00, flaga outlier IQR=tak).
Wykryta przez 2/3 modeli: Isolation Forest, LOF.
Rodzaj: nagla zmiana + odstaje od innych.
```

Model ma je tylko sformulowac w plynne zdania **bez zmieniania liczb**. Dzieki temu
jakosc raportu przestala zalezec od wyboru modelu.

W praktyce: **liczbom mozna ufac**, natomiast sformulowania moga sie roznic miedzy
modelami i uruchomieniami.

### Zakladka Pytanie

Ta sama zasada. Model dostaje policzony opis zbioru - liczbe wierszy, nazwy kolumn,
statystyki opisowe, braki danych, podsumowanie detekcji i opis najsilniejszych
anomalii. Cały kontekst to okolo 1300 znakow, wiec miesci sie w kazdym modelu.

Model **nie widzi surowej tabeli**, wiec nie odpowie na pytania o pojedyncze wiersze
spoza listy najsilniejszych anomalii. Prompt zawiera instrukcje, zeby w takim wypadku
napisac wprost, ze tych danych nie ma, zamiast zgadywac.

---

## Ollama i modele jezykowe

Ollama uruchamia modele lokalnie i wystawia REST API na porcie `11434`. Zadne dane nie
ida do chmury, nie ma kluczy API ani oplat.

```bash
ollama serve                  # uruchomienie serwera
ollama pull qwen3:8b          # pobranie modelu
ollama list                   # lista pobranych modeli
ollama show qwen3:8b          # parametry, m.in. rozmiar kontekstu
```

Aplikacja sama pobiera liste dostepnych modeli przez `http://localhost:11434/api/tags`.

### Przetestowane modele

| Model | Rozmiar | Uwagi |
|---|---|---|
| `mistral` | 7B | najslabszy, duzo bledow przy tabelach |
| `mistral-nemo` | 12B | lepszy, kontekst 128k, nadal mylil kolumny |
| `qwen3:8b` | 8B | najlepsza precyzja z testowanych |
| `bielik-11b-v3.0-instruct` | 11B | polski model, mocny na polskich benchmarkach |

Po przeniesieniu obliczen do Pythona roznice miedzy modelami sa duzo mniej istotne.

---

## Wydajnosc

Pomiary na 5000 wierszy i 4 kolumnach numerycznych:

| Etap | Czas |
|---|---|
| Detekcja, szybki SVM | ~0.5 s |
| Detekcja, klasyczny SVM | ~0.8 s |
| Raport LLM, 100 anomalii | kilka minut |

**Waskim gardlem nie sa modele, tylko generowanie raportu.** Kazda anomalia to osobny
tekst do wygenerowania przez model jezykowy.

### Szybki vs klasyczny SVM

| | `OneClassSVM` | `SGDOneClassSVM` |
|---|---|---|
| Rozwiazanie | dokladne (programowanie kwadratowe) | przyblizone (spadek gradientu) |
| Granica | nieliniowa (kernel rbf) | liniowa |
| Zlozonosc | kwadratowa do szesciennej | liniowa |
| Dokladnosc | wyzsza | nizsza |

Na tym samym zbiorze 5000 wierszy klasyczny SVM wskazal 219 anomalii, szybki 103.

**Rekomendacja:** dla plikow do kilkunastu tysiecy wierszy wylacz szybki tryb - roznica
w czasie jest znikoma, a dokladnosc wieksza. SVM to i tak tylko jeden z trzech
glosujacych modeli.

---

## Moduly - opis API

### `anomaly_d.py` - klasa `anomaly_detector`

```python
detect(df, window=10, contamination=0.05, fast_svm=True,
       feature_cols=None, group_col=None, time_col=None) -> (df, num_cols)
```

Pelny pipeline na gotowym DataFrame. Podanie `group_col` i `time_col` wlacza tryb
szeregow czasowych. `feature_cols=None` oznacza wszystkie kolumny numeryczne.

```python
read_csv_add_features_and_model(file_path, srednia_korczaca=10, ...) -> (df, num_cols)
```

Wersja wczytujaca prosto z pliku. **Zwraca krotke**, nie sam DataFrame.

Metody skladowe: `add_stat_features`, `add_rolling_features`, `add_outlier_flags`,
`add_group_rolling_features`, `add_within_group_stats`, `add_cross_sectional_stats`,
`run_models`, `add_anomaly_kind`.

### `mistral_raport_generator.py` - klasa `report_generator`

```python
generate_report(df, model="mistral") -> str
```
Opis anomalii z podanego DataFrame.

```python
ask_about_data(df, question, num_cols=None, model="mistral", historia=None) -> str
```
Odpowiedz na pytanie o zbior danych.

```python
build_row_facts(df, num_cols) -> str
build_data_context(df, num_cols=None, max_anom=15) -> str
ask_mistral(prompt, model="mistral", timeout=600) -> str
```

### `visualization.py` - klasa `anomaly_visualizer`

Wykresy do uzycia poza aplikacja, np. w notebooku.

---

## Rozwiazywanie problemow

**Aplikacja nie startuje po dwukliku**

```bash
"Detektor Anomalii.app/Contents/MacOS/launcher"
```

Uruchomienie z terminala pokaze blad, ktorego okno nie wyswietli.

**`ModuleNotFoundError` przy starcie bundla**

Bundle wskazuje na zly interpreter. Sprawdz:

```bash
cat "Detektor Anomalii.app/Contents/MacOS/launcher"
```

Sciezka w linii `exec` musi zawierac `venv`. Jesli nie - aktywuj venv i przebuduj.

**Biala pusta strona w binarce** - brakuje `--collect-all streamlit`.

**`PackageNotFoundError` w binarce** - dopisz pakiet do `--copy-metadata`.

**Bialy tekst na bialym tle** - brak `.streamlit/config.toml` albo aplikacja
uruchomiona z innego katalogu. Streamlit szuka configu wzgledem katalogu roboczego.

**`NameError: name 'alt_...' is not defined`** - pozostalosc po starszej wersji na
Altairze. Wszystkie wykresy sa teraz w Plotly, wywolywane przez `show(fig_...)`.

**Ostrzezenia o `torch` podczas budowania** - nieszkodliwe, sklearn i scipy szukaja
opcjonalnego backendu.

**macOS blokuje aplikacje** - prawy przycisk > Otworz > Otworz. Tylko raz.

**Detekcja trwa bardzo dlugo** - to prawie na pewno generowanie raportu, nie modele.
Zmniejsz partie albo zatrzymaj przyciskiem.

**Zmiany w kodzie nie sa widoczne** - bundle `.app` z `make_app.sh` **nie wymaga
przebudowy**, launcher czyta pliki z dysku przy kazdym uruchomieniu. Binarka
z `build.sh` **wymaga** przebudowy, bo ma kopie plikow w srodku.

---

## Licencje i prywatnosc

Wszystkie uzywane modele jezykowe sa na licencji **Apache 2.0**, ktora daje pelne
prawa komercyjne bez oplat, bez limitu uzytkownikow i bez wymogu atrybucji:

- Mistral 7B, Mistral NeMo
- Qwen3
- Bielik 3.0 (Apache 2.0 z dodatkowym regulaminem dotyczacym odpowiedzialnego uzycia,
  ktory nie ogranicza praw komercyjnych)

Modele Llama od Meta maja wlasna licencje z wymogiem oznaczenia "Built with Llama"
i progiem 700 milionow uzytkownikow miesiecznie - dlatego nie sa tu uzywane.

### Prywatnosc danych

Modele dzialaja lokalnie przez Ollame, wiec dane z CSV nigdy nie opuszczaja komputera.
Nie ma serwera zewnetrznego, logowania zapytan ani telemetrii tresci. Ryzyko lezy
wylacznie po stronie tego, co zrobisz z wygenerowanym raportem i plikiem zrodlowym -
warto dodac dane wejsciowe i raporty do `.gitignore`.