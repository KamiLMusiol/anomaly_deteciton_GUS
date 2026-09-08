"""
Zakladka Anomalie - wykresy pokazujace wynki detekcji
"""

import streamlit as st

from frontend_streamlit.pola import Pola
from frontend_streamlit.styles import ZSCORE_HELP
from frontend_streamlit.wykresy import Wykresy


def renderuj():
    st.subheader("Wykresy anomalii")

    if st.session_state.result_df is None:
        st.info("Najpierw uruchom detekcje w zakladce 'Detekcja'.")
        return

    res = st.session_state.result_df #wybrany datafrae
    num_cols = st.session_state.num_cols #kolumny numeryczne

    lim_votes = Pola.axis_fields("votes")  #obketk z pola.py gdzie ustawasz x i y
    Wykresy.show(Wykresy.fig_votes(res, lim_votes))  # z wykresy generujesz

    lim_per_col = Pola.axis_fields("per_col")
    f = Wykresy.fig_anom_per_col(res, num_cols, lim_per_col)
    if f is not None:
        Wykresy.show(f)

    st.divider()
    col = st.selectbox("Kolumna do analizy", num_cols, key="anom_col")

    if "Rodzaj_Anomalii" in res.columns:  # tryb szeregow czasowych
        st.markdown("#### Szeregi wedlug jednostek")
        gcol = st.session_state.get("group_col")
        tcol = st.session_state.get("time_col")
        jednostki = sorted(res[gcol].astype(str).unique())
        wybrane = st.multiselect("Jednostki na wykresie", jednostki,
                                 default=jednostki[:6], key="wybrane_jednostki")
        if wybrane:
            lim_panel = Pola.axis_fields("panel")
            Wykresy.show(Wykresy.fig_grupy(res, col, gcol, tcol, wybrane, lim_panel))
        st.caption(
            "Kazda linia to jedna jednostka. Czerwone kwadraty to wiersze uznane za anomalie. "
            "Skok pojedynczej linii w gore lub w dol to nagla zmiana, a linia biegnaca "
            "caly czas z dala od pozostalych to odstawanie od reszty."
        )
        st.divider()

    lim_roll = Pola.axis_fields("roll")
    Wykresy.show(Wykresy.fig_rolling_anom(res, col, lim_roll))

    thr = Pola.num_field("Prog z-score", 1.0, 6.0, 3.0, 0.5, "thr", is_int=False,
                         help=ZSCORE_HELP)
    lim_z = Pola.axis_fields("zscore")
    Wykresy.show(Wykresy.fig_zscore_anom(res, col, thr, lim_z))
    st.caption("Najedz na kwadrat, zeby zobaczyc wartosc, z-score i liczbe glosow modeli.")
    st.caption(ZSCORE_HELP)
