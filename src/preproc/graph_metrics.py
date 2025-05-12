"""
This file contains a number of helper functions that compute metrics on graphs that we can use to analyze the human data
"""

import os
import networkx as nx
import pandas as pd
from pyprojroot import here
from src.preproc.reasoning_graph import GraphBuilder
from src.preproc.utils import run_code


def reached_goal(graph: nx.DiGraph):
    """
    Check if the goal state is reachable from the start state
    """
    return graph.in_degree((24,)) > 0


def mean_branching_factor(graph: nx.DiGraph):
    """
    Compute the mean branching factor of a graph
    """
    return sum(graph.out_degree(node) for node in graph.nodes) / graph.number_of_nodes()


def mean_degree(graph: nx.DiGraph):
    """
    Compute the mean degree of a graph
    """
    return sum(graph.degree(node) for node in graph.nodes) / graph.number_of_nodes()


def n_subgoals(graph: nx.DiGraph):
    """
    Compute the number of subgoals in a graph
    """
    n = 0
    for edge in graph.edges:
        if graph.edges[edge]["operation"] == "subgoal":
            n += 1

    return n


def n_nodes(graph: nx.DiGraph):
    """
    Count the number of nodes in the graph
    """
    return graph.number_of_nodes()


def n_edges(graph: nx.DiGraph):
    """
    Compute the number of edges in the graph
    """
    return graph.number_of_edges()


metrics = {
    "reached_goal": reached_goal,
    "mean_branching_factor": mean_branching_factor,
    "mean_degree": mean_degree,
    "n_subgoals": n_subgoals,
    "n_nodes": n_nodes,
    "n_edges": n_edges,
}


def graph_from_code(code):
    ret = run_code(code, for_pretraining=False)
    if isinstance(ret, GraphBuilder):
        return ret.G
    else:
        return None


def main(args):
    df = pd.read_csv(args.data_filepath)
    df["graph"] = df["lm_code_translation"].apply(graph_from_code)

    # filter out the rows where the graph is None
    df = df[df["graph"].notnull()]

    for name, metric in metrics.items():
        df[name] = df["graph"].apply(metric)

    output_filepath = here(
        args.data_filepath.replace("/coded/", "/featurized/").replace(
            ".csv", "-featurized.csv"
        )
    )
    # create the parent directory if it doesn't exist
    if not os.path.exists(output_filepath.parent):
        os.makedirs(output_filepath.parent)

    df.drop(columns=["graph"]).to_csv(
        output_filepath,
        index=False,
    )
