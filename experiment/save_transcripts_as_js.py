# take N random transcripts from the csv and save them as jsPsych trials

import pandas as pd
import random
from pyprojroot import here
import numpy as np


def main():
    # load the csv
    df = (
        pd.read_csv(
            here(
                "data/processed/pre-collection-pilot-1/pre-collection-pilot-1-trials-filtered.csv"
            )
        )
        # remove irrelevant trials
        .query("relevant == 1")
        # remove practice trials
        .query("choices != '[6,1,1,2]' and choices != '[8,2,1,1]'")
    )
    # take N random transcripts, as well as the choices, and response corresponding to each transcript
    N = 28
    sample_indices = True
    while sample_indices:
        # randomly sample indices from the dataframe
        indices = random.sample(range(len(df)), N)
        # get the transcripts, choices, and responses corresponding to the sampled indices
        transcripts = df.iloc[indices]["transcript"].tolist()
        choices = df.iloc[indices]["choices"].tolist()
        responses = df.iloc[indices]["response"].tolist()

        if np.nan not in choices:  # had to add this because of problem with early pilot
            sample_indices = False

    # save them as jsPsych trials in the setup below
    #     const trial_data = [
    #     {
    #         transcript: "Let me try 3 plus 4...",
    #         choices: "[3,4,12,1]",
    #         response: "3*4+12*1"
    #     },
    # ];
    with open(here("code/experiment/transcripts_for_annotation.js"), "w") as f:
        f.write("const trial_data = [\n")
        for transcript, choices, response in zip(transcripts, choices, responses):
            f.write(
                f'{{transcript:"{transcript}", choices:"{choices}", response:"{response}"}},\n'
            )
        f.write("];")


if __name__ == "__main__":
    main()
