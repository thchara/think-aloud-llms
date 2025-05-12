"""
Who checks the autochecker?
"""

import pandas as pd
from pyprojroot import here

from src.preproc.utils import run_code
from src.preproc.auto_checker import check_graph, get_problems_str
from src.preproc.reasoning_graph import GraphBuilder
from src.preproc.code_checking_tools import (
    parse_number,
    is_op_well_formatted,
    check_if_all_elements_in_state,
    can_run_from_curr_state,
    get_resulting_state,
    can_set_subgoal,
)


def test_on_broken_trials():
    df_corrected = pd.read_csv(here("data/manual-coded/correction-examples.csv"))
    broken_translations = df_corrected["translation"].tolist()
    graphs = [run_code(t) for t in broken_translations]
    for graph in graphs:
        if isinstance(graph, str):
            continue
        problems = check_graph(graph)
        assert len(problems) > 0, "Broken graph has no problems!"


def test_on_corrected_trials():
    df_corrected = pd.read_csv(here("data/manual-coded/correction-examples.csv"))
    correct_translations = df_corrected["fixed_translation"].tolist()
    graphs = [run_code(t) for t in correct_translations]
    for graph in graphs:
        assert isinstance(graph, GraphBuilder), "Correct example not runnable!"
        problems = check_graph(graph)
        assert len(problems) == 0, f"Problems: {get_problems_str(problems)}"


def test_on_in_context_examples():
    df_in_context = pd.read_csv(here("data/manual-coded/in-context-examples.csv"))
    in_context_translations = df_in_context["annotation"].tolist()
    graphs = [run_code(t) for t in in_context_translations]
    for graph in graphs:
        problems = check_graph(graph)
        assert len(problems) == 0, f"Problems: {get_problems_str(problems)}"


def test_parse_number():
    # valid numbers
    assert parse_number("1", "1+1=2") == (True, 1)
    assert parse_number("1.0", "1.0+1.0=2.0") == (True, 1.0)
    assert parse_number("12", "12+1=13") == (True, 12)

    # invaild numbers
    assert not parse_number("1a", "1a+1=2")[0]
    assert not parse_number("1+", "1++1=2")[0]
    assert not parse_number(".", "1++1=2")[0]
    assert not parse_number("asdf", "1++1=2")[0]


def test_is_well_formatted():

    # well-formatted
    assert is_op_well_formatted("1+1=2")[0]
    assert is_op_well_formatted("13-7=6")[0]
    assert is_op_well_formatted("13/7=1.8571428571428572")[0]
    assert is_op_well_formatted("(1+1)*2=4")[0]
    assert is_op_well_formatted("3.5+5.6=9.1")[0]

    # not well-formatted
    assert not is_op_well_formatted("1+1=2+1=3")[0]
    assert not is_op_well_formatted("1*2*3*4")[0]
    assert not is_op_well_formatted("1+twelve=13")[0]


def test_check_if_all_elements_in_state():
    # should return True
    assert check_if_all_elements_in_state(["1", "2"], ("1", "2", "3")) == (True, [])
    assert check_if_all_elements_in_state(["1", "1"], ("1", "1", "2", "3")) == (
        True,
        [],
    )
    assert check_if_all_elements_in_state(["3", "3", "3"], ("1", "3", "3", "3")) == (
        True,
        [],
    )

    # should return False
    assert check_if_all_elements_in_state(["1", "2", "3"], ("1", "2")) == (
        False,
        ["3"],
    )
    assert check_if_all_elements_in_state(["1", "1"], ("1", "2")) == (
        False,
        ["1"],
    )
    assert check_if_all_elements_in_state(["1", "1", "1"], ("1", "1", "2")) == (
        False,
        ["1"],
    )
    assert check_if_all_elements_in_state(["1", "1", "1"], ("1", "2")) == (
        False,
        ["1", "1"],
    )


def test_can_run_from_curr_state():

    # should return True
    assert can_run_from_curr_state((1, 1), "1+1=2", (1,), (1,))[0]
    assert can_run_from_curr_state((12, 7), "12/7=1.7142857142857142", (12,), (12,))[0]
    assert can_run_from_curr_state((12, 7), "12/7=8", (12,), (12,))[0]
    assert can_run_from_curr_state((12, 7), "12*7=84", (12,), (12,))[0]
    assert can_run_from_curr_state((12, 7), "12-7=5", (12,), (12,))[0]
    assert can_run_from_curr_state(
        (1, 2, 3.33), "2-3.33=-1.33", (1, 2, 3.33), (1, 2, 3.33)
    )[0]
    assert can_run_from_curr_state((1, -2), "1*(-2)=-2", (1, -2), (1, -2))[0]
    assert can_run_from_curr_state((1, -2), "1*(-2)=-2", (1, -2), (1, -2))[0]

    # should return False
    assert not can_run_from_curr_state((1, 2), "1+1=2", (1,), (1,))[0]
    assert not can_run_from_curr_state((5, 8), "5.5*8=44", (5,), (5,))[0]
    assert not can_run_from_curr_state((2, 2), "2+2+2=6", (2,), (2,))[0]


def test_get_resulting_state():
    assert get_resulting_state((1, 1), "1+1=2", False)[0] == (2,)
    assert get_resulting_state((1, 3.33333333), "1+3.33333333=4.33333333", False)[
        0
    ] == (4.33,)
    assert get_resulting_state((1, 2, 3, 4), "1/2=0.5", False)[0] == (0.5, 3, 4)
    assert get_resulting_state((1, 2, 3, 4), "1+2=3", False)[0] == (3, 3, 4)
    assert get_resulting_state((1, -2, 3), "3*(-2)=-6", False)[0] == (-6, 1)
    assert get_resulting_state((1, 2, 3, 4), "1+2=5", True)[0] == (3, 4, 5)


def test_can_set_subgoal():
    # settable
    assert can_set_subgoal((12, 12), (24,)) == (True, "The subgoal can be set.")
    assert can_set_subgoal((11,), (24,)) == (True, "The subgoal can be set.")
    assert can_set_subgoal((3, 8), (24,)) == (True, "The subgoal can be set.")
    assert can_set_subgoal((1, 11, 12), (23, 1)) == (True, "The subgoal can be set.")

    # not settable
    assert not can_set_subgoal(1, (24,))[0]
    assert not can_set_subgoal("a string", (23, 2))[0]
    assert not can_set_subgoal((23, 2), "a string")[0]
