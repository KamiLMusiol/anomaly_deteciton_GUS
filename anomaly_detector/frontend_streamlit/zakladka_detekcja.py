"""
Zakladka Detekcja - wybor kolumn, tryb analizy (zwykly / szeregi czasowe),
parametry modeli i uruchomienie calego pipeline'u z anomaly_d.py.
"""

import streamlit as st

from backend_ml_llm.anomaly_d import anomaly_detector
from frontend_streamlit.magazyn_danych import MagazynDanych
from frontend_streamlit.narzedzia import Narzedzia
from frontend_streamlit.pola import Pola


def renderuj():
    raw_df = MagazynDanych.aktywny_df()
    all_num_cols = list(raw_df.select_dtypes(include="number").columns)

    st.subheader("Detekcja anomalii")

    if not all_num_cols:
        # zbior moze byc tekstowy - np. slownik wgrany tylko po to, zeby go z czyms polaczyc
        st.warning(f"Zbior '{st.session_state.aktywny}' nie ma kolumn liczbowych - detekcja anomalii "
                   "wymaga przynajmniej jednej. Wybierz inny zbior w panelu bocznym.")
        return

    st.markdown("#### Kolumny do analizy")
    feature_cols = st.multiselect(
        "Ktore kolumny numeryczne analizowac",
        all_num_cols,
        default=all_num_cols,
        key="feature_cols",
        help="Odznacz kolumny, ktore nie niosa informacji - numery porzadkowe, ID, kody. "
             "Trafiaja one do modeli tak samo jak reszta i psuja wynik.",
    )

    st.markdown("#### Tryb analizy")
    tryb = st.radio(
        "Rodzaj danych",
        ["Zwykly plik (jeden szereg)", "Szereg czasowy z podzialem na jednostki"],
        key="tryb",
        help="Drugi tryb jest dla danych panelowych - wiele jednostek (np. gospodarstw) "
             "obserwowanych w kolejnych okresach. Srednie kroczace licza sie wtedy osobno "
             "dla kazdej jednostki.",
    )

    group_col = None
    time_col = None

    if tryb.startswith("Szereg"):
        wszystkie_kol = list(raw_df.columns)
        cg1, cg2 = st.columns(2)
        with cg1:
            group_col = st.selectbox(
                "Kolumna z jednostka (np. gospodarstwo)", wszystkie_kol, key="group_col",
                help="Identyfikator jednostki. Dla kazdej z nich osobno licza sie srednie "
                     "kroczace i roznice miedzy okresami.",
            )
        with cg2:
            time_col = st.selectbox(
                "Kolumna z okresem", wszystkie_kol,
                index=min(1, len(wszystkie_kol) - 1), key="time_col",
                help="Data lub numer okresu. Dane zostana posortowane wedlug jednostki i okresu.",
            )

        if group_col == time_col:
            st.error("Kolumna z jednostka i kolumna z okresem musza byc rozne.")

        st.info(
            "W tym trybie wykrywane sa dwa rodzaje anomalii: **nagla zmiana** wewnatrz "
            "jednostki (skok wzgledem jej wlasnej historii) oraz **odstawanie od innych** "
            "jednostek w tym samym okresie. Wynik trafia do kolumny `Rodzaj_Anomalii`."
        )

    st.markdown("#### Parametry")
    c1, c2, c3 = st.columns(3)
    with c1:
        window = Pola.num_field("Okno sredniej kroczacej", 2, max(len(raw_df), 2), 10, 1, "window",
                                help="Ile ostatnich wierszy wchodzi do sredniej kroczacej. "
                                     "W trybie szeregow czasowych - ile ostatnich okresow danej jednostki.")
    with c2:
        contamination = Pola.num_field("Oczekiwany odsetek anomalii", 0.001, 0.5, 0.05, 0.01,
                                       "contamination", is_int=False,
                                       help="Zakladany udzial anomalii w danych, od 0.001 do 0.5. "
                                            "Gorna granica to 0.5, poniewaz Isolation Forest i LOF nie "
                                            "przyjmuja wyzszych wartosci - i slusznie, bo gdyby ponad "
                                            "polowa wierszy byla anomaliami, to one bylyby norma. "
                                            "Modele tna wynik dokladnie na tym progu, wiec przy 0.05 "
                                            "kazdy model wskaze okolo 5 procent wierszy niezaleznie "
                                            "od tego, ile anomalii jest naprawde.")
    with c3:
        fast_svm = st.checkbox(
            "Szybki SVM", value=False,
            help="Wariant przyblizony (SGDOneClassSVM). Domyslnie WYLACZONY, bo okazal sie "
                 "niestabilny - na czesci zbiorow wykrywa zero anomalii albo dwa razy za duzo, "
                 "co sprowadza glosowanie do dwoch modeli zamiast trzech. Na malych plikach "
                 "wariant dokladny jest rownie szybki. Wlacz to pole dopiero, gdy detekcja "
                 "trwa niewygodnie dlugo (powyzej kilkudziesieciu tysiecy wierszy).")

    st.caption(
        "Kolejnosc wierszy jest traktowana jako kolejnosc w czasie - srednia kroczaca ma sens "
        "tylko dla danych posortowanych chronologicznie."
    )

    if st.button("Uruchom detekcje", type="primary"):
        if not feature_cols:
            st.error("Wybierz przynajmniej jedna kolumne do analizy.")
        elif group_col is not None and group_col == time_col:
            st.error("Kolumna z jednostka i kolumna z okresem musza byc rozne.")
        else:
            with st.spinner("Licze cechy i uruchamiam modele..."):
                try:
                    result_df, num_cols = anomaly_detector.detect(
                        raw_df, window=window, contamination=contamination, fast_svm=fast_svm,
                        feature_cols=feature_cols, group_col=group_col, time_col=time_col,
                    )
                    st.session_state.result_df = result_df
                    st.session_state.num_cols = num_cols
                    st.session_state.report = None
                except Exception as e:
                    st.error(f"Blad detekcji: {e}")

    if st.session_state.result_df is None:
        return

    res = st.session_state.result_df
    st.success(f"Gotowe. Wykryto {int(res['Anomaly_Final'].sum())} anomalii "
               f"na {len(res)} wierszy.")

    glosy = {"Isolation Forest": int(res["Anomaly_IF"].sum()),
             "LOF": int(res["Anomaly_LOF"].sum()),
             "One-Class SVM": int(res["Anomaly_SVM"].sum())}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Isolation Forest", glosy["Isolation Forest"])
    c2.metric("LOF", glosy["LOF"])
    c3.metric("One-Class SVM", glosy["One-Class SVM"])
    c4.metric("Finalnie (>=2/3)", int(res["Anomaly_Final"].sum()))

    # Model, ktory nie wskazal niczego, w praktyce nie bierze udzialu w glosowaniu -
    # wynik opiera sie wtedy na dwoch modelach zamiast trzech. Warto o tym powiedziec,
    # bo bez tego uzytkownik nie ma jak tego zauwazyc.
    puste = [n for n, v in glosy.items() if v == 0]
    if puste:
        st.warning(
            f"Model {' i '.join(puste)} nie wskazal zadnego wiersza, wiec nie bierze udzialu "
            f"w glosowaniu - wynik opiera sie na pozostalych. Jesli zaznaczono 'Szybki SVM', "
            f"sprobuj go odznaczyc. Jesli nie, rozwaz podniesienie oczekiwanego odsetka anomalii."
        )

    if "Rodzaj_Anomalii" in res.columns:  # tylko tryb szeregow czasowych
        st.markdown("#### Rodzaje wykrytych anomalii")
        podzial = res[res["Anomaly_Final"] == 1]["Rodzaj_Anomalii"].value_counts()
        st.dataframe(podzial.rename("liczba wierszy"), width="stretch")

    st.markdown("#### Wykryte anomalie")
    base_cols = [c for c in raw_df.columns]
    extra_cols = ["Anomaly_IF", "Anomaly_LOF", "Anomaly_SVM",
                  "Anomaly_Votes", "Has_Outlier"]
    for c in ["Nagla_Zmiana", "Odstaje_Od_Innych", "Rodzaj_Anomalii"]:
        if c in res.columns:
            extra_cols.append(c)
    show_cols = base_cols + extra_cols
    st.dataframe(res[res["Anomaly_Final"] == 1][show_cols], width="stretch")

    Narzedzia.przycisk_pobierania(
        "Pobierz pelny wynik (CSV)", Narzedzia.to_csv_bytes(res),
        "wynik_anomalie.csv", "text/csv", key="pob_pelny")
    Narzedzia.przycisk_pobierania(
        "Pobierz same anomalie (CSV)", Narzedzia.to_csv_bytes(res[res["Anomaly_Final"] == 1]),
        "tylko_anomalie.csv", "text/csv", key="pob_anom")