import io

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from anomaly_d import anomaly_detector
from mistral_raport_generator import report_generator

st.set_page_config(page_title="detekcja anomalii", page_icon=None, layout="wide")

MAX_PLOT_POINTS = 5000  # powyzej tego wykresy liniowe sa probkowane, zeby nie zamulic UI

# opis z-score uzywany w kilku miejscach, zeby byl wszedzie taki sam
ZSCORE_HELP = (
    "Z-score mowi o ile odchylen standardowych dana wartosc odstaje od sredniej calej kolumny. "
    "0 = dokladnie srednia, 1 = jedno odchylenie powyzej, -2 = dwa odchylenia ponizej. "
    "Umownie |z| > 3 uznaje sie za wartosc nietypowa. "
    "Uwaga: srednia i odchylenie sa liczone z calej kolumny, wiec pojedyncza skrajna wartosc "
    "potrafi zawyzyc odchylenie i zaniżyc z-score pozostalych wierszy."
)

# paleta w stylu Excel/GUS - granat, zielen, szarosci
COL_PRIMARY = "#1F4E79"
COL_ACCENT = "#217346"
COL_ANOM = "#C00000"
COL_GRID = "#D9D9D9"
COL_TEXT = "#333333"


# ---------------------------------------------------------------- wyglad

def apply_style():
    """Bialy, kanciasty motyw zblizony do Excela i publikacji GUS."""

    st.markdown(
        """
        <style>
        /* Deploy i reszta opcji deweloperskich sa juz ukryte przez
        [client] toolbarMode = "viewer" w .streamlit/config.toml */

        /* zwijanie sidebara psulo sie (strzalka do przywrocenia znikala
        razem z paskiem Deploy) - prosciej jest w ogole zablokowac
        mozliwosc zwiniecia, sidebar zostaje zawsze widoczny.
        Bez ograniczenia do konkretnego tagu, bo w skompilowanym froncie
        ten sam data-testid moze byc na wrapperze, nie na <button> */
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] * { display: none !important; }

        /* wszystko kanciaste - zero zaokraglen */
        .stApp *, .stApp *::before, .stApp *::after { border-radius: 0 !important; }

        section[data-testid="stSidebar"] {
            border-right: 1px solid #BFBFBF;
        }

        h1, h2, h3, h4 { color: #1F4E79; font-weight: 700; }
        h1 { border-bottom: 3px solid #1F4E79; padding-bottom: 6px; }

        /* zakladki jak w arkuszu kalkulacyjnym */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 1px solid #BFBFBF;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #F2F2F2;
            border: 1px solid #BFBFBF;
            border-bottom: none;
            margin-right: 2px;
            padding: 6px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            border-top: 3px solid #1F4E79;
            font-weight: 700;
        }

        /* przyciski */
        .stButton button, .stDownloadButton button {
            border: 1px solid #1F4E79;
            font-weight: 600;
        }
        .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
            background-color: #1F4E79;
            border: 1px solid #16375A;
        }

        /* pola tekstowe i liczbowe */
        .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
            border: 1px solid #8C8C8C;
        }

        /* metryki jak komorki arkusza */
        div[data-testid="stMetric"] {
            background-color: #F2F2F2;
            border: 1px solid #BFBFBF;
            padding: 10px;
        }
        div[data-testid="stMetricValue"] {
            color: #1F4E79;
            font-variant-numeric: tabular-nums;
        }

        /* tabele */
        div[data-testid="stDataFrame"] { border: 1px solid #BFBFBF; }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_style()


# ---------------------------------------------------------------- pomocnicze

def clamp(value, low, high, default):
    """Puste pole -> domyslna wartosc. Za male / za duze -> najblizsza dopuszczalna."""
    if value is None:
        return default, False
    if value < low:
        return low, True
    if value > high:
        return high, True
    return value, False


def num_field(label, low, high, default, step, key, help=None, is_int=True):
    """Pole liczbowe bez suwaka. Bez min/max na widgecie, zeby dalo sie wpisac
    cokolwiek - wartosc jest potem przycinana do dopuszczalnego zakresu."""
    raw = st.number_input(
        label,
        value=None,
        step=step,
        key=key,
        placeholder=f"domyslnie {default} (zakres {low}-{high})",
        help=help,
    )
    value, clamped = clamp(raw, low, high, default)
    if clamped:
        st.caption(f"Wartosc poza zakresem {low}-{high} - uzyto {value}.")
    return int(value) if is_int else float(value)


def axis_fields(key_prefix, cols=4):
    """Cztery pola: X od/do, Y od/do. Puste = zakres automatyczny."""
    with st.expander("Zakres osi (puste = automatycznie)"):
        c1, c2, c3, c4 = st.columns(cols)
        x_min = c1.number_input("X od", value=None, key=f"{key_prefix}_xmin", placeholder="auto")
        x_max = c2.number_input("X do", value=None, key=f"{key_prefix}_xmax", placeholder="auto")
        y_min = c3.number_input("Y od", value=None, key=f"{key_prefix}_ymin", placeholder="auto")
        y_max = c4.number_input("Y do", value=None, key=f"{key_prefix}_ymax", placeholder="auto")
    return x_min, x_max, y_min, y_max


def apply_axis(ax, limits):
    """Nakłada recznie wpisane zakresy. None zostawia wartosc automatyczna."""
    x_min, x_max, y_min, y_max = limits
    if x_min is not None or x_max is not None:
        cur = ax.get_xlim()
        ax.set_xlim(x_min if x_min is not None else cur[0],
                    x_max if x_max is not None else cur[1])
    if y_min is not None or y_max is not None:
        cur = ax.get_ylim()
        ax.set_ylim(y_min if y_min is not None else cur[0],
                    y_max if y_max is not None else cur[1])
    return ax


def get_ollama_models():
    """Lista modeli sciagnietych lokalnie w Ollamie."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3) #modele jakie ollama ma powinny byc minumum 4 w readme napisane jakie
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])] #wraca po porstu wszytkie dostepne modele

    except Exception:
        return []


def downsample(df, max_points=MAX_PLOT_POINTS):
    """Co n-ty wiersz, zeby wykres liniowy pozostal czytelny i szybki."""
    if len(df) <= max_points:
        return df, 1
    step = len(df) // max_points + 1
    return df.iloc[::step], step #ma skakac co step wiersz


def to_csv_bytes(df):
    buf = io.StringIO() #wirtualny plik tekstowy
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8") #zamienia na surowe bajty


PLOT_LAYOUT = dict(  # wspolny wyglad wszystkich wykresow - bialy, kanciasty, jak w arkuszu
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color=COL_TEXT, size=12),
    title_font=dict(color=COL_PRIMARY, size=14),
    margin=dict(l=50, r=20, t=50, b=45),
    hoverlabel=dict(bgcolor="white", bordercolor=COL_PRIMARY, font_size=12),
    legend=dict(bordercolor="#8C8C8C", borderwidth=1),
)

AXIS_STYLE = dict(showgrid=True, gridcolor=COL_GRID, gridwidth=1,
                  linecolor="#8C8C8C", linewidth=1, mirror=True, ticks="outside")


def style_fig(fig, title, x_title=None, y_title=None, limits=None, height=420):
    """Nadaje wspolny wyglad i nakłada recznie wpisane zakresy osi."""
    fig.update_layout(title=title, height=height, **PLOT_LAYOUT)
    fig.update_xaxes(title_text=x_title, **AXIS_STYLE)
    fig.update_yaxes(title_text=y_title, **AXIS_STYLE)
    if limits:
        x_min, x_max, y_min, y_max = limits
        if x_min is not None or x_max is not None:
            fig.update_xaxes(range=[x_min, x_max])
        if y_min is not None or y_max is not None:
            fig.update_yaxes(range=[y_min, y_max])
    return fig


def show(fig):
    """Jedno miejsce na ustawienia paska narzedzi Plotly."""
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


def fig_line(df, cols, title, limits=None):
    fig = go.Figure()
    for c in cols:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[c], name=c, mode="lines",
            line=dict(width=1.6),
            hovertemplate=f"<b>{c}</b><br>wiersz %{{x}}<br>wartosc %{{y}}<extra></extra>",
        ))
    return style_fig(fig, title, "indeks wiersza", None, limits)


def fig_hist(df, col, bins, limits=None):
    fig = go.Figure(go.Histogram(
        x=df[col].dropna(), nbinsx=int(bins), marker_color=COL_PRIMARY,
        marker_line=dict(color="white", width=1),
        hovertemplate="przedzial %{x}<br>liczba wierszy %{y}<extra></extra>",
    ))
    return style_fig(fig, f"Histogram: {col}", col, "liczba wierszy", limits)


def fig_box(df, cols, limits=None):
    fig = go.Figure()
    for c in cols:
        fig.add_trace(go.Box(y=df[c].dropna(), name=c, marker_color=COL_PRIMARY,
                             boxpoints="outliers"))
    return style_fig(fig, "Boxplot (rozklad i outliery IQR)", None, None, limits)


def fig_corr(df, cols):
    corr = df[cols].corr()
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=cols, y=cols, zmin=-1, zmax=1, colorscale="RdYlGn",
        text=corr.round(2).values, texttemplate="%{text}",
        hovertemplate="%{y} vs %{x}<br>korelacja %{z:.3f}<extra></extra>",
    ))
    fig = style_fig(fig, "Korelacje miedzy kolumnami", None, None, None, height=520)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


def anom_hover(anom, col, extra_cols):
    """Buduje tekst dymka dla anomalii - wartosc plus kontekst z innych kolumn."""
    linie = []
    for i in anom.index:
        czesci = [f"<b>wiersz {i}</b>", f"{col}: {anom.loc[i, col]}"]
        for c in extra_cols:
            if c in anom.columns:
                v = anom.loc[i, c]
                if isinstance(v, float):
                    v = round(v, 3)
                czesci.append(f"{c}: {v}")
        linie.append("<br>".join(czesci))
    return linie


def fig_rolling_anom(df, col, limits=None):
    plot_df, step = downsample(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df[col], name=col, mode="lines",
        line=dict(color=COL_PRIMARY, width=1.6),
        hovertemplate=f"wiersz %{{x}}<br>{col} %{{y}}<extra></extra>",
    ))
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
            text=anom_hover(anom, col, ["Anomaly_Votes", "Has_Outlier",
                                        f"{col}_zscore", "Rodzaj_Anomalii"]),
            hovertemplate="%{text}<extra></extra>",
        ))
    tytul = f"{col} - wartosc vs srednia kroczaca" + (f" (co {step}. punkt)" if step > 1 else "")
    return style_fig(fig, tytul, "indeks wiersza", col, limits)


def fig_zscore_anom(df, col, threshold=3.0, limits=None):
    plot_df, _ = downsample(df)  # co ktoras wartosc dla klarownosci
    zc = f"{col}_zscore"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df[zc], name="z-score", mode="markers",
        marker=dict(color=COL_PRIMARY, size=5, symbol="square"),
        hovertemplate=f"wiersz %{{x}}<br>z-score %{{y:.2f}}<extra></extra>",
    ))
    anom = df[df["Anomaly_Final"] == 1]  # prawdziwa anomalia
    if len(anom) > 0:
        fig.add_trace(go.Scatter(
            x=anom.index, y=anom[zc], name="anomalia", mode="markers",
            marker=dict(color=COL_ANOM, size=10, symbol="square"),
            text=anom_hover(anom, col, [zc, "Anomaly_Votes", "Has_Outlier", "Rodzaj_Anomalii"]),
            hovertemplate="%{text}<extra></extra>",
        ))
    for y in (threshold, -threshold):
        fig.add_hline(y=y, line=dict(color="#8C8C8C", width=1, dash="dash"))
    fig.add_annotation(x=1, xref="paper", y=threshold, text=f"prog +/-{threshold}",
                       showarrow=False, font=dict(size=10, color="#8C8C8C"),
                       xanchor="right", yanchor="bottom")
    return style_fig(fig, f"{col} - z-score", "indeks wiersza", "z-score", limits)


def fig_grupy(df, col, group_col, time_col, jednostki, limits=None):
    """Szeregi czasowe kilku jednostek na jednym wykresie, z zaznaczonymi anomaliami."""
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
            text=anom_hover(anom, col, [group_col, "Anomaly_Votes",
                                        "Nagla_Zmiana", "Odstaje_Od_Innych", "Rodzaj_Anomalii"]),
            hovertemplate="%{text}<extra></extra>",
        ))
    return style_fig(fig, f"{col} wedlug jednostek", str(time_col), col, limits, height=480)


def fig_votes(df, limits=None):
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
    return style_fig(fig, "Liczba wykrytych anomalii per model", None, "liczba wierszy", limits)


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
    return style_fig(fig, "Glowna przyczyna anomalii wg kolumny", None, "liczba anomalii", limits)


# ---------------------------------------------------------------- state

for key in ["raw_df", "result_df", "num_cols", "report"]:
    st.session_state.setdefault(key, None)

# stan generowania raportu partiami (zeby dalo sie je zatrzymac)
st.session_state.setdefault("gen_trwa", False)
st.session_state.setdefault("gen_indeks", 0)
st.session_state.setdefault("gen_czesci", [])
st.session_state.setdefault("gen_model", None)
st.session_state.setdefault("historia_pytan", [])


# ---------------------------------------------------------------- sidebar

st.sidebar.title("Detekcja anomalii")
uploaded = st.sidebar.file_uploader("Wgraj plik CSV lub Excel", type=["csv", "xlsx", "xls"])

if uploaded is not None:
    excel = uploaded.name.lower().endswith((".xlsx", ".xls"))

    if excel:
        # Z pliku Excel bierzemy TYLKO PIERWSZY arkusz. Kolejne sa ignorowane -
        # zwykle sa to zestawienia pomocnicze o innej strukturze, ktorych nie da sie
        # analizowac razem z pierwszym.
        try:
            arkusze = pd.ExcelFile(uploaded).sheet_names
            st.sidebar.caption(f"Arkusz: {arkusze[0]}")
            if len(arkusze) > 1:
                pominiete = ", ".join(map(str, arkusze[1:]))
                st.sidebar.info(f"Plik ma {len(arkusze)} arkuszy. Wczytany zostanie tylko "
                                f"pierwszy ('{arkusze[0]}'). Pominiete: {pominiete}.")
        except Exception as e:
            st.sidebar.error(f"Nie udalo sie odczytac arkuszy: {e}")

        wiersz_naglowka = st.sidebar.number_input(
            "Wiersz z naglowkami", min_value=1, value=1, step=1,
            help="Numer wiersza z nazwami kolumn. Ustaw wiecej niz 1, jesli arkusz "
                 "zaczyna sie tytulem lub pustymi wierszami.",
        )
        sep = None
    else:
        sep = st.sidebar.selectbox("Separator", [",", ";", "\t", "|"], index=0)
        wiersz_naglowka = 1

    if st.sidebar.button("Wczytaj plik", type="primary", width="stretch"):
        try:
            if excel:
                st.session_state.raw_df = pd.read_excel(
                    uploaded, sheet_name=0, header=int(wiersz_naglowka) - 1)
            else:
                st.session_state.raw_df = pd.read_csv(uploaded, sep=sep)

            # kolumny bez nazwy (puste naglowki w Excelu) tylko przeszkadzaja
            st.session_state.raw_df = st.session_state.raw_df.loc[
                :, ~st.session_state.raw_df.columns.astype(str).str.startswith("Unnamed:")]

            st.session_state.result_df = None
            st.session_state.report = None
            st.sidebar.success(f"Wczytano {len(st.session_state.raw_df)} wierszy")
        except Exception as e:
            st.sidebar.error(f"Blad wczytywania: {e}")

if st.session_state.raw_df is not None:
    st.sidebar.divider() #zwykla linia
    st.sidebar.caption( #wyblakly tekst
        f"Wierszy: {len(st.session_state.raw_df)} | "
        f"Kolumn: {len(st.session_state.raw_df.columns)}"
    )


# ---------------------------------------------------------------- main

st.title("Wykrywanie anomalii w danych CSV")

if st.session_state.raw_df is None:
    st.info("Wgraj plik CSV w panelu po lewej, zeby zaczac.")
    st.stop()#zatrzymuje dlasze wykonanie skryptu

raw_df = st.session_state.raw_df
all_num_cols = list(raw_df.select_dtypes(include="number").columns)

if not all_num_cols:
    st.error("brak kolumn numerycznych - nie ma czego analizowac")
    st.stop()

tab_data, tab_explore, tab_detect, tab_anom, tab_report, tab_ask, tab_help = st.tabs(
    [" Dane", " Wykresy", " Detekcja", " Anomalie", " Raport", " Pytanie", " Dobre praktyki"]
)


# ------------------------------------------------- TAB: Dane
with tab_data:
    st.subheader("Podglad danych")
    st.dataframe(raw_df.head(200), width="stretch")

    c1, c2, c3 = st.columns(3) #dzieli pole na 3 rowne kolumny
    c1.metric("Wiersze", len(raw_df)) #duze kafelki - metryki
    c2.metric("Kolumny", len(raw_df.columns))
    c3.metric("Kolumny numeryczne", len(all_num_cols))

    st.subheader("Statystyki opisowe") #mniejszy naglowek
    st.dataframe(raw_df[all_num_cols].describe().T, width="stretch") #transponuje po porstu describa nazwy sa wierszami zamiast kolumnami

    braki = raw_df.isnull().sum()
    braki = braki[braki > 0]
    if len(braki) > 0:
        st.subheader("Braki danych")
        st.dataframe(braki.rename("liczba brakow"), width="stretch")
    else:
        st.success("Brak pustych wartosci w danych.")


# ------------------------------------------------- TAB: Wykresy
with tab_explore:
    st.subheader("Eksploracja danych")

    c1, c2, c3 = st.columns(3)
    with c1:
        row_from = num_field("Wiersz od", 0, len(raw_df) - 1, 0, 1, "row_from",
                             help="Ogranicz zakres, zeby przyjrzec sie fragmentowi duzego pliku.")
    with c2:
        row_to = num_field("Wiersz do", 1, len(raw_df), min(len(raw_df), 1000), 1, "row_to")
    with c3:
        bins = num_field("Liczba przedzialow (histogram)", 5, 200, 40, 1, "bins")

    if row_to <= row_from: #zabezpieczenie przed odwroconym zakresem
        st.caption(f"Koniec zakresu musi byc wiekszy od poczatku - uzyto {row_from + 1}.")
        row_to = row_from + 1

    view = raw_df.iloc[row_from:row_to]
    st.caption(f"Widok: wiersze {row_from}-{row_to} ({len(view)} z {len(raw_df)})")

    st.markdown("#### Wykres liniowy")
    line_cols = st.multiselect("Kolumny", all_num_cols, default=all_num_cols[:1], key="line_cols")
    if line_cols:
        lim_line = axis_fields("line")
        plot_view, step = downsample(view)
        if step > 1:
            st.caption(f"Bardzo duzo wartosci - wykres pokazuje co {step}. wiersz.")
        show(fig_line(plot_view, line_cols, "Przebieg wartosci", lim_line))
        st.caption("Najedz na punkt, zeby zobaczyc wartosc. Kolko myszy przybliza, przeciaganie przesuwa.")
    else:
        st.info("Wybierz przynajmniej jedna kolumne.")

    st.markdown("#### Histogram")
    hist_col = st.selectbox("Kolumna", all_num_cols, key="hist_col")
    lim_hist = axis_fields("hist")
    show(fig_hist(view, hist_col, bins, lim_hist))

    st.markdown("#### Boxplot")
    box_cols = st.multiselect("Kolumny", all_num_cols, default=all_num_cols[:4], key="box_cols")
    if box_cols:
        lim_box = axis_fields("box")
        show(fig_box(view, box_cols, lim_box))

    if len(all_num_cols) > 1:
        st.markdown("#### Korelacje")
        show(fig_corr(view, all_num_cols))


# ------------------------------------------------- TAB: Detekcja
with tab_detect:
    st.subheader("Detekcja anomalii")

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
        window = num_field("Okno sredniej kroczacej", 2, max(len(raw_df), 2), 10, 1, "window",
                           help="Ile ostatnich wierszy wchodzi do sredniej kroczacej. "
                                "W trybie szeregow czasowych - ile ostatnich okresow danej jednostki.")
    with c2:
        contamination = num_field("Oczekiwany odsetek anomalii", 0.01, 0.30, 0.05, 0.01,
                                  "contamination", is_int=False,
                                  help="Zakladany udzial anomalii w danych. Modele tna wynik "
                                       "dokladnie na tym progu, wiec przy 0.05 kazdy model wskaze "
                                       "okolo 5 procent wierszy niezaleznie od tego ile anomalii "
                                       "jest naprawde.")
    with c3:
        fast_svm = st.checkbox("Szybki SVM", value=True,
                               help="SGDOneClassSVM zamiast OneClassSVM. Przy duzych plikach "
                                    "klasyczny SVM liczy sie bardzo dlugo.")

    st.caption(
        "Kolejnosc wierszy jest traktowana jako kolejnosc w czasie - srednia kroczaca ma sens tylko dla danych posortowanych chronologicznie. "

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

    if st.session_state.result_df is not None:
        res = st.session_state.result_df
        st.success(f"Gotowe. Wykryto {int(res['Anomaly_Final'].sum())} anomalii "
                   f"na {len(res)} wierszy.")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Isolation Forest", int(res["Anomaly_IF"].sum()))
        c2.metric("LOF", int(res["Anomaly_LOF"].sum()))
        c3.metric("One-Class SVM", int(res["Anomaly_SVM"].sum()))
        c4.metric("Finalnie (>=2/3)", int(res["Anomaly_Final"].sum()))

        if "Rodzaj_Anomalii" in res.columns: #tylko tryb szeregow czasowych
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

        st.download_button(
            "Pobierz pelny wynik (CSV)",
            to_csv_bytes(res),
            file_name="wynik_anomalie.csv",
            mime="text/csv",
        )
        st.download_button(
            "Pobierz same anomalie (CSV)",
            to_csv_bytes(res[res["Anomaly_Final"] == 1]),
            file_name="tylko_anomalie.csv",
            mime="text/csv",
        )


# ------------------------------------------------- TAB: Anomalie
with tab_anom:
    st.subheader("Wykresy anomalii")

    if st.session_state.result_df is None:
        st.info("Najpierw uruchom detekcje w zakladce 'Detekcja'.")
    else:
        res = st.session_state.result_df
        num_cols = st.session_state.num_cols

        lim_votes = axis_fields("votes")
        show(fig_votes(res, lim_votes))

        lim_per_col = axis_fields("per_col")
        f = fig_anom_per_col(res, num_cols, lim_per_col)
        if f is not None:
            show(f)

        st.divider()
        col = st.selectbox("Kolumna do analizy", num_cols, key="anom_col")

        if "Rodzaj_Anomalii" in res.columns: #tryb szeregow czasowych
            st.markdown("#### Szeregi wedlug jednostek")
            gcol = st.session_state.get("group_col")
            tcol = st.session_state.get("time_col")
            jednostki = sorted(res[gcol].astype(str).unique())
            wybrane = st.multiselect("Jednostki na wykresie", jednostki,
                                     default=jednostki[:6], key="wybrane_jednostki")
            if wybrane:
                lim_panel = axis_fields("panel")
                show(fig_grupy(res, col, gcol, tcol, wybrane, lim_panel))
            st.caption(
                "Kazda linia to jedna jednostka. Czerwone kwadraty to wiersze uznane za anomalie. "
                "Skok pojedynczej linii w gore lub w dol to nagla zmiana, a linia biegnaca "
                "caly czas z dala od pozostalych to odstawanie od reszty."
            )
            st.divider()

        lim_roll = axis_fields("roll")
        show(fig_rolling_anom(res, col, lim_roll))

        thr = num_field("Prog z-score", 1.0, 6.0, 3.0, 0.5, "thr", is_int=False,
                        help=ZSCORE_HELP)
        lim_z = axis_fields("zscore")
        show(fig_zscore_anom(res, col, thr, lim_z))
        st.caption("Najedz na kwadrat, zeby zobaczyc wartosc, z-score i liczbe glosow modeli.")
        st.caption(ZSCORE_HELP)


# ------------------------------------------------- TAB: Raport
with tab_report:
    st.subheader("Raport tekstowy (lokalny LLM)")

    if st.session_state.result_df is None:
        st.info("Najpierw uruchom detekcje w zakladce 'Detekcja'.")
    else:
        res = st.session_state.result_df
        n_anom = int(res["Anomaly_Final"].sum())

        if n_anom == 0:
            st.info("Nie wykryto anomalii - nie ma z czego zrobic raportu.")
        else:
            models = get_ollama_models()
            if not models:
                st.warning(
                    "Nie wykryto Ollamy na http://localhost:11434. "
                    "Uruchom `ollama serve` i sciagnij model (`ollama pull qwen3:8b`)."
                )
                models = ["qwen3:8b", "mistral-nemo", "mistral"]

            c1, c2 = st.columns(2)
            with c1:
                model = st.selectbox("Model", models, key="model_raport")
            with c2:
                partia = num_field("Anomalii na partie", 1, 100, 10, 1, "partia",
                                   help="Raport powstaje partiami. Po kazdej partii mozna "
                                        "przerwac - im mniejsza partia, tym szybciej "
                                        "zadziala przycisk zatrzymania.")

            st.caption(f"Raport obejmie wszystkie {n_anom} wykrytych anomalii, "
                       f"posortowanych wg liczby glosow i liczby flag outlier.")

            anomalie = (res[res["Anomaly_Final"] == 1]
                        .sort_values(["Anomaly_Votes", "Has_Outlier"], ascending=False))
            num_cols_r = st.session_state.num_cols

            b1, b2 = st.columns(2)
            with b1:
                if st.button("Generuj raport", type="primary",
                             disabled=st.session_state.gen_trwa):
                    st.session_state.gen_trwa = True
                    st.session_state.gen_indeks = 0
                    st.session_state.gen_czesci = []
                    st.session_state.gen_model = model
                    st.session_state.report = None
                    st.rerun()
            with b2:
                if st.button("Zatrzymaj", disabled=not st.session_state.gen_trwa):
                    st.session_state.gen_trwa = False
                    st.session_state.report = "\n\n".join(st.session_state.gen_czesci)
                    st.rerun()

            # Generowanie idzie partiami, po jednej na przebieg skryptu. Dzieki temu
            # miedzy partiami interfejs odzywa i przycisk zatrzymania faktycznie dziala -
            # przy jednym dlugim wywolaniu Streamlit bylby zablokowany do konca.
            if st.session_state.gen_trwa:
                i = st.session_state.gen_indeks
                paczka = anomalie.iloc[i:i + int(partia)]

                st.progress(min(i / n_anom, 1.0),
                            text=f"Opisano {i} z {n_anom} anomalii...")

                if len(paczka) == 0:
                    st.session_state.gen_trwa = False
                    st.session_state.report = "\n\n".join(st.session_state.gen_czesci)
                    st.rerun()
                else:
                    try:
                        czesc = report_generator.generate_report(
                            paczka, model=st.session_state.gen_model)
                        st.session_state.gen_czesci.append(czesc)
                        st.session_state.gen_indeks = i + int(partia)
                        st.rerun()
                    except Exception as e:
                        st.session_state.gen_trwa = False
                        st.error(f"Blad generowania raportu: {e}")

            if st.session_state.gen_czesci and not st.session_state.gen_trwa:
                opisano = min(st.session_state.gen_indeks, n_anom)
                if opisano < n_anom:
                    st.warning(f"Generowanie przerwane. Opisano {opisano} z {n_anom} anomalii.")
                else:
                    st.success(f"Gotowe. Opisano wszystkie {n_anom} anomalii.")

            if st.session_state.report:
                st.markdown("#### Raport")
                st.write(st.session_state.report)
                st.download_button(
                    "Pobierz raport (TXT)",
                    st.session_state.report.encode("utf-8"),
                    file_name="raport_anomalie.txt",
                    mime="text/plain",
                )


# ------------------------------------------------- TAB: Pytanie
with tab_ask:
    st.subheader("Zapytaj model o dane")

    if st.session_state.raw_df is None:
        st.info("Najpierw wgraj plik CSV.")
    else:
        models = get_ollama_models()
        if not models:
            st.warning(
                "Nie wykryto Ollamy na http://localhost:11434. "
                "Uruchom `ollama serve` i sciagnij model (`ollama pull qwen3:8b`)."
            )
            models = ["qwen3:8b", "mistral-nemo", "mistral"]

        model_q = st.selectbox("Model", models, key="model_pytanie")

        # jesli detekcja byla zrobiona, model dostaje tez informacje o anomaliach
        df_q = st.session_state.result_df if st.session_state.result_df is not None else raw_df
        num_cols_q = st.session_state.num_cols

        if st.session_state.result_df is None:
            st.caption("Detekcja nie zostala jeszcze uruchomiona - model widzi tylko "
                       "strukture i statystyki danych, bez informacji o anomaliach.")
        else:
            st.caption("Model widzi strukture danych, statystyki oraz wyniki detekcji anomalii.")

        with st.expander("Co dokladnie widzi model"):
            st.text(report_generator.build_data_context(df_q, num_cols_q))
            st.caption(
                "Model nie dostaje surowej tabeli, tylko powyzszy opis. Wszystkie liczby sa "
                "policzone w Pythonie, wiec nie moze ich przekrecic. Nie zna natomiast "
                "wartosci pojedynczych wierszy spoza listy najsilniejszych anomalii."
            )

        pytanie = st.text_area(
            "Pytanie",
            placeholder="np. Ktora kolumna najczesciej powoduje anomalie i jak silne sa odchylenia?",
            key="pytanie",
            height=90,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            zapytaj = st.button("Zapytaj", type="primary")
        with c2:
            if st.button("Wyczysc historie"):
                st.session_state.historia_pytan = []
                st.rerun()

        if zapytaj:
            if not pytanie.strip():
                st.error("Wpisz pytanie.")
            else:
                with st.spinner(f"Modell odpowiada ({model_q})..."):
                    try:
                        odp = report_generator.ask_about_data(
                            df_q, pytanie, num_cols_q, model=model_q,
                            historia=st.session_state.historia_pytan,
                        )
                        st.session_state.historia_pytan.append((pytanie, odp))
                    except Exception as e:
                        st.error(f"Blad: {e}")

        if st.session_state.historia_pytan:
            st.markdown("#### Rozmowa")
            for pyt, odp in reversed(st.session_state.historia_pytan): #najnowsze na gorze
                st.markdown(f"**Pytanie:** {pyt}")
                st.write(odp)
                st.divider()

            rozmowa_txt = "\n\n".join(
                f"PYTANIE: {p}\n\nODPOWIEDZ: {o}" for p, o in st.session_state.historia_pytan)
            st.download_button(
                "Pobierz rozmowe (TXT)",
                rozmowa_txt.encode("utf-8"),
                file_name="pytania_o_dane.txt",
                mime="text/plain",
            )


# ------------------------------------------------- TAB: Dobre praktyki
with tab_help:
    st.subheader("Dobre praktyki i interpretacja wynikow")

    with st.expander("1. Jak przygotowac plik CSV przed wgraniem", expanded=True):
        st.markdown("""
**Posortuj dane chronologicznie.** To najwazniejsza rzecz. Aplikacja traktuje kolejnosc
wierszy jako kolejnosc w czasie - srednie kroczace i roznice miedzy wierszami licza sie
wzgledem sasiadow w pliku. Na danych posortowanych losowo te cechy beda szumem, a nie
sygnalem. Jesli masz kolumne z data lub znacznikiem czasu, posortuj po niej przed
zapisaniem pliku.

**Usun kolumny-identyfikatory.** Numery porzadkowe, ID transakcji, numery klienta - to
liczby, wiec aplikacja potraktuje je jako kolumny numeryczne i policzy dla nich z-score
oraz srednie kroczace. Wynik jest bezuzyteczny (rosnacy licznik zawsze wyglada jak
idealny trend), a dodatkowo takie kolumny psuja modele, bo wnosza do nich sztuczny
wymiar. Jesli musisz zachowac identyfikator do pozniejszego dopasowania wynikow,
zamien go na tekst - kolumny tekstowe sa pomijane w obliczeniach, ale zostaja w tabeli
wynikowej i w eksporcie CSV.

**Sprawdz separator i format liczb.** Aplikacja pozwala wybrac separator kolumn
(przecinek, srednik, tabulator, pionowa kreska), ale separator dziesietny musi byc
kropka. Plik z liczbami w formacie `1 234,56` zostanie wczytany jako tekst i kolumna
wypadnie z analizy.

**Zdecyduj co zrobic z brakami danych.** Puste komorki sa wypelniane zerem przed
podaniem do modeli. Jesli zero jest w twoich danych sensowna wartoscia (na przyklad
kwota), braki zostana potraktowane jako prawdziwe zera i moga zaburzyc wynik. Lepiej
uzupelnic je swiadomie przed wgraniem albo usunac takie wiersze.

**Jedna tabela, jeden typ zdarzenia.** Nie laczaj w jednym pliku danych o roznej
charakterystyce (na przyklad transakcji detalicznych i hurtowych). Modele ucza sie
"co jest normalne" z calego zbioru naraz - wymieszanie dwoch rozkladow sprawi, ze
mniejszy z nich w calosci zostanie uznany za anomalie.

**Minimalny rozmiar.** Ponizej okolo 100 wierszy wyniki sa malo wiarygodne. LOF
porownuje gestosc z sasiadami, a przy kilkudziesieciu punktach kazdy jest sasiadem
kazdego. Kwartyle do flag IQR tez sa wtedy bardzo niestabilne.
        """)

    with st.expander("2. Kolejnosc pracy w aplikacji"):
        st.markdown("""
**Krok 1 - zakladka Dane.** Zanim cokolwiek policzysz, sprawdz czy plik wczytal sie
poprawnie. Zwroc uwage na liczbe kolumn numerycznych - jesli jest mniejsza niz
oczekujesz, ktoras kolumna zostala wczytana jako tekst (zwykle przez przecinek
dziesietny albo spacje w liczbach). Sprawdz tez braki danych.

**Krok 2 - zakladka Wykresy.** Obejrzyj dane przed detekcja. Histogram pokaze ci
ksztalt rozkladu, boxplot od razu ujawni wartosci skrajne, a wykres liniowy pokaze
czy dane maja jakis trend lub sezonowosc. Na tym etapie czesto widac oczywiste bledy
danych - ujemne kwoty, niemozliwe wieki, wartosci sto razy wieksze od reszty.

**Krok 3 - zakladka Detekcja.** Ustaw parametry i uruchom. Zacznij od wartosci
domyslnych, potem doreguluj.

**Krok 4 - zakladka Anomalie.** Sprawdz czy wynik ma sens. To najwazniejszy etap
weryfikacji - opisany nizej.

**Krok 5 - zakladka Raport.** Dopiero gdy wyniki wygladaja sensownie, generuj opis
tekstowy. Generowanie trwa najdluzej z calego procesu, wiec nie ma sensu robic tego
na parametrach, ktore i tak bedziesz zmieniac.
        """)

    with st.expander("3. Jak dobrac parametry"):
        st.markdown("""
**Okno sredniej kroczacej.** Okresla, jak dlugi fragment historii jest traktowany jako
"lokalna norma". Male okno (5-10) reaguje szybko na zmiany i wychwytuje nagle skoki.
Duze okno (50-200) wygladza dane i pokazuje odstepstwa od dluzszego trendu. Jesli twoje
dane maja naturalny cykl - na przyklad dobowy albo tygodniowy - warto ustawic okno
zblizone do dlugosci tego cyklu.

**Oczekiwany odsetek anomalii.** To zalozenie, nie wynik pomiaru. Modele przytna wynik
dokladnie na tym progu, wiec przy 0.05 kazdy z nich wskaze okolo 5 procent wierszy -
nawet jesli dane sa idealnie czyste. Zacznij od 0.05, obejrzyj wykres z-score
w zakladce Anomalie i doreguluj:

- oznaczone anomalie maja z-score bliski zeru - obniz parametr, model dopycha wynik
  do zadanego procentu z normalnych wierszy
- cos ewidentnie odstajacego zostalo pominiete - podnies parametr

Dla wykrywania oszustw realistyczne wartosci to 0.01-0.02, bo prawdziwe naduzycia sa
rzadkie. Dla wykrywania bledow w danych czy awarii czujnikow moze byc wyzej.

**Szybki SVM.** Zostaw wylaczony dla plikow do kilkunastu tysiecy wierszy - roznica
w czasie jest znikoma, a dokladnosc wyraznie lepsza. Wlacz dopiero, gdy detekcja
zaczyna trwac niewygodnie dlugo.
        """)

    with st.expander("4. Jak czytac wyniki - zakladka Detekcja"):
        st.markdown("""
**Metryki per model.** Cztery liczby pod przyciskiem detekcji pokazuja, ile wierszy
wskazal kazdy model osobno i ile przeszlo finalne glosowanie.

Jesli jeden model wskazuje radykalnie wiecej niz pozostale, to sygnal ze wykryl cos
innego niz reszta - nie ze sie myli. Kazdy z trzech patrzy na dane inaczej:

- **Isolation Forest** szuka punktow, ktore latwo oddzielic od reszty losowymi
  podzialami. Dobrze radzi sobie z wartosciami skrajnymi w pojedynczych kolumnach.
- **LOF** porownuje lokalna gestosc punktu z gestoscia jego sasiadow. Wychwytuje
  anomalie kontekstowe - wartosc sama w sobie zwyczajna, ale nietypowa w swoim
  otoczeniu.
- **One-Class SVM** rysuje granice wokol obszaru uznanego za normalny. Reaguje na
  ogolny ksztalt rozkladu.

**Finalna liczba jest zwykle mniejsza niz pozostale trzy.** To normalne i zamierzone -
wymaga zgody przynajmniej dwoch modeli, wiec odsiewa przypadki, ktore tylko jeden
uznal za podejrzane.

**Tabela anomalii.** Kolumna `Anomaly_Votes` mowi ile modeli zaglosowalo (2 albo 3).
Wiersze z trzema glosami sa pewniejsze. Kolumna `Has_Outlier` mowi w ilu kolumnach
wiersz jest jednoczesnie statystycznym outlierem IQR - wysoka wartosc oznacza, ze
wiersz odstaje na wielu wymiarach naraz.
        """)

    with st.expander("5. Jak czytac wyniki - zakladka Anomalie"):
        st.markdown("""
**Wykres glosow modeli.** Sluzy do oceny, czy modele sie ze soba zgadzaja. Podobne
slupki oznaczaja spojna ocene danych. Jeden slupek wyraznie wyzszy oznacza, ze ten
model jest bardziej czuly na charakterystyke twoich danych - warto wtedy sprawdzic,
ktore wiersze wskazuje tylko on.

**Glowna przyczyna anomalii wg kolumny.** Pokazuje, w ktorej kolumnie najczesciej lezy
zrodlo problemu (kolumna o najwyzszej wartosci bezwzglednej z-score w danym wierszu).
Jesli jedna kolumna zdecydowanie dominuje, warto sie zastanowic, czy to naprawde
anomalie, czy po prostu ta kolumna ma inna skale albo rozklad niz reszta.

**Wykres sredniej kroczacej.** Najbardziej intuicyjny obraz. Niebieska linia to
wartosci, zielona przerywana to lokalna norma, czerwone kwadraty to anomalie. Szukaj
miejsc, gdzie niebieska linia gwaltownie odrywa sie od zielonej. Jesli czerwone punkty
leza tam, gdzie obie linie ida rownolegle - model prawdopodobnie zareagowal na inna
kolumne niz aktualnie ogladana.

**Wykres z-score.** Pokazuje, jak bardzo wartosci odstaja od sredniej calej kolumny,
w jednostkach odchylenia standardowego. Przerywane linie to prog, domyslnie 3.

Na co zwrocic uwage:

- czerwone punkty **powyzej progu** - anomalie potwierdzone tez statystycznie,
  najpewniejsze przypadki
- czerwone punkty **przy zerze** - model wykryl je z innego powodu niz wartosc w tej
  kolumnie, sprawdz inne kolumny w liscie rozwijanej
- **wszystkie punkty scisniete przy zerze, jeden bardzo wysoko** - klasyczny objaw
  pojedynczej ekstremalnej wartosci, ktora zawyzyla odchylenie standardowe i przez to
  splaszczyla z-score wszystkich pozostalych wierszy

**Uwaga o roznicy miedzy z-score a flaga IQR.** Wartosc moze miec bardzo wysoki
z-score, a mimo to nie byc oznaczona jako outlier IQR - albo odwrotnie. To nie blad.
Z-score opiera sie na sredniej i odchyleniu standardowym, ktore sa wrazliwe na
pojedyncze skrajne wartosci. IQR opiera sie na kwartylach, ktore sa na nie odporne.
Rozbieznosc miedzy tymi dwiema miarami sama w sobie jest informacja.
        """)

    with st.expander("6. Jak czytac raport tekstowy"):
        st.markdown("""
**Wszystkie liczby w raporcie sa liczone w Pythonie, nie przez model jezykowy.** Model
dostaje gotowe fakty i ma je tylko sformulowac w plynne zdania. To swiadoma decyzja
projektowa - male modele lokalne mylily numeracje wierszy i przypisywaly wartosci do
zlych kolumn, gdy dostawaly do analizy surowa tabele.

W praktyce oznacza to, ze **liczbom w raporcie mozna ufac**, natomiast sformulowania
moga sie roznic miedzy modelami i uruchomieniami.

**Raport obejmuje tylko najsilniejsze anomalie** - domyslnie 20, sortowanych wedlug
liczby glosow i liczby flag outlier. To limit wydajnosciowy: kazda anomalia to osobny
tekst do wygenerowania, a przy setkach wierszy trwaloby to minuty. Pelna liste zawsze
masz w tabeli i w eksporcie CSV.
        """)

    with st.expander("7. Czego aplikacja nie robi"):
        st.markdown("""
**Nie odrozni bledu danych od prawdziwej anomalii.** Wiek 999 i nietypowo duza
transakcja beda potraktowane tak samo - jako wartosci odstajace. Rozroznienie wymaga
wiedzy o dziedzinie i nalezy do ciebie.

**Nie wie, co jest wazne w twoich danych.** Modele nie maja pojecia, ze kolumna
z kwota jest istotniejsza niz kolumna z numerem tygodnia. Wszystkie kolumny numeryczne
traktowane sa rownorzednie - dlatego warto usunac przed wgraniem te, ktore nie niosa
informacji.

**Nie wykrywa anomalii, ktorych nie widac w liczbach.** Jesli oszustwo polega na
zwyklej kwocie o zwyklej porze, ale na koncie nalezacym do kogos innego, zadne z tych
narzedzi tego nie zauwazy.

**Nie zastepuje weryfikacji przez czlowieka.** Wynik to lista wierszy do sprawdzenia,
a nie werdykt. Czesc wskazan zawsze bedzie falszywymi alarmami - to wpisane w sposob
dzialania tych metod, nie usterka.
        """)