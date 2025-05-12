"""
Utilities to help with error analysis.
"""

import re
import numpy as np
import pandas as pd
from collections import defaultdict
from src.preproc.utils import run_code
from src.preproc.auto_checker import check_graph

error_names = {
    "Operation runnability from curr_state.": "runnability_errors",
    "Resulting state calculation error.": "state_calculation_errors",
}


def count_error_types(errors):
    """
    Count the number of errors of each type.
    """
    if errors is None or len(errors) == 0:
        return {}

    problem_type_counts = defaultdict(int)
    for error in errors:
        problems = error["Problems"]
        for problem in problems:
            problem_type = re.search(r"PROBLEM TYPE: (.+) DESCRIPTION:", problem).group(
                1
            )
            problem_type_counts[error_names[problem_type]] += 1

    problem_type_counts = dict(problem_type_counts)
    problem_type_counts["total_errors"] = sum(problem_type_counts.values())
    return problem_type_counts


def get_error_df(df_trials_raw, df_coded):
    """
    Get a dataframe with the number of errors per participant.
    """

    # first, apply exclusions to get df_coded_proc
    participants_to_exclude = (
        df_trials_raw.copy()
        # remove practice trials
        .query("not practice")
        # calculate percentage of relevant trials per participants
        .assign(
            relevant_ratio=lambda df: df.groupby("pid")["relevant"].transform("mean"),
        )
        # find participants with 0.5 or below relevant ratio
        .query("relevant_ratio <= 0.5")
        # get unique participant ids
        .pid.unique()
    )

    df_coded_proc = (
        df_coded.copy()
        # remove practice trials
        .query("not practice")
        # remove trials from a single condition that had the same problem that was included as practice
        .query("choices != '[1,1,2,6]'")
        # calculate trial index
        .assign(
            trial_index=lambda df: df.groupby("pid").cumcount() + 1,
        )
        # remove participants in exclusion list
        .query("pid not in @participants_to_exclude")
        # remove irrelevant trials
        .query("relevant == 1")
        # trials that went over 3 minutes and one second due to lag must be set to 0.0 and the response column set to nan
        .assign(
            response=lambda df: df["response"].where(
                cond=df["rt_s"] <= 181, other=np.nan
            )
        )
        # reset index
        .reset_index(drop=True)
    )

    # run the code
    df_coded_proc["graph"] = df_coded_proc["lm_code_translation"].apply(run_code)
    df_coded_proc["failed_to_run"] = df_coded_proc["graph"].apply(
        lambda x: isinstance(x, str)
    )

    df_coded_proc["errors"] = df_coded_proc["graph"].apply(
        lambda x: check_graph(x) if not isinstance(x, str) else None
    )

    problem_rows = list(df_coded_proc["errors"].apply(count_error_types))
    df_problems = pd.DataFrame(problem_rows).fillna(0)
    df_problems["failed_to_run"] = df_coded_proc["failed_to_run"]
    df_problems = df_problems.reset_index(names="trial_index")

    return df_problems
