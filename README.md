# Scaling up the think-aloud method with large language models

This repo contains code and data for the paper "Scaling up the think-aloud method," by Wurgaft et al., presented at
CogSci 2025

`src/` contains the main code for the preprocessing and coding pipeline (in `src/preproc`), as well 
as utilities for analyzing the data (in `src/analysis`). To run the code, we recommend creating a
new Python environment with a tool like conda or virtualenv. Then, you can install the requirements
with:

```
pip install -r requirements.txt
```

You can install this package with:

```
pip install -e .
```

# Scripts

The `scripts/` directory contains scripts for tasks like running the coding pipeline and computing 
inter-rater reliability.

The `scripts/run_pipeline.py` script is the main entry point to the preprocessing pipeline. Running it will:

1. Transcribe the audio
2. Determine whether each transcript contains information relevant to the task
3. Automatically code the transcript with a language model
4. Run the code that the model returns and compute features of the graphs.

Claude is a special case, because the Anthropic batch API makes it much cheaper if we submit batch
jobs. So `src/preproc/code_with_lm_batched.py` runs the coding with Claude.

Most of the first two steps are done in `src/preproc/preprocessing.py`. It generates random IDs for each
participant, saves the raw audio as files and transcribes them, then filters them based on 
relevance. `src/preproc/transcription.py` has a helper class for transcribing and 
`src/preproc/filtering.py` has helper functions for filtering based on relevance.

The `scripts/compute_geds.py` script computes graph edit distances for inter-rater reliability.
It does this by spawning a ton of small cpu-only Slurm jobs, so you might need to adjust some of 
the slurm parameters if you want to run it on your own cluster.

# Analysis notebooks

The `notebooks/` directory contains Jupyter notebooks for analyzing the data. The most important of
these notebooks is `MainAnalyses.ipynb`, which runs most of the analyses we report in the paper. 

# Experiment

The `experiment/` directory contains the JsPsych code we used for the experiment, along with Python
scripts to do tasks that interface with the experiment, like downloading data and counting the 
number of completions in each condition.
