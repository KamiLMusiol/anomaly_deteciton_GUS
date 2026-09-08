# backend_ml_llm

Warstwa obliczeniowa - wszystko co liczy i nie dotyka interfejsu.

Te moduly nie importuja Streamlita i nie wiedza o jego istnieniu. Dzieki temu
mozna ich uzywac niezaleznie: w notatniku Jupyter, w skrypcie wsadowym
przetwarzajacym wiele plikow, albo w zupelnie innej aplikacji.

## Pliki

| Plik | Zawartosc |
|---|---|
| `anomaly_d.py` | klasa `anomaly_detector` - cechy pochodne, trzy modele ML, glosowanie |
| `mistral_raport_generator.py` | klasa `report_generator` - fakty, kontekst, komunikacja z Ollama |
| `desktop.py` | launcher aplikacji w natywnym oknie (pywebview) |

## anomaly_d.py

Glowna metoda to `detect()` - przyjmuje DataFrame, zwraca krotke
`(df_z_wynikami, num_cols)`.

```python
from backend_ml_llm.anomaly_d import anomaly_detector

df_wynik, num_cols = anomaly_detector.detect(
    df,
    window=10,              # okno sredniej kroczacej
    contamination=0.05,     # zakladany odsetek anomalii (max 0.5)
    fast_svm=True,          # przyblizony SVM zamiast dokladnego
    feature_cols=None,      # ktore kolumny analizowac, None = wszystkie liczbowe
    group_col=None,         # kolumna jednostki - wlacza tryb panelowy
    time_col=None,          # kolumna okresu - wlacza tryb panelowy
)
```

Kolumny dodawane do wyniku:

- `{kol}_zscore`, `{kol}_diff_mean` - odchylenie od sredniej calej kolumny
- `{kol}_rolling_mean`, `{kol}_rolling_std`, `{kol}_diff_prev`,
  `{kol}_diff_from_rolling_mean` - kontekst lokalny
- `{kol}_is_outlier` - flaga IQR
- `Anomaly_IF`, `Anomaly_LOF`, `Anomaly_SVM` - glosy modeli
- `Anomaly_Votes` (0-3), `Anomaly_Final` (1 gdy >=2 glosy)
- `Has_Outlier` - w ilu kolumnach wiersz jest outlierem

W trybie panelowym dochodza: `{kol}_jump_score`, `{kol}_zscore_wlasny`,
`{kol}_zscore_miedzy`, `Nagla_Zmiana`, `Odstaje_Od_Innych`, `Rodzaj_Anomalii`.

## mistral_raport_generator.py

Kluczowa zasada: **wszystkie liczby licza sie tutaj, w Pythonie**. Model
jezykowy dostaje gotowe fakty i ma je tylko sformulowac w zdania.

Wynikalo to z testow - male modele lokalne mylily numery wierszy i przypisywaly
wartosci do zlych kolumn, gdy dostawaly surowa tabele do analizy.

```python
from backend_ml_llm.mistral_raport_generator import report_generator

# opis anomalii
tekst = report_generator.generate_report(df_anomalie, model="qwen3:8b")

# pytanie o zbior
odp = report_generator.ask_about_data(df, "Ktora kolumna odstaje najbardziej?",
                                      num_cols, model="qwen3:8b")
```

Wymaga dzialajacej Ollamy na `http://localhost:11434`.

## desktop.py

Uruchamia serwer Streamlit i otwiera natywne okno. Dziala w dwoch trybach,
rozpoznawanych automatycznie przez `sys.frozen`:

- **zwykly** - Streamlit jako osobny proces
- **spakowany** - serwer w watku tego samego procesu, bo w binarce
  `sys.executable` wskazuje na sama aplikacje i uruchomienie podprocesem
  dawaloby nieskonczona petle

Szuka `app.py` **o jeden poziom wyzej** (w katalogu projektu), bo sam lezy
w tym podfolderze.

```bash
python backend_ml_llm/desktop.py
```