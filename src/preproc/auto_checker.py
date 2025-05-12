from src.preproc.reasoning_graph import GraphBuilder
from src.preproc.code_checking_tools import (
    can_run_from_curr_state,
    is_op_well_formatted,
    can_set_subgoal,
    get_resulting_state,
)


def get_problems_str(problems: list[dict]) -> str:
    """
    Get the string representation of a list of problems.
    """
    problems_str = ""
    for action in problems:
        problems_str += f"\n\nAction: {action['Action']}.\nProblems:"
        for problem in action["Problems"]:
            problems_str += f"\n- {problem}"

    return problems_str.strip()


def get_recent_new_state(previous_actions: list[dict]) -> tuple:
    """
    Get the new state value from the operation and the current state.
    """
    # iterate backwards through the actions and find the first explore_operation
    for action in reversed(previous_actions):
        if action["type"] == "explore_operation":
            return action["resulting_state"]
    return None


def check_if_all_elements_in_state(elements: list[str], state: tuple) -> bool:
    """
    Check if all elements are in the state.
    """
    return all(element in state for element in elements)


def get_action_str(action: dict) -> str:
    """
    Get the string representation of an action.
    """
    if action["type"] == "explore_operation":
        return f"explore_operation(curr_state=curr_state,operation={action['operation']},resulting_state={action['resulting_state']},comment={action['comment']})"
    elif action["type"] == "set_subgoal":
        return f"set_subgoal(curr_state=curr_state,subgoal_state={action['subgoal_state']},state_after_subgoal={action['state_after_subgoal']})"
    else:
        return ""


def check_graph(graph: GraphBuilder):
    """
    Check if a graph is valid. If not, return a list of problems.
    """
    problems = []
    for i, action in enumerate(graph.actions):
        action_prob_dict = {"Action": get_action_str(action), "Problems": []}
        if action["type"] == "explore_operation":
            ## check if the operation is well-formatted - if not, provide feedback on how to fix it
            is_well_formatted, message = is_op_well_formatted(action["operation"])
            if not is_well_formatted:
                action_prob_dict["Problems"].append(
                    f"""PROBLEM TYPE: Operation formatting. DESCRIPTION: the operation {action['operation']} is not well-formatted. {message}"""
                )
                continue  # if the operation is not well-formatted, we don't need to check the other conditions

            ## check if the operation can be run from the current state - if not, provide feedback on which state to go to before running it
            can_run, message = can_run_from_curr_state(
                action["curr_state"],
                action["operation"],
                graph.start_state,
                get_recent_new_state(graph.actions[:i]),
            )
            if not can_run:
                action_prob_dict["Problems"].append(
                    f"""PROBLEM TYPE: Operation runnability from curr_state. DESCRIPTION: the operation `{action['operation']}` cannot be run from curr_state {action['curr_state']}. {message}"""
                )

            ## check if the resulting state is a valid successor of the current state - if not, provide the valid successor
            elif (
                action["resulting_state"]
                != get_resulting_state(
                    action["curr_state"],
                    action["operation"],
                    action["result_calc_error"],
                )[0]
            ):
                correct_resulting_state, correct_operation = get_resulting_state(
                    action["curr_state"],
                    action["operation"],
                    action["result_calc_error"],
                )
                action_prob_dict["Problems"].append(
                    f"""PROBLEM TYPE: Resulting state calculation error. DESCRIPTION: The resulting state {action['resulting_state']} provided is not the correct resulting state for the operation {action['operation']} from the current state {action['curr_state']}. The correct resulting_state is {correct_resulting_state}. You could fix this by changing the resulting state to {correct_resulting_state}. If you think the participant made a calculation error, make sure to set result_calc_error to True. If you think the participant misspoke or there was a transcription error (e.g. saying "2 times 1 is 3" when they probably meant "2 plus 1 is 3"), consider other possible interpretations of the transcript."""
                )

        elif action["type"] == "set_subgoal":
            ## check if the subgoal can be set
            can_set, message = can_set_subgoal(
                action["subgoal_state"], action["state_after_subgoal"]
            )
            if not can_set:
                action_prob_dict["Problems"].append(
                    f"PROBLEM TYPE: Subgoal setability. DESCRIPTION: The subgoal {action['subgoal_state']} cannot be set. {message}"
                )

        if action_prob_dict["Problems"]:
            problems.append(action_prob_dict)

    return problems


if __name__ == "__main__":
    from utils import run_code

    example_code = """start_state = (6, 6, 8, 12)
curr_state = start_state
graph = GraphBuilder(curr_state)
# 12 x 8 - participant is multiplying 12 by 8
new_state = graph.explore_operation(
    curr_state,
    operation="12*8=96",
    resulting_state=(6, 6, 96),
    comment="12 x 8 - participant is multiplying 12 by 8",
)
# 12 x 6 - participant is multiplying 12 by 6
new_state = graph.explore_operation(
    curr_state,
    operation="12*6=72",
    resulting_state=(6, 8, 72),
    comment="12 x 6 - participant is multiplying 12 by 6",
)
# plus 6 - participant is adding 6 to result
curr_state = graph.move_to_node(new_state)
new_state = graph.explore_operation(
    curr_state,
    operation="72+6=78",
    resulting_state=(8, 78),
    comment="plus 6 - participant is adding 6 to result",
)
# six multiplied by six - participant returned to start state and is now trying 6*6
curr_state = graph.move_to_node(start_state)
new_state = graph.explore_operation(
    curr_state,
    operation="6*6=36",
    resulting_state=(8, 12, 36),
    comment="six multiplied by six - participant returned to start state and is now trying 6*6",
)
# divided by 12 - looks like from result that participant is dividing 12 by 8
curr_state = graph.move_to_node(new_state)
new_state = graph.explore_operation(
    curr_state,
    operation="12/8=1.5",
    resulting_state=(1.5, 36),
    comment="# divided by 12 - looks like from result that participant is dividing 12 by 8",
)
# no further comment, but can see the division operation from result
curr_state = graph.move_to_node(new_state)
new_state = graph.explore_operation(
    curr_state,
    operation="36/1.5=24",
    resulting_state=(24,),
    comment="# no further comment, but can see the division operation from result",
)"""

    problems = check_graph(run_code(example_code).G)
    print(f"problems:")
    print("\n".join(problems))
