from src.analysis.analysis_utils import (
    classify_subgoal_state,
    count_operations,
    compute_item_correlation,
)
from src.analysis.gini_analysis import (
    get_ngrams,
    compute_gini,
    get_operation_sequence,
    get_random_op_sequence,
)
from src.analysis.errors import count_error_types
from src.preproc.reasoning_graph import GraphBuilder
from src.preproc.utils import run_code
import pandas as pd
import numpy as np


def test_classify_subgoal_state():

    # single-number subgoals
    assert classify_subgoal_state((1,)) == "single"
    assert classify_subgoal_state((12,)) == "single"
    assert classify_subgoal_state((6,)) == "single"
    assert classify_subgoal_state((24,)) == "single"

    # product subgoals
    assert classify_subgoal_state((2, 12)) == "product"
    assert classify_subgoal_state((12, 2)) == "product"
    assert classify_subgoal_state((3, 8)) == "product"
    assert classify_subgoal_state((6, 4)) == "product"
    assert classify_subgoal_state((1, 24)) == "product"

    # sum subgoals
    assert classify_subgoal_state((12, 12)) == "sum"
    assert classify_subgoal_state((11, 13)) == "sum"
    assert classify_subgoal_state((4, 20)) == "sum"
    assert classify_subgoal_state((26, -2)) == "sum"

    # difference subgoals
    assert classify_subgoal_state((36, 12)) == "difference"
    assert classify_subgoal_state((2, 26)) == "difference"
    assert classify_subgoal_state((10, 34)) == "difference"
    assert classify_subgoal_state((30, 6)) == "difference"

    # quotient subgoals
    assert classify_subgoal_state((48, 2)) == "quotient"
    assert classify_subgoal_state((3, 72)) == "quotient"
    assert classify_subgoal_state((4, 96)) == "quotient"
    assert classify_subgoal_state((120, 5)) == "quotient"

    # other subgoals
    assert classify_subgoal_state((1, 2, 3)) == "other"
    assert classify_subgoal_state((22, 1)) == "other"
    assert classify_subgoal_state((148, 45)) == "other"
    assert classify_subgoal_state((24, 24, 24, 24)) == "other"


def test_count_operations():
    graph = GraphBuilder((1, 2, 3, 4))
    graph.set_subgoal((6, 4), state_after_subgoal=(24,))
    graph.explore_operation((1, 2, 3, 4), "1+2=3", (3, 3, 4), False)
    graph.explore_operation((3, 3, 4), "3*4=12", (3, 12), False)
    graph.explore_operation((3, 12), "3+12=15", (15,), False)
    graph.explore_operation((1, 2, 3, 4), "4/1=4", (2, 3, 4), False)

    assert count_operations(graph) == {"+": 2, "*": 1, "/": 1, "-": 0}

    graph = GraphBuilder((1, 1, 4, 6))
    graph.set_subgoal((10,), state_after_subgoal=(24,))
    graph.explore_operation((1, 1, 4, 6), "4*6*1*1=24", (24,), False)

    assert count_operations(graph) == {"*": 3, "+": 0, "-": 0, "/": 0}

    graph = GraphBuilder((1, 1, 4, 6))
    graph.set_subgoal((10,), state_after_subgoal=(24,))
    graph.explore_operation((1, 1, 4, 6), "6-4=2", (1, 1, 2), False)
    graph.explore_operation((1, 1, 2), "1-1=0", (0, 2), False)
    graph.explore_operation((0, 2), "0+2=2", (2,), False)

    assert count_operations(graph) == {"-": 2, "+": 1, "*": 0, "/": 0}


def test_compute_item_correlation():
    # Test case 1: Perfect positive correlation
    df1 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [1, 0, 1, 0]})
    df2 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [1, 0, 1, 0]})
    assert np.isclose(compute_item_correlation(df1, df2), 1.0)

    # Test case 2: Perfect negative correlation
    df1 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [1, 0, 1, 0]})
    df2 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [0, 1, 0, 1]})
    assert np.isclose(compute_item_correlation(df1, df2), -1.0)

    # Test case 3: No correlation
    df1 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [1, 1, 0, 0]})
    df2 = pd.DataFrame({"choices": ["A", "B", "C", "D"], "correct": [1, 0, 1, 0]})
    assert np.isclose(compute_item_correlation(df1, df2), 0.0)

    # Test case 4: Different number of samples per choice
    df1 = pd.DataFrame(
        {"choices": ["A", "A", "B", "B", "C", "C"], "correct": [1, 1, 0, 0, 1, 1]}
    )
    df2 = pd.DataFrame({"choices": ["A", "B", "C"], "correct": [1, 0, 1]})
    assert np.isclose(compute_item_correlation(df1, df2), 1.0)

    # Test case 5: Missing choices in one group
    df1 = pd.DataFrame({"choices": ["A", "B", "C"], "correct": [1, 0, 1]})
    df2 = pd.DataFrame(
        {
            "choices": ["A", "B", "D"],
            "correct": [1, 0, 1],
        }
    )
    # Should only correlate on common choices A and B
    assert np.isclose(compute_item_correlation(df1, df2), 1.0)


def test_get_ngrams():
    assert get_ngrams([1, 2, 3, 4], 1) == [(1,), (2,), (3,), (4,)]
    assert get_ngrams([1, 2, 3, 4], 2) == [(1, 2), (2, 3), (3, 4)]
    assert get_ngrams([1, 2, 3, 4], 3) == [(1, 2, 3), (2, 3, 4)]
    assert get_ngrams([1, 2, 3, 4], 4) == [(1, 2, 3, 4)]
    assert get_ngrams([1, 2, 3, 4, 5], 2) == [(1, 2), (2, 3), (3, 4), (4, 5)]


def test_get_operation_sequence():

    graph = GraphBuilder((1, 2, 3, 4))
    graph.set_subgoal((4, 6), state_after_subgoal=(24,))
    graph.explore_operation((1, 2, 3, 4), "1+2=3", (3, 3, 4), False)
    graph.explore_operation((3, 3, 4), "3*4=12", (3, 12), False)
    graph.explore_operation((3, 12), "3+12=15", (15,), False)
    assert get_operation_sequence(graph) == [
        "subgoal: (4, 6)",
        "1+2=3",
        "3*4=12",
        "3+12=15",
    ]

    assert get_operation_sequence(graph, include_subgoals=False) == [
        "1+2=3",
        "3*4=12",
        "3+12=15",
    ]

    graph = GraphBuilder((1, 1, 4, 6))
    graph.set_subgoal((10,), state_after_subgoal=(24,))
    graph.explore_operation((1, 1, 4, 6), "4*6*1*1=24", (24,), False)
    assert get_operation_sequence(graph) == [
        "subgoal: (10,)",
        "4*6=24",
        "24*1=24",
        "24*1=24",
    ]

    graph = GraphBuilder((1, 1, 4, 6))
    graph.set_subgoal((10,), state_after_subgoal=(24,))
    graph.explore_operation((1, 1, 4, 6), "4+1=5", (5, 4, 6), False)
    graph.explore_operation((1, 1, 4, 6), "4+6=10", (1, 1, 10), False)
    graph.explore_operation((1, 1, 4, 6), "4+1=5", (5, 4, 6), False)
    graph.set_subgoal((10, 14), state_after_subgoal=(24,))
    graph.explore_operation((1, 1, 4, 6), "1+1=2", (2, 4, 6), False)
    graph.explore_operation((1, 1, 4, 6), "1+1=2", (2, 4, 6), False)
    assert get_operation_sequence(graph, include_subgoals=False) == [
        "4+1=5",
        "4+6=10",
        "4+1=5",
        "1+1=2",
        "1+1=2",
    ]


def test_compute_gini():
    # The gini index should be low if all n-grams are distinct (though not exactly 0 for smal)
    assert np.isclose(compute_gini([(1, 2), (3, 4), (5, 6), (7, 8)]), 0.25)
    assert np.isclose(
        compute_gini([(2, 1), (1, 2), (2, 3), (3, 2), (3, 4), (4, 3)]),
        0.1667,
        atol=0.001,
    )
    assert np.isclose(
        compute_gini([(1, 2, 3), (1, 2, 4), (1, 2, 5), (1, 2, 6), (1, 2, 7)]),
        0.2,
        atol=0.001,
    )

    assert np.isclose(
        compute_gini([(1,), (1,), (1,), (1,), (2,), (2,)]), 0.667, atol=0.001
    )
    assert np.isclose(
        compute_gini([(10, 11), (10, 11), (10, 11), (10, 11), (12, 13), (12, 13)]),
        0.667,
        atol=0.001,
    )

    # for large n, the gini index should be close to 0
    assert np.isclose(compute_gini([(x,) for x in range(10000)]), 0.0, atol=0.001)


def test_get_random_op_sequence():

    # make sure the traces are the right length
    start_state = (1, 1, 2, 8)
    n_operations = 8
    random_sequence = get_random_op_sequence(
        start_state, n_operations, return_code=False
    )
    assert len(random_sequence) == n_operations

    n_operations = 14
    random_sequence = get_random_op_sequence(
        start_state, n_operations, return_code=False
    )
    assert len(random_sequence) == n_operations

    # make sure the code is runnable
    n_operations = 12
    code = get_random_op_sequence(start_state, n_operations, return_code=True)
    graph = run_code(code)
    assert isinstance(graph, GraphBuilder)


def test_count_error_types():
    errors = [
        {
            "Problems": [
                "PROBLEM TYPE: Operation runnability from curr_state. DESCRIPTION: The operation '1+2=3' is not runnable from the current state (1, 1, 2, 8). The operation requires the current state to be (1, 2, 3, 8) or (1, 1, 3, 8), but the current state is (1, 1, 2, 8).",
            ]
        }
    ]
    type_counts = count_error_types(errors)
    assert type_counts["runnability_errors"] == 1
    assert type_counts["total_errors"] == 1

    errors = [
        {
            "Problems": [
                "PROBLEM TYPE: Operation runnability from curr_state. DESCRIPTION:",
                "PROBLEM TYPE: Resulting state calculation error. DESCRIPTION:",
                "PROBLEM TYPE: Resulting state calculation error. DESCRIPTION:",
                "PROBLEM TYPE: Resulting state calculation error. DESCRIPTION:",
            ]
        }
    ]
    type_counts = count_error_types(errors)
    assert type_counts["runnability_errors"] == 1
    assert type_counts["state_calculation_errors"] == 3
    assert type_counts["total_errors"] == 4

    errors = []
    assert count_error_types(errors) == {}

    errors = None
    assert count_error_types(errors) == {}
