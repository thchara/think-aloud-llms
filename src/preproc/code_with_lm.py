"""
Code the countdown data using constrained generation via the Fireworks API.
"""

from ast import literal_eval
import os
import numpy as np
import pandas as pd
from pyprojroot import here
from datetime import datetime
import submitit
import json
from glob import glob
from fireworks.client import Fireworks
from openai import OpenAI, BadRequestError
from src.preproc.prompts import get_translation_prompt, get_correction_prompt
from src.preproc.auto_checker import check_graph, get_problems_str
from src.preproc.utils import run_code
import anthropic
import backoff

test_prompt = "start state: {start_state}\nresponse: {response}\nresponse time: {rt_s} seconds\ntranscript: {transcript}"


@backoff.on_exception(backoff.expo, Exception, max_time=600)
def get_model_response(api_type, client, system_prompt, full_messages, args, temp=0.0):
    if api_type == "openai":
        system_role = (
            "system" if "gpt" in args["model_name"] else "user"
        )  # for o1 compatibility
        try:
            chat_completion = client.chat.completions.create(
                model=args["model_name"],
                messages=[{"role": system_role, "content": system_prompt}]
                + full_messages,
                temperature=temp,
            )
            translation = chat_completion.choices[0].message.content
        except BadRequestError:
            translation = "# Bad request error"
    elif api_type == "anthropic":
        chat_completion = client.messages.create(
            model=args["model_name"],
            max_tokens=3000,
            system=system_prompt,
            messages=full_messages,
            temperature=temp,
        )
        translation = chat_completion.content[0].text
    else:
        chat_completion = client.chat.completions.create(
            model=f"accounts/fireworks/models/{args['model_name']}",
            messages=[{"role": "system", "content": system_prompt}] + full_messages,
            temperature=temp,
        )
        translation = chat_completion.choices[0].message.content

    # save the result to the prompt cache (in case of error elsewhere in code)

    return translation


def try_retry(features, translation, problems, api_type, client, args):
    """
    When code fails the auto-checker, make another call to the language model to try fixing it
    """

    system_prompt, base_messages = get_correction_prompt()

    best_translation = translation
    if "Error running code" in problems[0]:
        best_n_problems = 9999
    else:
        best_n_problems = len(problems)

    all_translations = [
        {
            "iteration": 0,
            "transcript": features["transcript"],
            "translation": translation,
            "n_problems": best_n_problems,
            "problems": problems,
            "temp": 0.0,
        }
    ]

    temp = 0.0
    for i in range(5):
        # convert a list of dictionaries to a string
        if "Error running code" in problems[0]:
            problems_str = problems[0]
        else:
            problems_str = get_problems_str(problems)

        message = {
            "role": "user",
            "content": test_prompt.format(**features)
            + f"\n\noriginal code:\n{best_translation}\n\nproblems:\n{problems_str}",
        }
        prompt = base_messages + [message]

        translation = get_model_response(
            api_type, client, system_prompt, prompt, args, temp=temp
        )

        # run and check the code
        graph = run_code(translation)
        if isinstance(graph, str):
            problems = [graph]
        else:
            problems = check_graph(graph)

        # compute the number of problems
        if len(problems) >= 1 and "Error running code" in problems[0]:
            n_problems = 9999
        else:
            n_problems = len(problems)

        print(f"retry {i}")
        print(f"n problems: {n_problems}")
        print(f"best n problems: {best_n_problems}")

        all_translations.append(
            {
                "iteration": i + 1,
                "transcript": features["transcript"],
                "translation": translation,
                "n_problems": n_problems,
                "problems": problems,
                "temp": temp,
            }
        )

        # If this translation is better than the current best, replace the current best
        if n_problems < best_n_problems:
            best_translation = translation
            best_n_problems = n_problems
            temp = 0.0  # reset temperature if we've improved
        else:
            # increase temperature (up to 0.3) if we haven't improved upon the current translation
            if temp < 0.3:
                temp += 0.1

        # stop if there are no more problems
        if best_n_problems == 0:
            break

    df_log = pd.DataFrame(all_translations)
    return best_translation, df_log


def code_rows(df_chunk, args):

    # if we're using an OpenAI model:
    if "gpt" in args["model_name"] or "o1" in args["model_name"]:
        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        api_type = "openai"
    elif "claude" in args["model_name"]:
        client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )
        api_type = "anthropic"
    else:
        # use the Fireworks api
        client = Fireworks(api_key=os.getenv("FIREWORKS_API_KEY"))
        api_type = "fireworks"

    system_prompt, messages = get_translation_prompt()

    model_translations = []
    autochecker_log_dfs = []
    for _, row in df_chunk.iterrows():

        features = {
            "start_state": str(sorted(literal_eval(row["choices"]))).replace(" ", ""),
            "response": row["response"],
            "rt_s": row["rt_s"],
            "transcript": row["transcript"],
        }
        full_messages = messages + [
            {
                "role": "user",
                "content": test_prompt.format(**features),
            }
        ]

        translation = get_model_response(
            api_type, client, system_prompt, full_messages, args
        )

        graph = run_code(translation)
        if isinstance(graph, str):
            problems = [graph]
        else:
            problems = check_graph(graph)
        if problems:
            translation, df_log = try_retry(
                features, translation, problems, api_type, client, args
            )
            autochecker_log_dfs.append(df_log)

        # get the translation
        model_translations.append(translation)

        # save the translation to the cache, in case of error
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        with open(
            f"/scr/verbal-protocol/translation-cache/{args['model_name']}-{timestamp}.json",
            "w",
        ) as f:
            json.dump(
                {
                    "start_state": sorted(literal_eval(row["choices"])),
                    "response": row["response"],
                    "rt_s": row["rt_s"],
                    "transcript": row["transcript"],
                    "translation": translation,
                },
                f,
            )

    return model_translations, autochecker_log_dfs


slurm_params = {
    "name": "code_countdown_api",
    "slurm_account": "cocoflops",
    "slurm_partition": "cocoflops",
    "slurm_nodelist": "cocoflops1",
    "nodes": 1,
    "tasks_per_node": 1,
    "cpus_per_task": 1,
    "slurm_mem": "16G",
    "slurm_time": "24:00:00",
}


def main(args):

    # load the data
    df = pd.read_csv(here(args["filepath"]))
    # filter out in-context examples
    if "in_context" in df.columns:
        df = df[~df["in_context"]]
    # filter out irrelevant transcripts
    if "relevant" in df.columns:
        df = df[df["relevant"] == 1]
    df_trials = df[df["choices"].apply(lambda x: isinstance(x, str))]
    df_trials["start_state"] = df_trials["choices"].apply(lambda x: str(sorted(literal_eval(x))).replace(" ", ""))
    # load the already-coded rows
    already_coded_rows = []
    for fname in glob("/scr/verbal-protocol/translation-cache/llama4-maverick-instruct-basic-*"):
        row = json.load(open(fname))
        already_coded_rows.append(row)
    
    df_already_coded = pd.DataFrame(already_coded_rows)
    df_already_coded = df_already_coded.rename(columns={"translation": "lm_code_translation"})
    df_already_coded["start_state"] = df_already_coded["start_state"].apply(lambda x: str(sorted(x)).replace(" ", ""))
    print(f"{len(df_already_coded)} already-coded rows")
    df_trials = df_trials.merge(df_already_coded, on=["start_state", "response", "rt_s", "transcript"], how="left", indicator=True)
    df_already_coded_trials = df_trials[df_trials["lm_code_translation"].notna()]
    df_trials = df_trials[df_trials["lm_code_translation"].isna()]

    print(f"evaluating on {len(df_trials)} examples")

    # code the data in different processes
    executor = submitit.AutoExecutor(folder=here("scripts/submitit"))
    executor.update_parameters(**slurm_params)
    df_trials_chunks = np.array_split(df_trials, 10)
    jobs = []
    for chunk in df_trials_chunks:
        chunk = chunk[["response", "rt_s", "transcript", "choices"]]
        jobs.append(executor.submit(code_rows, chunk, args))

    # wait for the jobs to finish
    all_model_translations = []
    all_autochecker_log_dfs = []
    for job in jobs:
        model_translations, autochecker_log_dfs = job.result()
        all_model_translations.extend(model_translations)
        all_autochecker_log_dfs.extend(autochecker_log_dfs)

    # save the coded data
    df_trials["lm_code_translation"] = all_model_translations
    deployment_name = (
        args["filepath"].split("/")[-1].split(".")[0].replace("-trials", "")
    )
    output_filename = (
        deployment_name + "_model-" + args["model_name"].replace("/", "--") + ".csv"
    )

    df_all_trials = pd.concat([df_already_coded_trials, df_trials])
    if not os.path.exists(here(f"data/coded/{deployment_name}")):
        os.makedirs(here(f"data/coded/{deployment_name}"))
    df_all_trials.to_csv(
        here(f"data/coded/{deployment_name}/{output_filename}"), index=False
    )

    # save the autochecker logs
    df_autochecker = pd.concat(all_autochecker_log_dfs)

    if not os.path.exists(here("data/autochecker_logs")):
        os.makedirs(here("data/autochecker_logs"))
    if not os.path.exists(here(f"data/autochecker_logs/{deployment_name}")):
        os.makedirs(here(f"data/autochecker_logs/{deployment_name}"))
    df_autochecker.to_csv(
        here(
            f"data/autochecker_logs/{deployment_name}/"
            + output_filename.replace(".csv", "_autochecker.csv")
        ),
        index=False,
    )
