"""
Wszystkie wykresy aplikacji, zrobione w Plotly (interaktywne - przyblizanie,
przesuwanie, dymki po najechaniu).

Kazda metoda buduje jeden wykres i zwraca gotowy obiekt figury - nie
wywoluje sama st.plotly_chart, to robi Wykresy.show() w zakladce, zeby
mozna bylo w jednym miejscu ustawic pasek narzedzi.
"""

import plotly.graph_objects as go
import streamlit as st

from frontend_streamlit.styles import COL_PRIMARY, COL_ACCENT, COL_ANOM, PLOT_LAYOUT, AXIS_STYLE
from frontend_streamlit.narzedzia import Narzedzia


class Wykresy:
    """Cala fabryka wykresow - kazda metoda to jeden typ wykresu. Statyczne,
    bo nie trzymamy tu zadnego stanu, tylko budujemy figury na zadanie.
    leci to tak rodzaj wykresy -> style -> show
    """

    @staticmethod
    def style_fig(fig, title, x_title=None, y_title=None, limits=None, height=420):
        """Nadaje wspolny wyglad i naklada recznie wpisane zakresy osi."""
        fig.update_layout(title=title, height=height, **PLOT_LAYOUT)  # tytul wysokosc i ustawienia globalne z gory
        fig.update_xaxes(title_text=x_title, **AXIS_STYLE)
        fig.update_yaxes(title_text=y_title, **AXIS_STYLE)
        if limits:
            x_min, x_max, y_min, y_max = limits
            if x_min is not None or x_max is not None:
                fig.update_xaxes(range=[x_min, x_max])
            if y_min is not None or y_max is not None:
                fig.update_yaxes(range=[y_min, y_max])
        return fig

    @staticmethod
    def show(fig):
        """Jedno miejsce na ustawienia paska narzedzi Plotly."""
        st.plotly_chart(fig, use_container_width=True,
                        config={"displaylogo": False,
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})

    @staticmethod
    def anom_hover(anom, col, extra_cols): #anom to df, col to kolumna extra to sa extra kolumny do opisania
        """Buduje tekst dymka dla anomalii - wartosc plus kontekst z innych kolumn."""
        linie = []  # gotowe teksty dymkow
        for i in anom.index:
            czesci = [f"<b>wiersz {i}</b>", f"{col}: {anom.loc[i, col]}"]  # wiersz i wartosc z kolumny
            for c in extra_cols:  # petla przez dodatkowe kolumny
                if c in anom.columns:
                    v = anom.loc[i, c]
                    if isinstance(v, float):
                        v = round(v, 3)  # czytelnosc
                    czesci.append(f"{c}: {v}")
            linie.append("<br>".join(czesci))
        return linie

    @staticmethod
    def fig_line(df, cols, title, limits=None):
        """interaktywny wykres liniowy dla wybranych kolumn"""
        fig = go.Figure()  # z plotly wykres liniowy
        for c in cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], name=c, mode="lines",
                line=dict(width=1.6),
                hovertemplate=f"<b>{c}</b><br>wiersz %{{x}}<br>wartosc %{{y}}<extra></extra>",
            ))  # dodaje do wykresu nowa serie danych punktowo liniowych
        return Wykresy.style_fig(fig, title, "indeks wiersza", None, limits)

    @staticmethod
    def fig_hist(df, col, bins, limits=None):
        """histogram"""
        fig = go.Figure(go.Histogram(
            x=df[col].dropna(), nbinsx=int(bins), marker_color=COL_PRIMARY,
            marker_line=dict(color="white", width=1),
            hovertemplate="przedzial %{x}<br>liczba wierszy %{y}<extra></extra>",  # dymek po najechaniu tooltip
        ))
        return Wykresy.style_fig(fig, f"Histogram: {col}", col, "liczba wierszy", limits)

    @staticmethod
    def fig_box(df, cols, limits=None):
        """boxplot"""
        fig = go.Figure()
        for c in cols:
            fig.add_trace(go.Box(y=df[c].dropna(), name=c, marker_color=COL_PRIMARY,
                                 boxpoints="outliers"))
        return Wykresy.style_fig(fig, "Boxplot (rozklad i outliery IQR)", None, None, limits)

    @staticmethod
    def fig_corr(df, cols):
        """korelacja"""
        corr = df[cols].corr()
        fig = go.Figure(go.Heatmap(
            z=corr.values, x=cols, y=cols, zmin=-1, zmax=1, colorscale="RdYlGn",
            text=corr.round(2).values, texttemplate="%{text}",
            hovertemplate="%{y} vs %{x}<br>korelacja %{z:.3f}<extra></extra>",
        ))
        fig = Wykresy.style_fig(fig, "Korelacje miedzy kolumnami", None, None, None, height=520)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        return fig

    @staticmethod
    def fig_rolling_anom(df, col, limits=None):
        """limits to bylo xmin ymin itp"""
        plot_df, step = Narzedzia.downsample(df)  # aktualnie zero manualnie
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[col], name=col, mode="lines",
            line=dict(color=COL_PRIMARY, width=1.6),
            hovertemplate=f"wiersz %{{x}}<br>{col} %{{y}}<extra></extra>",
        ))  # linia wartosci
        if f"{col}_rolling_mean" in df.columns:
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[f"{col}_rolling_mean"], name="srednia kroczaca",
                mode="lines", line=dict(color=COL_ACCENT, width=1.6, dash="dash"),
                hovertemplate="wiersz %{x}<br>srednia %{y:.2f}<extra></extra>",
            ))
        anom = df[df["Anomaly_Final"] == 1]  # RYSUJE czerwone kwadraty tam gdzie jest anomalia
        if len(anom) > 0:
            fig.add_trace(go.Scatter(
                x=anom.index, y=anom[col], name="anomalia", mode="markers",
                marker=dict(color=COL_ANOM, size=9, symbol="square"),
                text=Wykresy.anom_hover(anom, col, ["Anomaly_Votes", "Has_Outlier",
                                            f"{col}_zscore", "Rodzaj_Anomalii"]),
                hovertemplate="%{text}<extra></extra>",
            ))  # te czerwone kwadraty pokazujace wykryte anomalie
        tytul = f"{col} - wartosc vs srednia kroczaca" + (f" (co {step}. punkt)" if step > 1 else "")
        return Wykresy.style_fig(fig, tytul, "indeks wiersza", col, limits)

    @staticmethod
    def fig_zscore_anom(df, col, threshold=3.0, limits=None):
        plot_df, _ = Narzedzia.downsample(df)  # co ktoras wartosc dla klarownosci
        zc = f"{col}_zscore"  # konwencja nazewnicza - kazda kolumna ma to po analizie
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[zc], name="z-score", mode="markers",  # indeks i wartosc tego guana
            marker=dict(color=COL_PRIMARY, size=5, symbol="square"),
            hovertemplate=f"wiersz %{{x}}<br>z-score %{{y:.2f}}<extra></extra>",
        ))  # to po prostu pokazuje te niebieskie kwadraty z score dla wszystkiego
        anom = df[df["Anomaly_Final"] == 1]  # prawdziwa anomalia
        if len(anom) > 0:  # niech bedzie wiecej niz 0 anomalii
            fig.add_trace(go.Scatter(
                x=anom.index, y=anom[zc], name="anomalia", mode="markers",
                marker=dict(color=COL_ANOM, size=10, symbol="square"),
                text=Wykresy.anom_hover(anom, col, [zc, "Anomaly_Votes", "Has_Outlier", "Rodzaj_Anomalii"]),
                hovertemplate="%{text}<extra></extra>",
            ))
        for y in (threshold, -threshold):
            fig.add_hline(y=y, line=dict(color="#8C8C8C", width=1, dash="dash"))
        fig.add_annotation(x=1, xref="paper", y=threshold, text=f"prog +/-{threshold}",
                           showarrow=False, font=dict(size=10, color="#8C8C8C"),
                           xanchor="right", yanchor="bottom")
        return Wykresy.style_fig(fig, f"{col} - z-score", "indeks wiersza", "z-score", limits)

    @staticmethod
    def fig_grupy(df, col, group_col, time_col, jednostki, limits=None):
        """Szeregi czasowe kilku jednostek na jednym wykresie, z zaznaczonymi anomaliami.
        group_col to kolumna z jednostki"""
        fig = go.Figure()
        for j in jednostki:
            sub = df[df[group_col].astype(str) == str(j)].sort_values(time_col)
            fig.add_trace(go.Scatter(
                x=sub[time_col], y=sub[col], name=str(j), mode="lines+markers",
                line=dict(width=1.6), marker=dict(size=5, symbol="square"),
                hovertemplate=f"<b>{j}</b><br>%{{x}}<br>{col} %{{y}}<extra></extra>",
            ))
        anom = df[(df["Anomaly_Final"] == 1) &
                  (df[group_col].astype(str).isin([str(x) for x in jednostki]))]
        if len(anom) > 0:
            fig.add_trace(go.Scatter(
                x=anom[time_col], y=anom[col], name="anomalia", mode="markers",
                marker=dict(color=COL_ANOM, size=14, symbol="square-open", line=dict(width=2.5)),
                text=Wykresy.anom_hover(anom, col, [group_col, "Anomaly_Votes",
                                            "Nagla_Zmiana", "Odstaje_Od_Innych", "Rodzaj_Anomalii"]),
                hovertemplate="%{text}<extra></extra>",
            ))
        return Wykresy.style_fig(fig, f"{col} wedlug jednostek", str(time_col), col, limits, height=480)

    @staticmethod
    def fig_votes(df, limits=None):
        """barchart slupki dla wynikow modeli, do podgladu"""
        counts = {
            "Isolation Forest": int(df["Anomaly_IF"].sum()),
            "LOF": int(df["Anomaly_LOF"].sum()),
            "One-Class SVM": int(df["Anomaly_SVM"].sum()),
            "Final (>=2/3)": int(df["Anomaly_Final"].sum()),
        }
        fig = go.Figure(go.Bar(
            x=list(counts.keys()), y=list(counts.values()),
            marker_color=[COL_PRIMARY] * 3 + [COL_ANOM],
            marker_line=dict(color="#8C8C8C", width=1),
            text=list(counts.values()), textposition="outside",
            hovertemplate="%{x}<br>wykryl %{y} wierszy<extra></extra>",
        ))
        return Wykresy.style_fig(fig, "Liczba wykrytych anomalii per model", None, "liczba wierszy", limits)

    @staticmethod
    def fig_anom_per_col(df, num_cols, limits=None):
        """Ile anomalii ma glowna przyczyne w danej kolumnie (najwyzszy |z-score|)."""
        anom = df[df["Anomaly_Final"] == 1]
        if len(anom) == 0:
            return None
        zcols = [f"{c}_zscore" for c in num_cols if f"{c}_zscore" in df.columns]
        main = anom[zcols].abs().idxmax(axis=1).str.replace("_zscore", "", regex=False)
        counts = main.value_counts()
        fig = go.Figure(go.Bar(
            x=list(counts.index), y=list(counts.values), marker_color=COL_ACCENT,
            marker_line=dict(color="#8C8C8C", width=1),
            text=list(counts.values), textposition="outside",
            hovertemplate="kolumna %{x}<br>%{y} anomalii<extra></extra>",
        ))
        return Wykresy.style_fig(fig, "Glowna przyczyna anomalii wg kolumny", None, "liczba anomalii", limits)
