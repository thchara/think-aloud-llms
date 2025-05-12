"""
Code the data from the experiment in batches to save on cost.
"""

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
import pandas as pd
from pyprojroot import here
from ast import literal_eval
from src.preproc.utils import run_code
from src.preproc.auto_checker import check_graph, get_problems_str
from src.preproc.prompts import get_translation_prompt, get_correction_prompt
import json
import time
import os

test_prompt = "start state: {start_state}\nresponse: {response}\nresponse time: {rt_s} seconds\ntranscript: {transcript}"


def add_cache_control(message_list):
    last_message = message_list[-1]
    new_last_message = last_message.copy()
    new_last_message["content"] = [
        {
            "type": "text",
            "text": last_message["content"],
            "cache_control": {"type": "ephemeral"},
        }
    ]
    return message_list[:-1] + [new_last_message]


def wait_for_results(client, batch_id):
    while True:
        message_batch = client.messages.batches.retrieve(batch_id)
        if message_batch.processing_status == "ended":
            break
        time.sleep(60)

    print("Batch completed, retrieving results...")
    batch_results = client.messages.batches.results(batch_id)
    return batch_results


def start_first_batch(client, args, df_trials, deployment_name):

    print(f"coding {len(df_trials)} examples")
    system_prompt, messages = get_translation_prompt()
    messages = add_cache_control(messages)

    # create a giant batch of requests
    requests = []
    for idx, row in df_trials.iterrows():
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
        requests.append(
            Request(
                custom_id=f"coding-{idx}",
                params=MessageCreateParamsNonStreaming(
                    model=args["model_name"],
                    max_tokens=3000,
                    system=system_prompt,
                    messages=full_messages,
                    temperature=0.0,
                ),
            )
        )

    print(f"created {len(requests)} requests")

    batch = client.messages.batches.create(requests=requests)
    with open(
        here(f"data/batches/anthropic_main_batch_info_{deployment_name}.json"), "w"
    ) as f:
        json.dump(json.loads(batch.model_dump_json()), f)


def auto_checker_loop(client, coded_trials, args, deployment_name):
    system_prompt, base_messages = get_correction_prompt()
    base_messages = add_cache_control(base_messages)

    fixed_trials = []
    problem_trials = []
    # first, compile all the invalid translations
    for trial in coded_trials:
        graph = run_code(trial["translation"])
        if isinstance(graph, str):
            problem_trials.append(
                dict(
                    trial=trial,
                    n_problems=9999,
                    problems=[graph],
                    temp=0.0,
                )
            )
        else:
            problems = check_graph(graph)
            if len(problems) > 0:
                problem_trials.append(
                    dict(
                        trial=trial,
                        n_problems=len(problems),
                        problems=problems,
                        temp=0.0,
                    )
                )
            else:
                fixed_trials.append(trial)

    autochecker_log_rows = []
    for problem_trial in problem_trials:
        autochecker_log_rows.append(
            {
                "iteration": 0,
                "idx": problem_trial["trial"]["idx"],
                "trial_features": problem_trial["trial"],
                "translation": problem_trial["trial"]["translation"],
                "n_problems": problem_trial["n_problems"],
                "problems": problem_trial["problems"],
                "temp": problem_trial["temp"],
            }
        )

    # first batch
    for iteration in range(5):
        print(
            f"auto-checker iteration {iteration}: checking {len(problem_trials)} trials"
        )
        requests = []
        autochecker_test_prompts = []
        for problem_trial in problem_trials:
            if "Error running code" in problem_trial["problems"][0]:
                problems_str = problem_trial["problems"][0]
            else:
                problems_str = get_problems_str(problem_trial["problems"])
            message = {
                "role": "user",
                "content": test_prompt.format(
                    start_state=problem_trial["trial"]["start_state"],
                    response=problem_trial["trial"]["response"],
                    rt_s=problem_trial["trial"]["rt_s"],
                    transcript=problem_trial["trial"]["transcript"],
                )
                + f"\noriginal code:\n{problem_trial['trial']['translation']}\nproblems:\n{problems_str}",
            }
            autochecker_test_prompts.append(message["content"])
            full_messages = base_messages + [message]

            requests.append(
                Request(
                    custom_id=f"coding-{problem_trial['trial']['idx']}",
                    params=MessageCreateParamsNonStreaming(
                        model=args["model_name"],
                        max_tokens=3000,
                        system=system_prompt,
                        messages=full_messages,
                        temperature=problem_trial["temp"],
                    ),
                )
            )

        if not os.path.exists(
            here(
                f"data/batches/anthropic_autochecker_iteration_{iteration}_{deployment_name}.json"
            )
        ):
            batch = client.messages.batches.create(requests=requests)
            with open(
                here(
                    f"data/batches/anthropic_autochecker_iteration_{iteration}_{deployment_name}.json"
                ),
                "w",
            ) as f:
                json.dump(json.loads(batch.model_dump_json()), f)

        with open(
            here(
                f"data/batches/anthropic_autochecker_iteration_{iteration}_{deployment_name}.json"
            ),
            "r",
        ) as f:
            batch = json.load(f)
        with open(
            here(
                f"data/batches/autochecker_test_prompts_iteration_{iteration}_{deployment_name}.json"
            ),
            "w",
        ) as f:
            json.dump(autochecker_test_prompts, f)

        batch_results = wait_for_results(client, batch["id"])

        new_problem_trials = []
        for i, result in enumerate(batch_results):
            problem_trial = problem_trials[i]
            translation = result.result.message.content[0].text

            # run the code and check for problems
            graph = run_code(translation)
            if isinstance(graph, str):
                problems = [graph]
                n_problems = 9999
            else:
                problems = check_graph(graph)
                n_problems = len(problems)

            autochecker_log_rows.append(
                {
                    "iteration": iteration + 1,
                    "idx": problem_trial["trial"]["idx"],
                    "trial_features": problem_trial["trial"],
                    "translation": translation,
                    "n_problems": n_problems,
                    "problems": problems,
                    "temp": problem_trial["temp"],
                }
            )

            # If there are no remaining problems, add the trial to the fixed trials
            if n_problems == 0:
                new_trial = problem_trial["trial"].copy()
                new_trial["translation"] = translation
                fixed_trials.append(new_trial)
                continue

            # if we've improved upon the current best, replace the current best
            if n_problems < problem_trial["n_problems"]:
                new_trial = problem_trial["trial"].copy()
                new_trial["translation"] = translation
                new_problem_trials.append(
                    dict(
                        trial=new_trial,
                        n_problems=n_problems,
                        problems=problems,
                        temp=0.0,
                    )
                )

            # if we haven't improved upon the current best, increase temperature
            else:
                new_problem_trial = problem_trial.copy()
                if new_problem_trial["temp"] < 0.3:
                    new_problem_trial["temp"] += 0.1
                new_problem_trials.append(new_problem_trial)

        problem_trials = new_problem_trials
        if len(problem_trials) == 0:
            break  # lol if only

    # load up fixed_trials with the remaining problem trials
    fixed_trials.extend([pt["trial"] for pt in problem_trials])
    return fixed_trials, autochecker_log_rows


def main(args):
    deployment_name = (
        args["filepath"].split("/")[-1].split(".")[0].replace("-trials", "")
    )
    # load the data
    df_trials = pd.read_csv(here(args["filepath"]))

    # filter out in-context examples
    if "in_context" in df_trials.columns:
        df_trials = df_trials[~df_trials["in_context"]]
    # filter out irrelevant transcripts
    if "relevant" in df_trials.columns:
        df_trials = df_trials[df_trials["relevant"] == 1]
    if "practice" in df_trials.columns:
        df_trials = df_trials[~df_trials["practice"]]
    df_trials = df_trials.reset_index(drop=True)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if not os.path.exists(
        here(f"data/batches/anthropic_main_batch_info_{deployment_name}.json")
    ):
        start_first_batch(client, args, df_trials, deployment_name)

    with open(
        here(f"data/batches/anthropic_main_batch_info_{deployment_name}.json"), "r"
    ) as f:
        batch = json.load(f)

    # check batch status every minute until complete
    batch_results = wait_for_results(client, batch["id"])

    trials = []
    for i, result in enumerate(batch_results):
        row = df_trials.iloc[i]
        features = {
            "start_state": str(sorted(literal_eval(row["choices"]))),
            "response": "blank" if pd.isna(row["response"]) else row["response"],
            "rt_s": row["rt_s"],
            "transcript": row["transcript"],
        }
        trials.append(
            {"idx": i, "translation": result.result.message.content[0].text, **features}
        )

    print(f"auto-checking {len(trials)} trials")
    fixed_trials, autochecker_log_rows = auto_checker_loop(
        client, trials, args, deployment_name
    )

    df_coded = pd.DataFrame(fixed_trials)
    df_coded.drop(
        columns=["response", "rt_s", "transcript", "start_state"], inplace=True
    )
    df_coded.rename(columns={"translation": "lm_code_translation"}, inplace=True)
    df_coded.set_index("idx", inplace=True)
    df_trials = df_trials.merge(df_coded, left_index=True, right_index=True)
    print("trials index")
    print(df_trials.index)

    output_filename = (
        deployment_name + "_model-" + args["model_name"].replace("/", "--") + ".csv"
    )

    os.makedirs(here(f"data/coded/{deployment_name}"), exist_ok=True)
    df_trials.to_csv(
        here(f"data/coded/{deployment_name}/{output_filename}"), index=False
    )

    os.makedirs(here(f"data/autochecker_logs/{deployment_name}"), exist_ok=True)
    df_autochecker = pd.DataFrame(autochecker_log_rows)
    df_autochecker.to_csv(
        here(
            f"data/autochecker_logs/{deployment_name}/{output_filename.replace('.csv', '_autochecker.csv')}"
        ),
        index=False,
    )


if __name__ == "__main__":
    args = {
        "filepath": "data/processed/full-experiment/full-experiment-trials.csv",
        "model_name": "claude-3-5-sonnet-20241022",
    }
    main(args)
