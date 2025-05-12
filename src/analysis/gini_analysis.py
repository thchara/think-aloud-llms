import networkx as nx
from src.preproc.reasoning_graph import GraphBuilder
import pandas as pd
import numpy as np
import random
import warnings
from typing import Union
from ast import literal_eval


def get_ngrams(sequence, n=2):
    """Get all n-grams from a sequence.

    Args:
        sequence: List of items to get n-grams from
        n: Length of n-grams to extract

    Returns:
        List of n-grams, where each n-gram is a tuple of n items
    """
    if len(sequence) < n:
        return []

    ngrams = []
    for i in range(len(sequence) - n + 1):
        ngram = tuple(sequence[i : i + n])
        ngrams.append(ngram)
    return ngrams


def get_operation_sequence(graph, include_subgoals=True):
    """Get the sequence of operations in the graph."""
    timestep_to_operation = {}
    for _, target, data in graph.G.edges(data=True):
        operation = data["operation"]
        timesteps = data["op_timesteps"]
        if operation == "subgoal":
            operation = f"subgoal: {target}"

        for timestep in timesteps:
            timestep_to_operation[timestep] = operation

    operations = []
    for i in range(1, len(timestep_to_operation) + 1):
        if i in timestep_to_operation:
            op = timestep_to_operation[i]
            if include_subgoals or "subgoal" not in op:
                operations.append(op)
        else:
            warnings.warn(f"No operation found for timestep {i}")

    return operations


def compute_gini(ngrams):
    """
    Compute the Gini coefficient for a list of n-grams.
    """
    if not ngrams:
        return 0.0

    # Count frequency of each n-gram
    counts = pd.Series(ngrams).value_counts().values

    counts = np.sort(counts)
    n = len(counts)
    cumulative = np.cumsum(counts)
    lorenz = cumulative / cumulative[-1]
    area = np.sum(lorenz[:-1]) / n

    gini = 1 - 2 * area

    return gini


def sample_node(graph: nx.DiGraph):
    """
    Sample a node from the graph.
    """
    node = random.choice(list(graph.nodes))
    while len(node) == 1:
        node = random.choice(list(graph.nodes))
    return node


def get_random_op_sequence(
    start_state: tuple, n_operations: int, return_code: bool = False
) -> Union[list, str]:
    """
    Get a random sequence of operations from a given start state
    """
    start_state = tuple([int(x) for x in start_state])
    graph = GraphBuilder(start_state)
    all_ops = []
    code = f"""start_state = {start_state}
curr_state = start_state
graph = GraphBuilder(start_state)
"""
    last_state = start_state
    for _ in range(n_operations):
        state = sample_node(graph.G)
        if state != last_state:
            code += f"\ncurr_state = graph.move_to_node({state})"
        last_state = state

        num1, num2 = np.random.choice(state, size=2, replace=False)

        if num2 == 0:
            legal_op_types = ["+", "-", "*"]
        else:
            legal_op_types = ["+", "-", "*", "/"]

        operation = random.choice(legal_op_types)
        resulting_state = list(state)
        resulting_state.remove(num1)
        resulting_state.remove(num2)

        # Calculate result and convert to int if possible
        result = eval(f"{num1}{operation}{num2}")

        if result.is_integer():
            result = int(result)
        else:
            result = round(result, 2)

        if isinstance(num1, float) and num1.is_integer():
            num1 = int(num1)
        if isinstance(num2, float) and num2.is_integer():
            num2 = int(num2)

        operation_str = f"{num1}{operation}{num2}={result}"
        all_ops.append(operation_str)
        resulting_state.append(result)
        resulting_state = tuple(sorted(resulting_state))
        code += f'\ngraph.explore_operation(curr_state={state}, operation="{operation_str}", resulting_state={resulting_state}, result_calc_error=False)'
        graph.explore_operation(
            curr_state=state,
            operation=operation_str,
            resulting_state=resulting_state,
            result_calc_error=False,
        )

    if return_code:
        return code
    else:
        return all_ops


def sample_random_baseline_code_traces(
    start_state, df_participants, include_subgoals=False
):
    random_code_traces = []
    df_trial = df_participants.copy().query("choices == @start_state")
    df_trial["operation_sequence"] = df_trial["graph"].apply(
        lambda x: get_operation_sequence(x, include_subgoals=include_subgoals)
    )
    for _, row in df_trial.iterrows():
        if type(start_state) == str:
            start_state = tuple(literal_eval(start_state))
        code = get_random_op_sequence(
            start_state, len(row["operation_sequence"]), return_code=True
        )
        random_code_traces.append(code)
    return random_code_traces


### Gini analysis utils ###
def prune_graph(graph, threshold=2, remove_subgoals=True):
    """
    Prune the graph by removing nodes with less than threshold visits.
    """
    pruned_graph = graph.copy()
    nx_graph = pruned_graph.G
    edges_to_remove = []
    if remove_subgoals:
        # remove subgoal edges
        for edge in nx_graph.edges:
            if nx_graph.edges[edge]["operation"] == "subgoal":
                edges_to_remove.append(edge)
    nx_graph.remove_edges_from(edges_to_remove)
    nodes_to_remove = [
        node
        for node, data in nx_graph.nodes(data=True)
        if len(data.get("visitation_timesteps", [])) < threshold
    ]
    nx_graph.remove_nodes_from(nodes_to_remove)
    # drop nodes with no edges
    nx_graph.remove_nodes_from(
        [
            node
            for node in nx_graph.nodes
            if nx_graph.out_degree(node) == 0 and nx_graph.in_degree(node) == 0
        ]
    )
    return pruned_graph


def unite_graph_lst(graph_lst, start_state):
    # Create new graph with start state
    aggregated_graph = GraphBuilder(start_state)
    # Unite with each graph in the list
    for graph in graph_lst:
        aggregated_graph.unite_graphs(graph)
    return aggregated_graph
