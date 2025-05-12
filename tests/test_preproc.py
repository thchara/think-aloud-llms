from src.preproc.reasoning_graph_utils import get_sub_operations
from src.preproc.reasoning_graph import GraphBuilder
import networkx as nx


def test_get_sub_operations():
    assert get_sub_operations("-3+3") == [[-3, "+", 3, 0]]
    assert get_sub_operations("2+(-5)") == [[2, "+", -5, -3]]
    assert get_sub_operations("(9-4)*3+9") == [
        [9, "-", 4, 5],
        [5, "*", 3, 15],
        [15, "+", 9, 24],
    ]
    assert get_sub_operations("-1*(2+3)*4") == [
        [2, "+", 3, 5],
        [-1, "*", 5, -5],
        [-5, "*", 4, -20],
    ]
    assert get_sub_operations("5*-3") == [[5, "*", -3, -15]]
    assert get_sub_operations("4/(-2)") == [[4, "/", -2, -2]]
    assert get_sub_operations("3-(-3)") == [[3, "-", -3, 6]]


def test_graph_builder():
    graph = GraphBuilder((1, 2, 3, 4))
    graph.set_subgoal((6, 4), state_after_subgoal=(24,))
    graph.explore_operation((1, 2, 3, 4), "1+2=3", (3, 3, 4), False)
    graph.explore_operation((3, 3, 4), "3*4=12", (3, 12), False)
    graph.explore_operation((3, 12), "3+12=15", (15,), False)
    graph.explore_operation((1, 2, 3, 4), "1*2*3*4=24", (24,), False)

    assert len(graph.G.nodes) == 7
    assert len(graph.G.edges) == 7
    assert nx.has_path(graph.G, (1, 2, 3, 4), (24,))
    assert nx.has_path(graph.G, (1, 2, 3, 4), (4, 6))
    assert nx.has_path(graph.G, (24,), (4, 6))
