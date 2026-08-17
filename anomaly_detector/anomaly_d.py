import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.linear_model import SGDOneClassSVM
from sklearn.preprocessing import StandardScaler


class anomaly_detector:

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

    @staticmethod
    def run_models(df: pd.DataFrame, contamination: float = 0.05, fast_svm: bool = False) -> pd.DataFrame:
        """
        fast_svm=True uzywa SGDOneClassSVM (liniowa zlozonosc) zamiast OneClassSVM (kwadratowa).
       bardzo duzych ilosci wierszy klasyczny OneClassSVM potrafi liczyc minutami, zmienic najwyzej
        """
        X = df.select_dtypes(include=[np.number]).fillna(0)
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



    #sprawdza czy dany wiersz mial jakikowielk outlier oraz leci z modelami i innymi kolumnami
    @staticmethod
    def detect(df: pd.DataFrame, window: int = 10, contamination: float = 0.05,
               fast_svm: bool = True, feature_cols=None, group_col=None, time_col=None):
        """Pelny pipeline na gotowym DataFrame. Zwraca (df_z_wynikami, num_cols)."""
        df = df.copy()
        num_cols = list(df.select_dtypes(include=[np.number]).columns)
        if len(num_cols) == 0:
            raise ValueError("Plik nie zawiera kolumn numerycznych.")

        df = anomaly_detector.add_stat_features(df, num_cols)
        df = anomaly_detector.add_rolling_features(df, num_cols, window=window)
        df = anomaly_detector.add_outlier_flags(df, num_cols)
        df = anomaly_detector.run_models(df, contamination=contamination, fast_svm=fast_svm)

        outlier_columns = [c for c in df.columns if c.endswith('_is_outlier')]
        df['Has_Outlier'] = df[outlier_columns].sum(axis=1)
        return df, num_cols

    #czyta i dodaje kolumny z pomoca metody
    @staticmethod
    def read_csv_add_features_and_model(file_path="test.csv", srednia_korczaca: int = 10,
                                        contamination: float = 0.05, fast_svm: bool = True):
        """Wersja wczytujaca prosto z pliku (zgodna ze starym uzyciem)."""
        df = pd.read_csv(file_path)
        df, num_cols = anomaly_detector.detect(df, window=srednia_korczaca,
                                               contamination=contamination, fast_svm=fast_svm)
        return df, num_cols