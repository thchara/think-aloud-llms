from black import format_str, Mode
from pyprojroot import here
from src.preproc.auto_checker import check_graph, get_problems_str
from src.preproc.utils import run_code


# Read the GraphBuilder class code from reasoning_graph.py
def get_graphbuilder_code():
    with open(here("src/preproc/reasoning_graph.py"), "r") as file:
        lines = file.readlines()

    # Find the start of the GraphBuilder class
    start_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("class GraphBuilder:"):
            start_index = i
            break

    if start_index is None:
        raise ValueError("GraphBuilder class not found in reasoning_graph.py")

    # Find the end of the GraphBuilder class (one line before draw_graph method)
    end_index = None
    for i in range(start_index + 1, len(lines)):
        if lines[i].strip().startswith("def draw_graph"):
            end_index = i - 1
            break

    if end_index is None:
        end_index = len(lines)

    # Extract the class code
    class_code = "".join(lines[start_index : end_index + 1])
    return class_code


# Get the GraphBuilder class code
graphbuilder_code = get_graphbuilder_code()


translation_system_prompt = f"""# Task

You are acting as an AI research assistant for researchers in cognitive psychology. The researchers ran an experiment in which participants played the game of 24. In the game of 24, participants are given four numbers that they must use to make the number 24 using basic arithmetic operations (addition, subtraction, multiplication, and division). Each starting number can only be used once, and the goal is reached when all numbers are used and the result is 24.

Participants were told to say everything that comes to mind out loud as they did the experiment. You will see transcripts of what participants said as they played the game, along with the responses they submitted and their response time in seconds. Your goal is to translate each transcript into Python code which describes the operations people perform at each step toward the answer. Be aware that the transcripts may contain some transcription errors, so you should handle ambiguous cases by making reasonable assumptions.

The python code will generate a graph. The structure of that graph will represent the states they visit (sets of numbers they can use) and the operations they try (e.g., multiplication of two numbers) on the way to the solution. Operations take numbers in a state and generate a new state.

Participants can also be thought of as moving to a previously explored node if they backtrack (e.g., "this won't work, let's try again from scratch"). Finally, participants can set subgoals, which are states they are trying to reach on their way to the goal (e.g., "Let's try to make 6 and 4 to get 24").

# Code

Here is the code with the class and methods you will use to translate the participants' transcripts into Python code:

```python
{graphbuilder_code.strip()}
```

For each example, you will see the starting numbers, the response the participant submitted (i.e. the left-hand size of an equation that makes 24) the response time in seconds, and a transcript of what the participant said. Participants had 180 seconds to submit a response, so response times of 180 seconds usually mean the participant ran out of time.
"""


def get_translation_prompt():
    import pandas as pd
    from pyprojroot import here

    df = pd.read_csv(here("data/manual-coded/in-context-examples.csv"))

    messages = []
    for _, row in df.iterrows():
        start_state = row["start_state"]
        transcript = row["transcript"].strip()
        response = row["response"]
        if pd.isna(response):
            response = "blank"
        rt_s = row["rt_s"]
        translation = row["annotation"]
        translation = (
            "```python\n"
            + format_str(translation.replace("```", ""), mode=Mode())
            + "\n```"
        )

        messages.append(
            {
                "role": "user",
                "content": f"start state: {start_state}\nresponse: {response}\nresponse time: {rt_s} seconds\ntranscript: {transcript}",
            }
        )
        messages.append({"role": "assistant", "content": translation})

    return translation_system_prompt, messages


fix_system_prompt = f"""# Task

You are acting as an AI research assistant for researchers in cognitive psychology. The researchers ran an experiment in which participants played the game of 24. In the game of 24, participants are given four numbers that they must use to make the number 24 using basic arithmetic operations (addition, subtraction, multiplication, and division). Each starting number can only be used once, and the goal is reached when all numbers are used and the result is 24.

Participants were told to say everything that comes to mind out loud as they did the experiment. You will see transcripts of what participants said as they played the game, along with the responses they submitted and their response time in seconds. Your goal is to translate each transcript into Python code which describes the operations people perform at each step toward the answer. Be aware that the transcripts may contain some transcription errors, so you should handle ambiguous cases by making reasonable assumptions.

The python code will generate a graph. The structure of that graph will represent the states they visit (sets of numbers they can use) and the operations they try (e.g., multiplication of two numbers) on the way to the solution. Operations take numbers in a state and generate a new state.

Participants can also be thought of as moving to a previously explored node if they backtrack (e.g., "this won't work, let's try again from scratch"). Finally, participants can set subgoals, which are states they are trying to reach on their way to the goal (e.g., "Let's try to make 6 and 4 to get 24").

In a previous prompt, you translated what the participant said and did to code. We ran that code and checked the graph it produces for problems. Your job now is to take an existing translation and a list of problems and fix all the problems.

# Code

Here is the code with the class and methods that the translations use:

```python
{graphbuilder_code.strip()}
```

For each example, you will see the starting numbers, the response the participant submitted (i.e. the left-hand size of an equation that makes 24) the response time in seconds, a transcript of what the participant said, the original code, and the errors with the original code. Participants had 180 seconds to submit a response, so response times of 180 seconds usually mean the participant ran out of time.

Here are a few particularly common types of error. They are not the only possible errors you might encounter, but it is worth being aware of them:
- Forgetting to remove all of the input numbers in the resulting state. This seems to be especially common with 0s and 1s. For example, if the current state is (1, 2, 5) and the operation is "5*1=1", the resulting state should be (2, 5) and not (1, 2, 5)
- Dropping numbers that didn't occur on the left-hand side of the operation. This tends to happen when there are duplicate numbers in the current state, or when one of the numbers is 1. For example, if the current state is (2, 2, 10, 12) and the operation is "12*2=24", the resulting state should be (2, 10, 24), since one of the 2s from the previous state should still be there.
- Using numbers in the operation that don't occur in the current state. There are two common reasons why this happens:
	- Skipping a step, where the model uses a number that could be made simply, but doesn't get stated. For example, if the current state is (2, 7, 12) and the operation is "12+9=21", replacing the operation with "12+(7+2)=21" would fix the problem.
	- Failing to update the state properly. Sometimes the participant tries again from the start state or uses numbers from the previous state, but the translation doesn't update the state properly

Do not include any additional text before or after the code. Your response should only be runnable Python code. This is very important. If you include extra text, the code will not run.
"""


def get_correction_prompt():

    import pandas as pd
    from pyprojroot import here

    df_correction_examples = pd.read_csv(
        here("data/manual-coded/correction-examples-shortened.csv")
    )

    correction_examples = df_correction_examples.to_dict(orient="records")

    messages = []
    for _, example in enumerate(correction_examples):
        start_state = example["start_state"]
        transcript = example["transcript"].strip()
        original_code = example["translation"]
        original_code = (
            original_code.replace("```python", "").replace("```", "").strip()
        )
        original_code = "```python\n" + original_code + "\n```"
        corrected_code = example["fixed_translation"]
        corrected_code = format_str(
            corrected_code.replace("```python", "").replace("```", "").strip(),
            mode=Mode(),
        )
        corrected_code = "```python\n" + corrected_code + "\n```"
        response = example["response"]
        if pd.isna(response):
            response = "blank"
        rt_s = example["rt_s"]
        original_graph = run_code(original_code)
        # if the original graph is a string (i.e. an error message), that works as the problems
        if isinstance(original_graph, str):
            problems_str = original_graph
        else:
            problems = check_graph(original_graph)
            problems_str = get_problems_str(problems)

        messages.append(
            {
                "role": "user",
                "content": f"start state: {start_state}\nresponse: {response}\nresponse time: {rt_s} seconds\ntranscript: {transcript}\noriginal code:\n{original_code}\nproblems:\n{problems_str}",
            }
        )
        messages.append({"role": "assistant", "content": corrected_code})

    return fix_system_prompt, messages


if __name__ == "__main__":
    from rich import print

    # print(graphbuilder_code)
    # translation_system_prompt, messages = get_translation_prompt()
    # print("Translation system prompt:")
    # print(translation_system_prompt)
    # print("Translation messages:")
    # for message in messages:
    #     print(f'{message["role"].upper()}:')
    #     print(message["content"] + "\n")

    correction_system_prompt, messages = get_correction_prompt()
    # print(correction_system_prompt)
    # print(correction_system_prompt)
    for message in messages:
        print(f'{message["role"].upper()}:')
        print(message["content"] + "\n")
    # print("Correction messages:")
    # print(messages[0]["content"])
    # print(messages[1]["content"])
