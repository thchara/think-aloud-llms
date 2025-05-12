"""
Code the examples that we use for inter-rater reliability between human coders.
"""

from src.preproc.code_with_lm import main as run_coding


def main(args):
    for model_name in args["model_names"]:
        coding_args = {
            "model_name": model_name,
            "filepath": args["filepath"],
        }
        run_coding(coding_args)


if __name__ == "__main__":
    args = {
        "filepath": "data/manual-annotation/full-experiment/full-experiment-trials-to-annotate-fixed.csv",
        "model_names": ["llama-v3p3-70b-instruct", "llama-v3p1-8b-instruct"],
    }
    main(args)
