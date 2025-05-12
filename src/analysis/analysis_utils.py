"""
Utilities to help with analyzing the coded, featurized data.
"""

import pandas as pd
import numpy as np
from tqdm import tqdm
from src.preproc.reasoning_graph import GraphBuilder
from ast import literal_eval


### graph edit distance ###
def compute_normalized_ged(unnormalized_ged, graph1, graph2):
    if isinstance(graph1, str) or isinstance(graph2, str) or unnormalized_ged is None:
        return 1  # maximal ged if one of the graphs is invalid

    max_node_count = max(len(graph1.G.nodes()), len(graph2.G.nodes()))
    max_edge_count = max(len(graph1.G.edges()), len(graph2.G.edges()))

    return unnormalized_ged / (max_node_count + max_edge_count)


### hypothesis testing ###


def compute_item_correlation(df_group1: pd.DataFrame, df_group2: pd.DataFrame) -> float:
    """
    Compute item-level correlation between two groups.

    Args:
        df_group1: DataFrame for first group
        df_group2: DataFrame for second group

    Returns:
        correlation: Pearson correlation coefficient between group means by choices
    """
    # Compute mean accuracy for each problem type in group 1
    group1_means = (
        df_group1.groupby("choices")["correct"]
        .mean()
        .reset_index()
        .rename(columns={"correct": "group1_mean"})
    )

    # Compute mean accuracy for each problem type in group 2
    group2_means = (
        df_group2.groupby("choices")["correct"]
        .mean()
        .reset_index()
        .rename(columns={"correct": "group2_mean"})
    )

    # Merge the means on choices
    combined = group1_means.merge(group2_means, on="choices")

    # Calculate correlation
    correlation = combined["group1_mean"].corr(combined["group2_mean"])

    return correlation


### graph utils ###
def count_operations(graph: GraphBuilder):
    """Count the number of each operation type in the graph."""
    operations = {"+": 0, "-": 0, "*": 0, "/": 0}

    for _, _, data in graph.G.edges(data=True):
        operation = data.get("operation", "")
        if "=" in operation:  # Only look at the part before the equals sign
            operation = operation[: operation.find("=")]

        # Count each operator in the operation
        for op in operations.keys():
            operations[op] += operation.count(op)

    return operations


def classify_subgoal_state(subgoal_state):
    if len(subgoal_state) == 1:
        return "single"
    elif len(subgoal_state) == 2:
        if subgoal_state[0] * subgoal_state[1] == 24:
            return "product"
        elif subgoal_state[0] + subgoal_state[1] == 24:
            return "sum"
        elif (
            subgoal_state[0] - subgoal_state[1] == 24
            or subgoal_state[1] - subgoal_state[0] == 24
        ):
            return "difference"
        elif (
            subgoal_state[0] / subgoal_state[1] == 24
            or subgoal_state[1] / subgoal_state[0] == 24
        ):
            return "quotient"
        else:
            return "other"
    else:
        return "other"


def within_problem_permutation_test(
    df,
    rng,
    dep_var="correct",
    n_permutations=10000,
):
    """
    A hierarchical permutation test that respects the trial structure of the data
    """
    # Get observed statistic
    condition_means = df.groupby("condition")[dep_var].mean()
    observed_stat = condition_means["noVP"] - condition_means["VP"]

    problems = df["choices"].unique()
    problem_masks = {}
    for problem in problems:
        problem_masks[problem] = df["choices"] == problem
    permuted_stats = []

    for _ in tqdm(range(n_permutations)):
        shuffled_df = df.copy()
        for problem in problems:
            problem_mask = problem_masks[problem]
            problem_rows = shuffled_df.loc[problem_mask]
            shuffled_conditions = rng.permutation(problem_rows["condition"].values)
            shuffled_df.loc[problem_mask, "condition"] = shuffled_conditions

        # Compute permuted stat
        problem_diffs_perm = shuffled_df.groupby("condition")[dep_var].mean()
        stat = (problem_diffs_perm["noVP"] - problem_diffs_perm["VP"]).mean()
        permuted_stats.append(stat)

    permuted_stats = np.array(permuted_stats)

    # Compute two-tailed p-value
    p_value = np.mean(np.abs(permuted_stats) >= np.abs(observed_stat))

    return observed_stat, p_value


def requires_division(problem):
    """
    Check if a problem requires division.
    """
    for solution in [f"Solution {i}" for i in range(1, 12)]:
        if pd.isna(problem[solution]):
            break
        if "/" not in problem[solution]:
            return False
    return True


def count_divisions(graph: GraphBuilder):
    """
    Count the number of operations in a graph that involve division.
    """
    divisions = 0
    G = graph.G
    for edge in G.edges():
        op = G.edges[edge]["operation"]
        if "/" in op:
            divisions += 1
    return divisions
