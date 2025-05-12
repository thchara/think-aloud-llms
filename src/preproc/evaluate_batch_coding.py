import pandas as pd
from pyprojroot import here
from src.preproc.auto_checker import check_graph
from src.preproc.utils import run_code

if __name__ == "__main__":

    df = pd.read_csv(here("data/coded/fixed_trials_claude-3-haiku-20240307.csv"))

    df["graph"] = df["translation"].apply(run_code)
    df["n_problems"] = df["graph"].apply(lambda g: len(check_graph(g.G)))
    print(df["n_problems"])

    df.to_csv(here("data/coded/fixed_trials_claude-3-haiku-20240307.csv"), index=False)

    df_autochecker = pd.read_csv(
        here("data/autochecker_logs/autochecker_log_claude-3-haiku-20240307.csv")
    )

    print(df_autochecker["n_problems"].value_counts())
