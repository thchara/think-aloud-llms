from re import A
import pandas as pd
from pyprojroot import here
import submitit
import networkx as nx
from src.preproc.utils import unnormalized_graph_edit_distance, run_code
from argparse import ArgumentParser
import time
import os


def intersection_heuristic(G1, G2):
    """
    An upper bound on graph edit distance: you can always delete things from G1 until you get to the intersection, then add the things missing from G2 to the intersection.
    """
    G_intersection = nx.intersection(G1, G2)

    n_node_deletions = len(G1.nodes()) - len(G_intersection.nodes())
    n_node_additions = len(G2.nodes()) - len(G_intersection.nodes())

    n_edge_deletions = len(G1.edges()) - len(G_intersection.edges())
    n_edge_additions = len(G2.edges()) - len(G_intersection.edges())

    return n_node_deletions + n_node_additions + n_edge_deletions + n_edge_additions


def node_match_fn(x, y):
    return x["state"] == y["state"]


def compute_ged_with_heuristic(G1, G2, timeout):
    """
    Compute the GED between two graphs using the intersection heuristic as an upper bound.
    """
    if isinstance(G1, str) or isinstance(G2, str):
        return None, False

    heuristic = intersection_heuristic(G1.G, G2.G)
    if heuristic == 0:
        return 0, False

    start_time = time.time()
    ged = nx.graph_edit_distance(
        G1.G,
        G2.G,
        node_match=node_match_fn,
        timeout=timeout,
        upper_bound=heuristic,
    )
    end_time = time.time()
    time_taken = end_time - start_time

    timed_out = time_taken >= timeout

    if heuristic < ged:
        print(f"heuristic less than ged: {heuristic} < {ged}")

    print(f"ged: {ged}, heuristic: {heuristic}")
    return min(ged, heuristic), timed_out


slurm_params = {
    "name": "compute_geds",
    "slurm_account": "cocoflops",
    "slurm_partition": "cocoflops",
    "slurm_nodelist": "cocoflops2",
    "nodes": 1,
    "tasks_per_node": 1,
    "cpus_per_task": 1,
    "slurm_mem": "4G",
    "slurm_time": "12:00:00",
}


def submit_model_jobs(model, timeout):
    """
    Create submitit jobs for a given model.
    """
    print(f"Submitting jobs for model: {model}")
    df = pd.read_csv(here(f"data/coded/irr/irr_model-{model}.csv"))

    df["ben_graph"] = df["ben_annotation"].apply(run_code)
    df["ced_graph"] = df["ced_annotation"].apply(run_code)
    df["model_graph"] = df["lm_code_translation"].apply(run_code)

    executor = submitit.AutoExecutor(folder=here("scripts/submitit"))
    executor.update_parameters(**slurm_params)

    df["ben_ged_job"] = df.apply(
        lambda row: executor.submit(
            compute_ged_with_heuristic,
            row["ben_graph"],
            row["model_graph"],
            timeout=timeout,
        ),
        axis=1,
    )

    df["ced_ged_job"] = df.apply(
        lambda row: executor.submit(
            compute_ged_with_heuristic,
            row["ced_graph"],
            row["model_graph"],
            timeout=timeout,
        ),
        axis=1,
    )

    df["model"] = model
    return df


def submit_human_jobs(timeout):
    print("Submitting human jobs...")
    df = pd.read_csv(here("data/manual-coded/irr-trials.csv"))

    df["ben_graph"] = df["ben_annotation"].apply(run_code)
    df["ced_graph"] = df["ced_annotation"].apply(run_code)

    executor = submitit.AutoExecutor(folder=here("scripts/submitit"))
    executor.update_parameters(**slurm_params)

    df["human_ged_job"] = df.apply(
        lambda row: executor.submit(
            compute_ged_with_heuristic,
            row["ben_graph"],
            row["ced_graph"],
            timeout=timeout,
        ),
        axis=1,
    )

    df["model"] = "human"
    return df


def collect_model_results(df):
    """Collect results from submitted jobs for a given model."""
    print(f"Collecting results for model: {df['model'].iloc[0]}")

    ben_model_results = df["ben_ged_job"].apply(lambda job: job.result())
    df["ben_model_ged"] = [res[0] for res in ben_model_results]
    df["ben_model_timed_out"] = [res[1] for res in ben_model_results]

    ced_model_results = df["ced_ged_job"].apply(lambda job: job.result())
    df["ced_model_ged"] = [res[0] for res in ced_model_results]
    df["ced_model_timed_out"] = [res[1] for res in ced_model_results]

    # drop the results, since we don't need them anymore
    return df.drop(columns=["ben_ged_job", "ced_ged_job"])


def collect_human_results(df):
    """Collect results from submitted jobs for the human model."""

    human_results = df["human_ged_job"].apply(lambda job: job.result())
    df["human_ged"] = [res[0] for res in human_results]
    df["human_timed_out"] = [res[1] for res in human_results]

    return df.drop(columns=["human_ged_job"])


IRR_MODELS = [
    "claude-3-5-sonnet-20241022",
    "llama-v3p1-8b-instruct",
    "llama-v3p3-70b-instruct",
    "deepseek-v3-0324",
    "llama4-maverick-instruct-basic",
    "llama4-scout-instruct-basic",
    "qwen3-235b-a22b",
]

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--timeout", type=float, default=1)
    parser.add_argument("--overwrite", default=False)
    parser.add_argument(
        "--results_filepath", default=here("data/coded/irr/irr_results.csv")
    )
    args = parser.parse_args()

    TIMEOUT = args.timeout * 60 * 60

    if os.path.exists(args.results_filepath):
        df_saved_results = pd.read_csv(args.results_filepath)

        irr_models_to_compute = []
        for model in IRR_MODELS:
            if model not in df_saved_results["model"].unique() or args.overwrite:
                irr_models_to_compute.append(model)
                df_saved_results = df_saved_results.query(
                    "model != @model"
                )  # drop old results from df_saved_results

        if "human" not in df_saved_results["model"].unique() or args.overwrite:
            compute_human_ged = True
            df_saved_results = df_saved_results.query(
                "model != 'human'"
            )  # drop old results from df_saved_results
        else:
            compute_human_ged = False

    else:
        irr_models_to_compute = IRR_MODELS
        compute_human_ged = True

    all_new_result_dfs = []
    if irr_models_to_compute != []:
        print("Submitting model jobs...")
        model_dfs = [
            submit_model_jobs(model, TIMEOUT) for model in irr_models_to_compute
        ]
        print("Collecting model results...")
        all_new_result_dfs = [collect_model_results(df) for df in model_dfs]

    if compute_human_ged:
        print("Submitting human job...")
        human_df = submit_human_jobs(TIMEOUT)
        print("Collecting human results...")
        all_new_result_dfs.append(collect_human_results(human_df))

    print("Combining and saving results...")
    # combine all_new_result_dfs
    all_new_result_df = pd.concat(all_new_result_dfs, ignore_index=True)

    # drop the graphs since they'll just be saved as strings
    all_new_result_df.drop(
        columns=["ben_graph", "ced_graph", "model_graph"], inplace=True
    )

    # combine with saved results
    df_results = pd.concat([df_saved_results, all_new_result_df], ignore_index=True)

    # save results
    df_results.to_csv(args.results_filepath, index=False)
