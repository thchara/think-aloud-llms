"""
Code the IRR trials with a given model.
"""

from src.preproc.code_with_lm import main as run_coding
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--model_name", type=str, required=True)
parser.add_argument(
    "--filepath", type=str, default="data/manual-annotation/irr-trials.csv"
)

if __name__ == "__main__":

    args = vars(parser.parse_args())
    run_coding(args)
