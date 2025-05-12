import numpy as np
import pandas as pd
from os import listdir
from tqdm import tqdm

if __name__ == "__main__":

    # Get all the files in the data directory
    data_dir = "/scr/verbal-protocol/data/full-experiment"
    files = listdir(data_dir)
    condition_rows = []
    for file in tqdm(files):
        # Load the file
        df = pd.read_csv(f"{data_dir}/{file}")

        # get the first row
        first_row = df.iloc[0:1]
        condition_info = first_row[["CONDITION", "TYPE"]]
        condition_rows.append(condition_info)

    df_conditions = pd.concat(condition_rows)

    df_counts = df_conditions.value_counts().reset_index()
    print(f"total count: {df_counts['count'].sum()}")
    df_counts["n_needed"] = df_counts.apply(
        lambda x: 32 - x["count"] if x["TYPE"] == 1 else 20 - x["count"], axis=1
    )

    n_batches_left = 1
    print(f"total still needed: {df_counts['n_needed'].sum()}")
    df_counts["n_needed_one_batch"] = np.ceil(
        df_counts["n_needed"] / n_batches_left
    ).astype(int)
    print(df_counts.columns)
    df_counts = df_counts.sort_values(by=["TYPE", "CONDITION"], ascending=[False, True])
    print(df_counts)
