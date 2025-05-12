"""
Read the JsPsych data and preprocess it for coding and subsequent analysis.
"""

import os
from uuid import uuid4
import pandas as pd
import base64
from tqdm import tqdm
from pyprojroot import here
from src.preproc.transcription import transcribe_audio
from src.preproc.filtering import determine_relevance
import submitit
import numpy as np
import warnings
from src.preproc.utils import run_code
from ast import literal_eval

slurm_params = {
    "name": "transcribe_audio",
    "slurm_account": "cocoflops",
    "slurm_partition": "cocoflops",
    "slurm_nodelist": "cocoflops1",
    "slurm_gres": "gpu:1",
    "nodes": 1,
    "tasks_per_node": 1,
    "cpus_per_task": 1,
    "slurm_mem": "64G",
    "slurm_time": "48:00:00",
}


def b64_audio_to_file(audio_binary, file_path):
    """
    Convert a base64-encoded audio string to an audio file at the specified path.
    """
    audio_binary += "=" * (-len(audio_binary) % 4)  # make sure padding is correct
    decoded = base64.b64decode(audio_binary)
    with open(file_path, "wb") as f:
        f.write(decoded)


def process_task_data(args):
    # read the data from each file in the raw data folder

    print("Loading data from ", args.raw_data_dir)
    df = pd.DataFrame()
    for file in os.listdir(args.raw_data_dir):
        if file.endswith(".csv"):
            # read the csv and append it to the full dataframe
            df = pd.concat([df, pd.read_csv(os.path.join(args.raw_data_dir, file))])
    df_full = df.reset_index(drop=True)

    audio_filepaths = []

    df_full["pid"] = df_full.groupby("PROLIFIC_PID")["PROLIFIC_PID"].transform(
        lambda _: uuid4()
    )

    df_full_vp = df_full[df_full["exp_type"] == "vp"]

    df_trials = df_full_vp[df_full_vp["trial_type"] == "GameOfN-audio-recording"]

    # create the recordings directory if it doesn't exist
    if not os.path.exists(f"{args.raw_data_dir}/recordings"):
        os.makedirs(f"{args.raw_data_dir}/recordings")

    print("Saving audio to webm files...")
    # save the audio to a webm file so it can be transcribed
    for _, row in tqdm(df_trials.iterrows()):
        if not isinstance(row["recording"], str):
            warnings.warn(
                f"No recording found for participant {row['pid']} trial {row['trial_index']}"
            )
            audio_filepath = "NONE"
        else:
            audio_filepath = f"{args.raw_data_dir}/recordings/participant-{row['pid']}-trial-{row['trial_index']}.webm"
            b64_audio_to_file(
                row["recording"],
                audio_filepath,
            )

        audio_filepaths.append(audio_filepath)

    # transcribe the audio
    df_trials["audio_filepath"] = audio_filepaths

    print("Transcribing...")
    # split the dataframe into 5 equal-sized chunks
    df_trials_chunks = np.array_split(df_trials, 5)

    # set up the submitit executor
    executor = submitit.AutoExecutor(folder=here("scripts/submitit"))
    executor.update_parameters(**slurm_params)

    # submit each of the chunks to the executor
    jobs = []
    for chunk in df_trials_chunks:
        jobs.append(
            executor.submit(
                transcribe_audio,
                chunk["audio_filepath"],
                args.transcription_kwargs,
            )
        )

    # wait for the jobs to finish
    transcripts = []
    for job in jobs:
        # get the results
        transcripts.extend(job.result())

    # Add the results to the dataframe
    df_trials["transcript"] = transcripts

    df_trials.to_csv(
        "/scr/verbal-protocol/transcription-cache/transcribed-data.csv", index=False
    )

    print("Filtering transcripts...")
    # decide whether each transcript has content relevant to the task
    df_trials["relevant"] = df_trials["transcript"].apply(
        lambda x: determine_relevance(x, args.filtering_model_name)
    )

    # convert response time to seconds
    df_trials["rt_s"] = (df_trials["rt"] / 1000).astype(int)

    columns_to_drop = [
        "run_id",
        "source_code_version",
        "ip",
        "user_agent",
        "device",
        "browser",
        "browser_version",
        "platform",
        "platform_version",
        "referer",
        "accept_language",
        "study_id",
        "session_id",
        "recording",
        "recorded_at",
        "rt",
        "device_id",
        "internal_node_id",
        "view_history",
        "PROLIFIC_PID",
        "STUDY_ID",
        "SESSION_ID",
    ]

    # remove PII
    df_trials = df_trials.drop(columns=columns_to_drop)
    df_full_vp = df_full_vp.drop(columns=columns_to_drop)

    # process the control condition, if it exists
    df_full_control = df_full[df_full["exp_type"] == "no-vp"]
    df_full_control["rt_s"] = (df_full_control["rt"] / 1000).astype(int)
    if df_full_control.shape[0] > 0:
        df_trials_control = df_full_control[df_full_control["trial_type"] == "GameOfN"]
        # remove PII
        df_trials_control = df_trials_control.drop(columns=columns_to_drop)
        df_full_control = df_full_control.drop(columns=columns_to_drop)

    print("Done preprocessing!")

    deployment_name = args.raw_data_dir.split("/")[-1]
    if not os.path.exists(here(f"data/processed/{deployment_name}")):
        os.mkdir(here(f"data/processed/{deployment_name}"))

    df_trials.to_csv(
        here(f"data/processed/{deployment_name}/{deployment_name}-trials.csv"),
        index=False,
    )

    df_full_vp.to_csv(
        here(f"data/processed/{deployment_name}/{deployment_name}-full.csv"),
        index=False,
    )

    if df_full_control.shape[0] > 0:
        df_full_control.to_csv(
            here(
                f"data/processed/{deployment_name}/{deployment_name}-control-full.csv"
            ),
            index=False,
        )
        df_trials_control.to_csv(
            here(
                f"data/processed/{deployment_name}/{deployment_name}-control-trials.csv"
            ),
            index=False,
        )


# Functions to process coded data for finetuning


def preprocess_graph_for_finetuning(annotation, target=24, for_pretraining=False):
    """
    Preprocess a human graph for finetuning LM.
    """
    # get graph from annotation
    graph = run_code(annotation, for_pretraining=for_pretraining)
    # check if graph is a string
    code_str_proc = ""
    # get each action from graph
    for i, action in enumerate(graph.actions):
        if action["type"] == "start":
            code_str_proc += f"# Goal: {target}\ncurr_state = {action["state"]}\ngraph = GraphBuilder(curr_state)\n"
        elif action["type"] == "explore_operation":
            if action["sub_operations_dict"] is not None:
                for j in range(len(action["sub_operations_dict"]["operation"])):
                    code_str_proc += f"new_state = graph.explore_operation(curr_state,operation='{action["sub_operations_dict"]["operation"][j]}',resulting_state={action["sub_operations_dict"]["resulting_state"][j]})\n"
                    if j != len(action["sub_operations_dict"]["operation"]) - 1:
                        code_str_proc += f"curr_state = graph.move_to_node({action["sub_operations_dict"]["resulting_state"][j]})\n"
            else:
                code_str_proc += f"new_state = graph.explore_operation(curr_state,operation='{action["operation"]}',resulting_state={action["resulting_state"]})\n"
            if i == len(graph.actions) - 1 and action[
                "resulting_state"
            ] == literal_eval(f"({target},)"):
                code_str_proc += "# Goal Reached\n"
        elif action["type"] == "move_to_node":
            code_str_proc += f"curr_state = graph.move_to_node({action["new_state"]})\n"
    return code_str_proc


def preproc_for_finetuning(args):
    """
    Preprocess the data for finetuning by removing comments, breaking down multi-operation actions, removing excluded participants, and other preprocessing steps.
    """
    # read the data from each file in the raw data folder

    print("Loading data from ", args.data_filepath)
    df_with_exclusions = (
        pd.read_csv(args.data_filepath).assign(
            relevant_ratio=lambda df: df.groupby("pid")["relevant"].transform("sum")
            / df.groupby("pid").transform("size")
        )
        # remove participants with below 0.5 relevant ratio
        .query("relevant_ratio >= 0.5")
        # remove irrelevant trials
        .query("relevant == 1")
    )

    df_with_exclusions["code_str_proc"] = None
    # preprocess the graph for finetuning
    for i, row in df_with_exclusions.iterrows():
        code_str_proc = preprocess_graph_for_finetuning(row["lm_code_translation"])
        # add to the dataframe
        df_with_exclusions.at[i, "code_str_proc"] = code_str_proc

    # create a new dataframe with just code_str_proc
    df_code_str_proc = df_with_exclusions[["code_str_proc", "pid", "choices"]]
    # save the dataframe
    finetuning_proc_filepath = args.data_filepath.replace(
        "/featurized/", "/processed-for-finetuning/"
    ).replace("-featurized.csv", "-processed-for-finetuning.csv")
    df_code_str_proc.to_csv(finetuning_proc_filepath, index=False)
