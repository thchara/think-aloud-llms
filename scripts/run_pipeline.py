"""
Run the whole verbal protocol transcription pipeline.
"""

from pyprojroot import here
from src.preproc.preprocess import process_task_data as run_preprocessing
from src.preproc.preprocess import preproc_for_finetuning
from src.preproc.code_with_lm import main as run_coding
from src.preproc.graph_metrics import main as run_featurization
from src.preproc.utils import DotDict
import os


def main(args):

    deployment_name = args.raw_data_dir.split("/")[-1]

    need_to_recode = args["force_recode"]

    # first, do the preprocessing
    preprocessed_filepath = here(
        f"data/processed/{deployment_name}/{deployment_name}-trials.csv"
    )
    if os.path.exists(preprocessed_filepath) and not args["force_redo"]:
        print(f"Found preprocessed trials.")
    else:
        print("Preprocessing...")
        run_preprocessing(args)
        need_to_recode = True  # We changed something about the preprocessing, so we need to redo the coding and featurization

    args["filepath"] = str(preprocessed_filepath)

    # then do the coding with each of the models
    for model_name in args.coding_model_names:

        coded_filename = (
            deployment_name + "_model-" + model_name.replace("/", "--") + ".csv"
        )

        coded_filepath = str(here(f"data/coded/{deployment_name}/{coded_filename}"))

        print(coded_filepath)  # TODO: switched to batched coding script!
        if os.path.exists(coded_filepath) and not need_to_recode:
            print(f"Found coded data file: ({coded_filepath})")
            need_to_refeaturize = False
        else:
            args.model_name = model_name
            print(f"Coding with {model_name}...")
            run_coding(args)
            need_to_refeaturize = True

        featurized_filepath = coded_filepath.replace("/coded/", "/featurized/").replace(
            ".csv", "-featurized.csv"
        )
        if os.path.exists(featurized_filepath) and not need_to_refeaturize:
            print(f"Found featurized data file: ({featurized_filepath})")
        else:
            args.data_filepath = coded_filepath
            print(f"Featurizing {model_name} data...")
            run_featurization(args)

        # preproc for finetuning
        finetuning_proc_filepath = featurized_filepath.replace(
            "/featurized/", "/processed-for-finetuning/"
        ).replace("-featurized.csv", "-processed-for-finetuning.csv")
        if os.path.exists(finetuning_proc_filepath) and not args["force_redo"]:
            print(
                f"Found data file processed for finetuning at: ({finetuning_proc_filepath})"
            )
        else:
            args.data_filepath = featurized_filepath
            print(f"Preprocessing for finetuning...")
            preproc_for_finetuning(args)


if __name__ == "__main__":
    args = DotDict(
        {
            "force_redo": False,
            "force_recode": False,
            "raw_data_dir": "/scr/verbal-protocol/data/full-experiment",
            "coding_model_names": [
                # "claude-3-5-sonnet-20241022",
                # "deepseek-v3",
                # "llama-v3p3-70b-instruct",
                # "gpt-4o-mini",
                # "deepseek-v3-0324",
                "llama4-maverick-instruct-basic",
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
