#!/usr/bin/env python3
"""
Compute line-wise edit distance between two files.
"""
import numpy as np
import pandas as pd
from pyprojroot import here
import editdistance
from ast import literal_eval
import re


def bootstrap_mean(data, n_samples=1000):
    """Bootstrap the mean of a dataset"""
    means = []
    for _ in range(n_samples):
        sample = np.random.choice(data, len(data), replace=True)
        means.append(np.mean(sample))
    ci_lower = np.percentile(means, 2.5)
    ci_upper = np.percentile(means, 97.5)
    return np.mean(means), [ci_lower, ci_upper]


def sort_commutative(line):
    op = "+" if "+" in line else "*"
    operation = re.search(r"\d+[\*|\+]\d+", line).group(0)
    terms = sorted([int(x) for x in operation.split(op)])
    return re.sub(r"\d+[\*|\+]\d+", str(terms[0]) + op + str(terms[1]), line)


def preprocess_translation(raw):
    raw = raw.strip()
    lines = []
    for line in raw.split("\n"):
        if line.startswith("//"):
            continue
        if "[" in line and "]" in line and "uncodable" not in line:
            start_idx = line.index("[")
            end_idx = line.index("]")
            number_list = literal_eval(line[start_idx : end_idx + 1])
            line = line[:start_idx] + str(sorted(number_list)) + line[end_idx + 1 :]
        line = line.replace(":", "").replace(" ", "").lower()
        if "*" in line or "+" in line:
            line = sort_commutative(line)
        lines.append(line)
    return lines


def characterwise_edit_distance(a, b):
    a = "\n".join(preprocess_translation(a))
    b = "\n".join(preprocess_translation(b))
    return editdistance.eval(a, b) / max(len(a), len(b))


def linewise_edit_distance(a, b):
    """Edit distance, where each line of text is treated as a unit. Ignores comments and spaces"""
    # first, remove comments
    a = preprocess_translation(a)
    b = preprocess_translation(b)

    # then, compute edit distance
    return editdistance.eval(a, b) / max(len(a), len(b))


def main(args):

    # load the human data
    df_truth = pd.read_csv(here(args["ground_truth_filepath"]))
    print(df_truth.columns)
    df_truth = df_truth[
        df_truth.apply(lambda x: isinstance(x["human_DSL_translation"], str), axis=1)
    ]

    rows = []
    for model_name in args["model_names"]:

        # Read the translations for a particular model
        df_model = pd.read_csv(
            here(f"data/coded/countdown_val_model-{model_name}.csv")
        ).drop(columns=["human_DSL_translation"])

        df_merged = pd.merge(
            df_truth,
            df_model,
            on=["choices", "transcript"],
            how="inner",
        )

        # compute edit distances between human and LM translations
        df_merged["linewise_distance"] = df_merged.apply(
            lambda x: linewise_edit_distance(
                x["human_DSL_translation"], x["lm_DSL_translation"]
            ),
            axis=1,
        )

        df_merged["characterwise_distance"] = df_merged.apply(
            lambda x: characterwise_edit_distance(
                x["human_DSL_translation"], x["lm_DSL_translation"]
            ),
            axis=1,
        )

        mean_linewise, ci_linewise = bootstrap_mean(df_merged["linewise_distance"])
        mean_characterwise, ci_characterwise = bootstrap_mean(
            df_merged["characterwise_distance"]
        )

        print(
            f"model: {model_name}, linewise distance: {mean_linewise:.3f} ({ci_linewise[0]:.3f}, {ci_linewise[1]:.3f})\ncharacterwise distance: {mean_characterwise:.3f} ({ci_characterwise[0]:.3f}, {ci_characterwise[1]:.3f})"
        )

        for _, row in df_merged.iterrows():
            rows.append(
                {
                    "model": model_name,
                    "linewise_distance": row["linewise_distance"],
                    "characterwise_distance": row["characterwise_distance"],
                    "lm_DSL_translation": row["lm_DSL_translation"],
                    "human_DSL_translation": row["human_DSL_translation"],
                }
            )

    # Add the mean edit distances between human-human translations
    for i, row1 in df_truth.iterrows():
        for j, row2 in df_truth.iterrows():
            if i < j:
                linewise_distance = linewise_edit_distance(
                    row1["human_DSL_translation"], row2["human_DSL_translation"]
                )
                characterwise_distance = characterwise_edit_distance(
                    row1["human_DSL_translation"], row2["human_DSL_translation"]
                )
                rows.append(
                    {
                        "model": "human-human",
                        "linewise_distance": linewise_distance,
                        "characterwise_distance": characterwise_distance,
                    }
                )

    df = pd.DataFrame(rows)
    df.to_csv(here("data/processed/translation_evaluation.csv"))


if __name__ == "__main__":
    args = dict(
        # The path to the file with human translations
        ground_truth_filepath="data/manual-annotation/countdown_val.csv",
        # The names of the models to use
        model_names=[
            "llama-v3p1-8b-instruct",
            "gpt-4o",
            "llama-v3p1-70b-instruct",
            "llama-v3p1-405b-instruct",
        ],
    )
    main(args)
