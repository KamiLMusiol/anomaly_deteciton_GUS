import requests
import pandas as pd


class report_generator:

    @staticmethod
    def ask_mistral(prompt: str, model: str = "mistral") -> str:
        response = requests.post(
            "http://localhost:11434/api/generate", #domyslnie jezeli nikt nic nie zmienial w ustawieniach lla,y nie polceam
            json={"model": model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        return response.json()["response"]

    @staticmethod
    def generate_report(df: pd.DataFrame, max_chars: int = 12000) -> str: #ten prompt max_chart potem moze miec problem i ucinac
        focus_cols = [c for c in df.columns if any(
            key in c for key in ['rolling_mean', 'diff_prev', 'diff_from_rolling_mean',
                                 'zscore', 'is_outlier', 'Anomaly_', 'Has_Outlier']
        )]

        full_table_text = df.to_csv(index=True)

        if len(full_table_text) <= max_chars:
            table_text = full_table_text
            info = "Ponizej pelna tabela ze wszystkimi kolumnami." #info dla chata
        else:
            table_text = df[focus_cols].to_csv(index=True)
            info = "Tabela jest zbyt duza, ponizej tylko kluczowe kolumny (cechy anomalii i wyniki modeli)." #info dla chata

        prompt = (
            "Jestes analitykiem danych. Ponizej tabela z wynikami wykrywania anomalii.\n"
            f"{info}\n"
            "Kolumny to m.in. srednie kroczace, roznice od poprzedniej wartosci, z-score, "
            "flagi outlierow (IQR) oraz wyniki 3 modeli (Isolation Forest, LOF, One-Class SVM) "
            "i finalna decyzja (Anomaly_Final).\n\n"
            "Przeanalizuj tabele pod katem tych kolumn. Wskaz ktore wiersze sa najbardziej "
            "podejrzane i dlaczego, bazujac szczegolnie na roznicach od sredniej kroczacej, "
            "z-score oraz liczbie modeli ktore zaglosowaly na anomalie.\n\n"
            f"Tabela w formie csv:\n{table_text}"
        )

        return report_generator.ask_mistral(prompt)