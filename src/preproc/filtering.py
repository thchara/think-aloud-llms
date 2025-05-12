"""
Filter out the transcripts that aren't relevant to the task
"""

import os
import pandas as pd
from fireworks.client import Fireworks
from pyprojroot import here
import backoff

system_prompt = """You will see transcripts from participants in a psychology experiment. Participants were asked to play a mathematical game and say whatever comes to mind. Sometimes, participants didn't say anything and the transcription algorithm produced something weird. Other times, the transcription picked up on background noise.
Your goal is to determine which transcripts contain information relevant to the experiment and which are just irrelevant information.

Classify each transcript as:
1. relevant to the mathematical game, containing the participant's thoughts about the numbers of the game they were playing
2. irrelevant to the mathematical game, containing other thoughts, background noise, or transcription errors
"""

in_context_examples = [
    ("Hello.", "irrelevant to the mathematical game"),
    (
        "Okay, target number is 24. Okay, 24, so 9 plus 11, what was that? That gives us 20. Oh, we can just add all these up. 9 plus 11, because 9 plus 11 gives us 20, plus 2, plus 2 gives us 24.",
        "relevant to the mathematical game",
    ),
    ("Okay. E aí E aí E aí E aí", "irrelevant to the mathematical game"),
    (
        "Great, another one. Okay, now I'm on a 7 is 2. Okay. 7 times 6 is 42. 42. Why does this have to be so hard? Oh my gosh. I was trying to do nine times four is 36 minus 13, but that gives me 23. okay what if I do 9 times 6 is awful. Takk for ating med. Okay, what if I did – oh, I got it. Okay, I got it. minus 6 gives me 3 times 7 for 21 plus 4 that's 25. Wow okay I thought I had it but if I do",
        "relevant to the mathematical game",
    ),
    (
        "Thank you. The presence of an odd number here makes this one tricky. and my first thought would be to subtract 13 and 10 to get 3, but I don't think 3 helps us. Actually, no, never mind. I'm wrong. So we put parentheses 13 minus 10 to get 3, and then we're just going to multiply the following two numbers, and that'll give us 24, because 3 times 4 is 12, and that'll give us 24. Because three times four is 12 and 12 times two is 24.",
        "relevant to the mathematical game",
    ),
    (
        "Thank you. 16. Thank you. Hmm. Okay. Спасибо. .",
        "irrelevant to the mathematical game",
    ),
    (
        "24 25 26 27",
        "irrelevant to the mathematical game",
    ),
    (
        "24. Um. Okay. Uh. I don't really know. Um. Um. Hmm. hmm um okay okay okay think cat this is hard so it could do Wait a second. Wait a second. I don't know. This is hard. 18. 18 minus. Um. wait, 20, 36, nope. Oh, I think I got it. 9 times 6 equals 54. Divided by 2. Where's the divide? Okay. 54 divided by 2 is 27. No, wait. Never mind. That didn't work. Hmm. nevermind that didn't work. 6 times 1272 108 divided by 6 is what?",
        "relevant to the mathematical game",
    ),
    (
        "Okay, my target number is 24. Okay, I know that 24 minus 13 gives me 11. oh my gosh I don't know what to do okay 2 plus 4 is 6. 10 divided by 2 would be 5. 5 plus 4 is 9. Fuck. 10. Fuck. Ten. Oh my gosh. I don't know how to figure this out. I'm struggling. Ten times two is twenty. I could do 4 minus 2 is 2",
        "relevant to the mathematical game",
    ),
    (
        "Let's see. Thank you. so So, let's do the weight.",
        "irrelevant to the mathematical game",
    ),
]

obviously_irrelevant = ("Thank you", "Thank you.", "you", ".", "Gracias.", "or", "")

full_messages = [{"role": "system", "content": system_prompt}]
for example in in_context_examples:
    full_messages.append({"role": "user", "content": example[0]})
    full_messages.append({"role": "assistant", "content": example[1]})

response_grammar = r"""
root ::= "relevant to the mathematical game" | "irrelevant to the mathematical game"
"""


@backoff.on_exception(backoff.expo, Exception, max_time=600)
def query_model(client, full_messages, transcript, model_name):
    model_str = f"accounts/fireworks/models/{model_name}"
    chat_completion = client.chat.completions.create(
        model=model_str,
        response_format={"type": "grammar", "grammar": response_grammar},
        messages=full_messages + [{"role": "user", "content": transcript}],
    )
    return chat_completion


def determine_relevance(transcript, model_name):

    # First, use some heuristics
    if (not isinstance(transcript, str)) or (
        transcript.strip() in obviously_irrelevant
    ):
        return 0

    client = Fireworks(api_key=os.getenv("FIREWORKS_API_KEY"))
    # Otherwise, use the prompt to filter
    chat_completion = query_model(client, full_messages, transcript, model_name)

    return int(
        chat_completion.choices[0].message.content.strip()
        == "relevant to the mathematical game"
    )


def main(args):

    # Load the data
    df = pd.read_csv(here(args["filepath"]))

    output_filepath = args["filepath"].replace(".csv", "-filtered.csv")
    df.to_csv(here(output_filepath), index=False)
