"""
Run the whole verbal protocol transcription pipeline.
"""

from src.preproc.code_with_lm_batched import main as run_coding
from src.preproc.graph_metrics import main as run_featurization
from src.preproc.utils import DotDict
from src.preproc.transcription import transcribe_audio
from pyprojroot import here
import pandas as pd
import os
import subprocess


def cut_off_audio(filepath, cutoff_time=181):
    new_filepath = filepath.replace(".webm", "-cut-off.webm")
    if not os.path.exists(new_filepath):
        # cut off the audio at the cutoff time
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                filepath,
                "-c:a",
                "libopus",
                "-t",
                str(cutoff_time),
                new_filepath,
            ]
        )

    return new_filepath


def main(args):
    df = pd.read_csv(here(args.filepath))
    # filter out trials that are too long
    df = df[(df["rt_s"] > 181) & (df["audio_filepath"] != "NONE")]

    # preprocess those trials
    df["correct"] = False
    df["response"] = pd.NA

    # cut off and re-transcribe
    df["audio_filepath"] = df["audio_filepath"].apply(cut_off_audio)
    df["transcript"] = transcribe_audio(df["audio_filepath"], args.transcription_kwargs)

    new_filepath = args.filepath.replace("-trials.csv", "-too-long-fix-trials.csv")
    df.to_csv(here(new_filepath), index=False)

    # re-code the data
    run_coding({"filepath": new_filepath, "model_name": "claude-3-5-sonnet-20241022"})


if __name__ == "__main__":
    args = DotDict(
        {
            "filepath": "data/processed/full-experiment/full-experiment-trials.csv",
            "coding_model_names": [
                "claude-3-5-sonnet-20241022",
            ],
            "filtering_model_name": "llama-v3p3-70b-instruct",
            "transcription_kwargs": {
                "beam_size": 5,
                "condition_on_previous_text": True,
                "compression_ratio_threshold": 2.4,
                "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.6,
                "word_timestamps": True,
                "language": "en",
                "initial_prompt": "Interviewer: You will play a mathematical game where you start with a set of 4 numbers and have to make the number 24. As you perform the task, try to say aloud everything that comes to mind.\nParticipant:",
                "hallucination_silence_threshold": 20,
                "vad_filter": False,
            },
        }
    )

    main(args)
