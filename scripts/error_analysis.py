"""
Analyze the number of errors in coding for each model.
"""

import os
from numpy import full
import pandas as pd
from plotnine import *
from src.analysis.errors import get_error_df
from pyprojroot import here
import argparse

MODELS = [
    "deepseek-v3-0324",
    "claude-3-5-sonnet-20241022",
    "llama-v3p1-8b-instruct",
    "llama-v3p3-70b-instruct",
    "llama4-maverick-instruct-basic",
    "llama4-scout-instruct-basic",
    "qwen3-235b-a22b",
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment_name", type=str, default="full-experiment")
    args = parser.parse_args()
    EXPERIMENT_NAME = args.experiment_name

    all_problem_dfs = []
    ns_failed = {}
    df_trials_raw = pd.read_csv(
        here(f"data/processed/full-experiment/full-experiment-trials.csv")
    )

    for model in MODELS:
        full_coded_filepath = here(
            f"data/coded/{EXPERIMENT_NAME}/{EXPERIMENT_NAME}_model-{model}.csv"
        )
        # read the full coded file
        if os.path.exists(full_coded_filepath):
            df_coded = pd.read_csv(full_coded_filepath)
            if EXPERIMENT_NAME == "irr":
                df_coded["practice"] = False
                df_coded["relevant"] = 1
                df_coded["pid"] = None

            df_problems = get_error_df(df_trials_raw, df_coded)
            df_problems["model"] = model
            all_problem_dfs.append(df_problems)
            ns_failed[model] = df_problems["failed_to_run"].sum()

    print(f"Number of codes that failed to run:\n{ns_failed}")

    df_all_problems = pd.concat(all_problem_dfs, ignore_index=True).fillna(0)
    df_all_problems.to_csv(
        here(f"data/analysis/{EXPERIMENT_NAME}-errors.csv"),
        index=False,
    )
