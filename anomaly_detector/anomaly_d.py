import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

class anomaly_detector:


    @staticmethod
    def add_rolling_features(df: pd.DataFrame, num_cols, window: int = 10) -> pd.DataFrame:
        for col in num_cols:
            df[f'{col}_rolling_mean'] = df[col].rolling(window=window, min_periods=1).mean()
            df[f'{col}_rolling_std'] = df[col].rolling(window=window, min_periods=1).std().fillna(0)
            df[f'{col}_diff_prev'] = df[col].diff().fillna(0)
            df[f'{col}_diff_from_rolling_mean'] = df[col] - df[f'{col}_rolling_mean'] #srednia kroczaca

        return df

    @staticmethod
    def read_csv_add_features_and_model(file_path = test.csv, srednia_korczaca:int = 10):
        df = pd.read_csv(file_path)
        num_cols = df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            mean_val = df[col].mean()
            std_val = df[col].std()

            # Odchylenie od średniej
            df[f'{col}_diff_mean'] = df[col] - mean_val
            # Z-score
            df[f'{col}_zscore'] = np.where(std_val == 0, 0, df[f'{col}_diff_mean'] / std_val)


        df = anomaly_detector.add_rolling_features(df, num_cols, window=srednia_korczaca) #na 10 standard mozna sie pobawic
        df = anomaly_detector.add_outlier_flags(df, num_cols)
        X = df.select_dtypes(include=[np.number]).fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)


        iso = IsolationForest(contamination=0.05, random_state=42)
        lof = LocalOutlierFactor(contamination=0.05)
        ocsvm = OneClassSVM(nu=0.05)


        # 0 norma 1 anomalia latwiej manipuuje
        df['Anomaly_IF'] = (iso.fit_predict(X_scaled) == -1).astype(int)
        df['Anomaly_LOF'] = (lof.fit_predict(X_scaled) == -1).astype(int)
        df['Anomaly_SVM'] = (ocsvm.fit_predict(X_scaled) == -1).astype(int)

        df['Anomaly_Final'] = ((df['Anomaly_IF'] + df['Anomaly_LOF'] + df['Anomaly_SVM']) >= 2).astype(int)

        outlier_columns = [c for c in df.columns if c.endswith('_is_outlier')]
        df['Has_Outlier'] = df[outlier_columns].sum(axis=1)

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

