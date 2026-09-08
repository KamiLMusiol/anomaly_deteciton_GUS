"""
Punkt wejscia aplikacji. Caly kod jest teraz podzielony na moduly - ten
plik tylko je spina: ustawia strone, inicjalizuje stan, rysuje panel
boczny i przelacza miedzy siedmioma zakladkami.

    konkrerne logiki:
  styles.py            - kolory, CSS, wyglad wykresow
  pola.py              - pola liczbowe z przycinaniem, zakresy osi
  narzedzia.py         - CSV, Ollama, probkowanie
  wykresy.py           - wszystkie wykresy plotly
  magazyn_danych.py    - zarzadzanie wczytanymi zbiorami (session_state)
  panel_boczny.py       - wgrywanie plikow
  zakladka_*.py         - kazda zakladka w osobnym pliku
  anomaly_d.py          - detekcja anomalii, cechy, modele ML
  mistral_raport_generator.py - warstwa LLM
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontend_streamlit.magazyn_danych import MagazynDanych
from frontend_streamlit.styles import Wyglad
from frontend_streamlit import panel_boczny
from frontend_streamlit import zakladka_dane
from frontend_streamlit import zakladka_wykresy
from frontend_streamlit import zakladka_detekcja
from frontend_streamlit import zakladka_anomalie
from frontend_streamlit import zakladka_raport
from frontend_streamlit import zakladka_pytanie
from frontend_streamlit import zakladka_pomoc

st.set_page_config(page_title="detekcja anomalii", page_icon=None, layout="wide")

Wyglad.zastosuj()  # aplikujemy style
MagazynDanych.inicjalizuj()

panel_boczny.renderuj()


# ---------------------------------------------------------------- main

st.title("Wykrywanie anomalii w danych CSV")

if not st.session_state.zbiory:
    st.info("Wgraj plik w panelu po lewej, zeby zaczac. Mozna wgrac kilka naraz.")
    st.stop()  # zatrzymuje dalsze wykonanie skryptu

tab_data, tab_explore, tab_detect, tab_anom, tab_report, tab_ask, tab_help = st.tabs(
    [" Dane", " Wykresy", " Detekcja", " Anomalie", " Raport", " Pytanie", " Dobre praktyki"]
)

with tab_data:
    zakladka_dane.renderuj()

with tab_explore:
    zakladka_wykresy.renderuj()

with tab_detect:
    zakladka_detekcja.renderuj()

with tab_anom:
    zakladka_anomalie.renderuj()

with tab_report:
    zakladka_raport.renderuj()

with tab_ask:
    zakladka_pytanie.renderuj()

with tab_help:
    zakladka_pomoc.renderuj()
