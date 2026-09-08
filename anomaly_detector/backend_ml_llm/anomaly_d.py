import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.linear_model import SGDOneClassSVM
from sklearn.preprocessing import StandardScaler


class anomaly_detector:

    # ---------------------------------------------------------------- cechy klasyczne

    @staticmethod
    def add_rolling_features(df: pd.DataFrame, num_cols, window: int = 10) -> pd.DataFrame:
        for col in num_cols:
            df[f'{col}_rolling_mean'] = df[col].rolling(window=window, min_periods=1).mean()
            df[f'{col}_rolling_std'] = df[col].rolling(window=window, min_periods=1).std().fillna(0)
            df[f'{col}_diff_prev'] = df[col].diff().fillna(0)
            df[f'{col}_diff_from_rolling_mean'] = df[col] - df[f'{col}_rolling_mean']
        return df

    @staticmethod
    def add_outlier_flags(df: pd.DataFrame, num_cols) -> pd.DataFrame:
        for col in num_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            df[f'{col}_is_outlier'] = ((df[col] < lower_bound) | (df[col] > upper_bound)).astype(int)
        return df

    @staticmethod
    def add_stat_features(df: pd.DataFrame, num_cols) -> pd.DataFrame:
        for col in num_cols:
            mean_val = df[col].mean()
            std_val = df[col].std()
            df[f'{col}_diff_mean'] = df[col] - mean_val
            df[f'{col}_zscore'] = np.where(std_val == 0, 0, df[f'{col}_diff_mean'] / std_val)
        return df

    # ---------------------------------------------------------------- cechy dla szeregow czasowych

    @staticmethod
    def add_group_rolling_features(df: pd.DataFrame, num_cols, group_col, window: int = 10) -> pd.DataFrame:
        """Srednie kroczace i roznice liczone OSOBNO dla kazdego gospodarstwa.
        Bez tego srednia mieszalaby ze soba rozne gospodarstwa i byla bez sensu."""
        g = df.groupby(group_col, sort=False)
        for col in num_cols:
            df[f'{col}_rolling_mean'] = g[col].transform(
                lambda s: s.rolling(window=window, min_periods=1).mean())
            df[f'{col}_rolling_std'] = g[col].transform(
                lambda s: s.rolling(window=window, min_periods=1).std()).fillna(0)
            df[f'{col}_diff_prev'] = g[col].diff().fillna(0)  # zmiana wzgledem poprzedniego okresu tego samego gospodarstwa
            df[f'{col}_diff_from_rolling_mean'] = df[col] - df[f'{col}_rolling_mean']

            # nagla zmiana: o ile odchylen wlasnej historii skoczyla wartosc
            std_safe = df[f'{col}_rolling_std'].replace(0, np.nan)
            df[f'{col}_jump_score'] = (df[f'{col}_diff_from_rolling_mean'] / std_safe).fillna(0)
        return df

    @staticmethod
    def add_within_group_stats(df: pd.DataFrame, num_cols, group_col) -> pd.DataFrame:
        """Z-score wzgledem wlasnej historii gospodarstwa - czy wartosc jest nietypowa
        na tle tego, co to gospodarstwo zwykle raportuje."""
        g = df.groupby(group_col, sort=False)
        for col in num_cols:
            mean_g = g[col].transform("mean")
            std_g = g[col].transform("std").replace(0, np.nan)
            df[f'{col}_zscore_wlasny'] = ((df[col] - mean_g) / std_g).fillna(0)
        return df

    @staticmethod
    def add_cross_sectional_stats(df: pd.DataFrame, num_cols, time_col) -> pd.DataFrame:
        """Z-score wzgledem pozostalych gospodarstw W TYM SAMYM OKRESIE - czy gospodarstwo
        odstaje od reszty w danym momencie."""
        g = df.groupby(time_col, sort=False)
        for col in num_cols:
            mean_t = g[col].transform("mean")
            std_t = g[col].transform("std").replace(0, np.nan)
            df[f'{col}_zscore_miedzy'] = ((df[col] - mean_t) / std_t).fillna(0)
        return df

    # ---------------------------------------------------------------- modele

    @staticmethod
    def run_models(df: pd.DataFrame, feature_matrix_cols, contamination: float = 0.05,
                   fast_svm: bool = False) -> pd.DataFrame:
        """
        fast_svm=True uzywa SGDOneClassSVM (liniowa zlozonosc) zamiast OneClassSVM.

        UWAGA - domyslnie WYLACZONE. Wariant przyblizony okazal sie niestabilny:
        na jednym ze zbiorow testowych wykryl 0 anomalii (przy 25 z pozostalych
        dwoch modeli), a na innym ponad dwa razy za duzo. Model, ktory wskaze zero
        wierszy, w praktyce wypada z glosowania - wynik opiera sie wtedy na dwoch
        modelach zamiast trzech.

        Wariant dokladny na malych plikach jest rownie szybki (0,13 s wobec 0,15 s
        przy 500 wierszach), a przy 50 tys. wierszy wolniejszy okolo 2,5-krotnie
        (26 s wobec 10 s) - co nadal jest do przyjecia. Wlaczaj przyblizony tylko
        wtedy, gdy detekcja trwa niewygodnie dlugo.
        """
        X = df[feature_matrix_cols].replace([np.inf, -np.inf], 0).fillna(0)
        X_scaled = StandardScaler().fit_transform(X)

        iso = IsolationForest(contamination=contamination, random_state=42)
        lof = LocalOutlierFactor(contamination=contamination)
        if fast_svm:
            ocsvm = SGDOneClassSVM(nu=contamination, random_state=42)
        else:
            ocsvm = OneClassSVM(nu=contamination)

        # 0 = norma, 1 = anomalia
        df['Anomaly_IF'] = (iso.fit_predict(X_scaled) == -1).astype(int)
        df['Anomaly_LOF'] = (lof.fit_predict(X_scaled) == -1).astype(int)
        df['Anomaly_SVM'] = (ocsvm.fit_predict(X_scaled) == -1).astype(int)

        df['Anomaly_Votes'] = df['Anomaly_IF'] + df['Anomaly_LOF'] + df['Anomaly_SVM']
        df['Anomaly_Final'] = (df['Anomaly_Votes'] >= 2).astype(int)
        return df

    # ---------------------------------------------------------------- rodzaj anomalii

    @staticmethod
    def add_anomaly_kind(df: pd.DataFrame, num_cols, prog: float = 2.0) -> pd.DataFrame:
        """Rozroznia dwa rodzaje anomalii w szeregach czasowych:
        - nagla zmiana wewnatrz gospodarstwa (jump_score)
        - odstawanie od innych gospodarstw w tym samym okresie (zscore_miedzy)"""
        jump_cols = [f'{c}_jump_score' for c in num_cols if f'{c}_jump_score' in df.columns]
        cross_cols = [f'{c}_zscore_miedzy' for c in num_cols if f'{c}_zscore_miedzy' in df.columns]

        df['Nagla_Zmiana'] = df[jump_cols].abs().max(axis=1) if jump_cols else 0.0
        df['Odstaje_Od_Innych'] = df[cross_cols].abs().max(axis=1) if cross_cols else 0.0

        nagla = df['Nagla_Zmiana'] > prog
        odstaje = df['Odstaje_Od_Innych'] > prog

        df['Rodzaj_Anomalii'] = np.select(
            [nagla & odstaje, nagla, odstaje],
            ["nagla zmiana + odstaje od innych", "nagla zmiana", "odstaje od innych"],
            default="brak wyraznego wzorca",
        )
        return df

    # ---------------------------------------------------------------- pipeline

    @staticmethod
    def detect(df: pd.DataFrame, window: int = 10, contamination: float = 0.05,
               fast_svm: bool = False, feature_cols=None,
               group_col=None, time_col=None):
        """
        Pelny pipeline. Zwraca (df_z_wynikami, num_cols).

        feature_cols - ktore kolumny numeryczne analizowac. None = wszystkie.
        group_col    - kolumna z identyfikatorem jednostki (np. gospodarstwo).
        time_col     - kolumna z okresem. Podanie obu wlacza tryb szeregow czasowych.
        """
        df = df.copy()
        all_num = list(df.select_dtypes(include=[np.number]).columns)

        # kolumny grupujace nie moga byc jednoczesnie analizowane
        wykluczone = {group_col, time_col} - {None}
        if feature_cols is None:
            num_cols = [c for c in all_num if c not in wykluczone]
        else:
            num_cols = [c for c in feature_cols if c not in wykluczone]

        if len(num_cols) == 0:
            raise ValueError("Nie wybrano zadnej kolumny numerycznej do analizy.")

        tryb_czasowy = group_col is not None and time_col is not None

        if tryb_czasowy:
            # Do liczenia cech kroczacych wiersze musza isc jednostka po jednostce,
            # ale plik wejsciowy jest zwykle ulozony chronologicznie (A, B, C, A, B, C...).
            # Zapamietujemy wiec pierwotna kolejnosc i na koncu ja przywracamy,
            # zeby numery wierszy w wyniku zgadzaly sie z plikiem zrodlowym.
            df['_kolejnosc'] = np.arange(len(df))
            df = df.sort_values([group_col, time_col]).reset_index(drop=True)
            df = anomaly_detector.add_group_rolling_features(df, num_cols, group_col, window)
            df = anomaly_detector.add_within_group_stats(df, num_cols, group_col)
            df = anomaly_detector.add_cross_sectional_stats(df, num_cols, time_col)
            df = anomaly_detector.add_stat_features(df, num_cols)   # z-score globalny, do wykresow
            df = anomaly_detector.add_outlier_flags(df, num_cols)

            sufiksy = ['_rolling_mean', '_rolling_std', '_diff_prev', '_diff_from_rolling_mean',
                       '_jump_score', '_zscore_wlasny', '_zscore_miedzy', '_is_outlier']
        else:
            df = anomaly_detector.add_stat_features(df, num_cols)
            df = anomaly_detector.add_rolling_features(df, num_cols, window)
            df = anomaly_detector.add_outlier_flags(df, num_cols)

            sufiksy = ['_diff_mean', '_zscore', '_rolling_mean', '_rolling_std',
                       '_diff_prev', '_diff_from_rolling_mean', '_is_outlier']

        # do modeli trafiaja tylko wybrane kolumny i ich cechy pochodne
        feature_matrix_cols = list(num_cols)
        for c in num_cols:
            feature_matrix_cols += [f'{c}{s}' for s in sufiksy if f'{c}{s}' in df.columns]

        df = anomaly_detector.run_models(df, feature_matrix_cols, contamination, fast_svm)

        outlier_columns = [c for c in df.columns if c.endswith('_is_outlier')]
        df['Has_Outlier'] = df[outlier_columns].sum(axis=1)

        if tryb_czasowy:
            df = anomaly_detector.add_anomaly_kind(df, num_cols)
            # powrot do kolejnosci z pliku wejsciowego
            df = df.sort_values('_kolejnosc').drop(columns='_kolejnosc').reset_index(drop=True)

        return df, num_cols

    @staticmethod
    def read_csv_add_features_and_model(file_path="test.csv", srednia_korczaca: int = 10,
                                        contamination: float = 0.05, fast_svm: bool = False,
                                        feature_cols=None, group_col=None, time_col=None):
        """Wersja wczytujaca prosto z pliku (zgodna ze starym uzyciem)."""
        df = pd.read_csv(file_path)
        return anomaly_detector.detect(df, window=srednia_korczaca,
                                       contamination=contamination, fast_svm=fast_svm,
                                       feature_cols=feature_cols,
                                       group_col=group_col, time_col=time_col)