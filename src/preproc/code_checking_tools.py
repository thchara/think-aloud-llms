from src.preproc.reasoning_graph_utils import tokenize, get_sub_operations
import traceback
import json


def parse_number(number: str, operation: str):
    """
    Check if a number is valid.
    """
    try:
        number = eval(number)
        return True, number
    except Exception:
        return (
            False,
            f"All operations must consist of valid numbers. Found {number} in operation {operation}. Please make sure all the numbers in the operation field of explore_operation are valid integers or floats.",
        )


def is_op_well_formatted(operation: str) -> tuple[bool, str]:
    """
    Tool to check if an operation is well-formatted.

    Args:
        operation (str): The operation to be checked.
    Returns:
        bool: True if the operation is well-formatted, False otherwise.
        str: A message indicating if the operation is well-formatted, and if not, a suggestion for how to fix it.
    """
    try:
        lhs = operation[: operation.rfind("=")]
        elements = tokenize(lhs)
        for element in elements:
            if (
                element not in ["+", "-", "*", "/", "(", ")"]
                and not parse_number(element, operation)[0]
            ):
                return parse_number(element, operation)
    # return error message if operation is not well-formatted
    except Exception as e:
        return False, e
    if operation.count("=") != 1:
        return False, "The operation does not contain exactly one '='."

    return True, "The operation is well-formatted."


def check_if_all_elements_in_state(elements: list[str], state: tuple) -> bool:
    """
    Check if all elements are in the state.
    """
    # check if any of the elements are not in curr_state
    unused_numbers = list(state)
    elements_not_in_curr_state = []
    for element in elements:
        if element in unused_numbers:
            unused_numbers.remove(element)
        else:
            elements_not_in_curr_state.append(element)
    return len(elements_not_in_curr_state) == 0, elements_not_in_curr_state


def can_run_from_curr_state(
    curr_state, operation, start_state, new_state
) -> tuple[bool, str]:
    """
    Tool to check if an operation can be run from the current state.
    Args:
        curr_state: The current state of the graph.
        operation: The operation to be applied to the graph.
        start_state: The start state of the graph.
        new_state: The new state of the graph.
    Returns:
        bool: True if the operation can be run from the current state, False otherwise.
        str: A message indicating if the operation can be run from the current state, and if not, a suggestion for how to get to a state where the operation can be run.
    """
    # convert curr_state to tuple and sort it
    try:
        curr_state = sorted(curr_state)
        start_state = sorted(start_state)
    except Exception:
        return (
            False,
            "The current state, start state, and new state must be valid tuples of numbers.",
        )
    elements = [
        parse_number(element, operation)[1]
        for element in tokenize(operation[: operation.rfind("=")])
        if parse_number(element, operation)[0]
    ]

    # check if any of the elements are not in curr_state
    can_run_from_curr_state, elements_not_in_curr_state = (
        check_if_all_elements_in_state(elements, curr_state)
    )
    if can_run_from_curr_state:
        return True, "The operation can be run safely from the current state."
    else:
        # check if all of the elements of the operation are in start_state
        if (
            start_state is not None
            and check_if_all_elements_in_state(elements, start_state)[0]
        ):
            return (
                False,
                f"You are missing the elements {tuple(elements_not_in_curr_state)} in curr_state {tuple(curr_state)}, but all elements needed for the operation are in the start_state {tuple(start_state)}. Consider moving to start_state before running the operation from there.",
            )
        # check if all of the elements in curr_state are in new_state
        elif (
            new_state is not None
            and check_if_all_elements_in_state(elements, new_state)[0]
        ):
            return (
                False,
                f"You are missing the elements {tuple(elements_not_in_curr_state)} in curr_state {tuple(curr_state)}, but all elements needed for the operation are in the new state {tuple(new_state)}. Consider moving to new_state before running the operation from there.",
            )
        else:
            return (
                False,
                f"You are missing the elements {tuple(elements_not_in_curr_state)} in curr_state {tuple(curr_state)}. They were not found in start_state{' ' + str(tuple(start_state)) if start_state is not None else ''} or new_state{' ' + str(tuple(new_state)) if new_state is not None else ''}. Make sure you are not inventing new elements. Consider ways the participant might have made the required numbers. Consider also that the participant might be setting a subgoal rather than exploring an operation.",
            )


def get_resulting_state(
    curr_state: str, operation: str, result_calc_error: bool = False
) -> str:
    """
    Tool to get the resulting state of a graph after an operation is applied.
    Args:
        curr_state (str): The current state of the graph.
        operation (str): The operation to be applied to the graph.
        result_calc_error (bool): Whether the result of the calculation the participant made is incorrect. defaults to False.
    Returns:
        str: The resulting state of the graph.
    """
    sub_operations = get_sub_operations(operation[: operation.rfind("=")])
    # remove elements from curr_state that are in sub_operations
    resulting_state = list(curr_state)
    tokenized_lhs = tokenize(operation[: operation.rfind("=")])
    for element in tokenized_lhs:
        try:
            element = eval(element)
            if element in resulting_state:
                resulting_state.remove(element)
        except Exception:
            pass

    # add result of operation to curr_state
    if result_calc_error:
        result = eval(operation[operation.rfind("=") + 1 :])
    else:
        try:
            result = sub_operations[-1][-1]
        except Exception:
            print(f"Error getting result of operation {operation}")
            print(f"sub_operations: {sub_operations}")
            print(f"curr_state: {curr_state}")
            print(traceback.format_exc())
            raise Exception(f"Missing sub-operation result of operation {operation}")

    result = round(result, 2)
    resulting_state = tuple(sorted(resulting_state + [result]))
    operation = operation[: operation.rfind("=")] + f"={result}"

    return resulting_state, operation


def can_set_subgoal(subgoal_state: tuple, state_after_subgoal: tuple) -> str:
    """
    tool to check if a subgoal can be set. use this tool before every time you want to call set_subgoal.

    args:
        subgoal_state: the current state of the graph (tuple)
        state_after_subgoal: the state that the participant is trying to reach after the subgoal is reached (tuple)
    returns:
        str: a message indicating if the subgoal can be set and the result
    """
    try:
        assert isinstance(subgoal_state, tuple) or isinstance(subgoal_state, list)
        assert isinstance(state_after_subgoal, tuple) or isinstance(
            state_after_subgoal, list
        )
        subgoal_state = tuple(subgoal_state)
        state_after_subgoal = tuple(state_after_subgoal)
        return True, "The subgoal can be set."
    except Exception:
        return (
            False,
            f"Error parsing input:\n{traceback.format_exc()}\nplease provide input in the format: e.g., {{'subgoal_state': (x, y), 'state_after_subgoal': (24,)}}",
        )


if __name__ == "__main__":
    input_json = json.dumps(
        {
            "curr_state": (1, 2, 12),
            "operation": "12*2=36",
            "start_state": (1, 2, 3, 4),
            "result_calc_error": True,
        }
    )
