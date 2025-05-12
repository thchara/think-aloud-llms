import re
import traceback
import linecache
import pandas as pd
from pyprojroot import here
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import linecache
import re
import numpy as np
from pyprojroot import here
from src.preproc.reasoning_graph import GraphBuilder


class DotDict(dict):
    """
    dot.notation access to dictionary attributes
    https://stackoverflow.com/a/23689767
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def copy(self):
        return DotDict(super().copy())


def fix_tuples(response, for_pretraining=True):
    # all tuples must be sorted in ascending order
    response_lines = response.split("\n")
    for i, line in enumerate(response_lines):
        if i == 1:
            # remove anything after # from line if present
            line = line.split("#")[0]
            num_tuple = (
                line.split("curr_state = ")[1]
                .replace(")", "")
                .replace(" ", "")
                .replace("(", "")
                .split(",")
            )
            if (
                for_pretraining
            ):  # for pretraining, we want to ensure all numbers are integers to make learning easier
                num_tuple = sorted([int(num) for num in num_tuple if len(num) > 0])
                num_tuple = str(tuple(num_tuple))
            else:
                # check if the first value in num_tuple is variable rather than a number
                if len(num_tuple) > 0 and all(
                    c.isalpha() or c == "_" for c in num_tuple[0]
                ):
                    num_tuple = num_tuple[0]
                else:
                    num_tuple = sorted([eval(num) for num in num_tuple if len(num) > 0])
                    num_tuple = str(tuple(num_tuple))
            response_lines[i] = "curr_state = " + num_tuple
        elif "graph.move_to_node(" in line:
            # remove anything after # from line if present
            line = line.split("#")[0]
            initial_line = line.split("graph.move_to_node(")[0] + "graph.move_to_node("
            num_tuple = (
                line.split("graph.move_to_node(")[1]
                .replace(")", "")
                .replace(" ", "")
                .replace("(", "")
                .split(",")
            )
            if (
                for_pretraining
            ):  # for pretraining, we want to ensure all numbers are integers to make learning easier
                num_tuple = sorted([int(num) for num in num_tuple if len(num) > 0])
                num_tuple = str(tuple(num_tuple))
            else:
                # check if the first value in num_tuple is variable rather than a number
                if len(num_tuple) > 0 and all(
                    c.isalpha() or c == "_" for c in num_tuple[0]
                ):
                    num_tuple = num_tuple[0]
                else:
                    num_tuple = sorted([eval(num) for num in num_tuple if len(num) > 0])
                    num_tuple = str(tuple(num_tuple))
            response_lines[i] = initial_line + num_tuple + ")"
        elif "resulting_state=(" in line:
            # remove anything after # from line if present
            line = line.split("#")[0]
            initial_line = line.split("resulting_state=(")[0] + "resulting_state="
            num_tuple = (
                line.split("resulting_state=(")[1]
                .replace(")", "")
                .replace(" ", "")
                .replace("(", "")
                .split(",")
            )
            if (
                for_pretraining
            ):  # for pretraining, we want to ensure all numbers are integers to make learning easier
                num_tuple = sorted([int(num) for num in num_tuple if len(num) > 0])
                num_tuple = str(tuple(num_tuple))
            else:
                # check if the first value in num_tuple is variable rather than a number
                if len(num_tuple) > 0 and all(
                    c.isalpha() or c == "_" for c in num_tuple[0]
                ):
                    num_tuple = num_tuple[0]
                else:
                    num_tuple = sorted([eval(num) for num in num_tuple if len(num) > 0])
                    num_tuple = str(tuple(num_tuple))
            response_lines[i] = initial_line + num_tuple + ","
    response = "\n".join(response_lines)
    return response


def preprocess_response(response, for_pretraining):
    # remove everything up to the </think> tag if it exists
    if "</think>" in response:
        response = response.split("</think>")[1]

    try:
        response = response.replace("```python", "")
        response = response.replace("```", "")
        response = response.replace("comments=", "comment=")
        response = response.replace("comments =", "comment =")
    except Exception:
        print(response)
        raise
    response = re.sub(
        r"start_state = \[(\d+), ?(\d+), ?(\d+), ?(\d+)\]",
        r"start_state = (\1, \2, \3, \4)",
        response,
    )

    response = response.strip()
    # response = fix_tuples(response, for_pretraining=for_pretraining)

    response = "global graph\n" + response

    return response


def run_code(code, for_pretraining=True):
    code = preprocess_response(code, for_pretraining=for_pretraining)
    linecache.cache["<string>"] = (
        len(code),
        None,
        code.splitlines(keepends=True),
        "<string>",
    )
    try:
        exec(code)
        return graph
    except Exception:
        traceback_str = "".join(traceback.format_exc())
        if "IndexError: pop from empty list" in traceback_str:
            return f"Error running code. Python gave the following error message:\n{traceback_str}\nIt is possible that you forgot a '=' sign."
        else:
            return f"Error running code. Python gave the following error message:\n{traceback_str}"


def graph_edit_distance(graph1, graph2, timeout=60):
    if isinstance(graph1, str) or isinstance(graph2, str):
        return None
    return nx.graph_edit_distance(
        graph1.G,
        graph2.G,
        timeout=timeout,
        node_subst_cost=lambda x, y: 1 if x["state"] != y["state"] else 0,
    ) / (
        max(graph1.G.number_of_nodes(), graph2.G.number_of_nodes())
        + max(graph1.G.number_of_edges(), graph2.G.number_of_edges())
    )


def unnormalized_graph_edit_distance(graph1, graph2, timeout=60):
    if isinstance(graph1, str) or isinstance(graph2, str):
        return None
    return nx.graph_edit_distance(
        graph1.G,
        graph2.G,
        timeout=timeout,
        node_subst_cost=lambda x, y: 1 if x["state"] != y["state"] else 0,
    )


def graph_IoU(graph1, graph2):
    if isinstance(graph1, str) or isinstance(graph2, str):
        return None
    intersection = nx.intersection(graph1.G, graph2.G)
    union = nx.compose(graph1.G, graph2.G)
    return intersection.size() / union.size()


if __name__ == "__main__":
    import pandas as pd

    # read annotation from in context examples
    in_context_examples = pd.read_csv(
        here("data/manual-annotation/in-context-examples.csv")
    )
    # take a particular row index
    row_index = 0
    print(in_context_examples.iloc[row_index]["annotation"])
    print(
        preprocess_human_graph_for_finetuning(
            in_context_examples.iloc[row_index]["annotation"]
        )
    )
