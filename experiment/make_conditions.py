# Read in stimuli from csv
import pandas as pd
import random


def main():
    # Read the CSV file
    problem_set = pd.read_csv("../../data/problem_set.csv")["Puzzles"].tolist()

    # convert each element in problem_set "N N N N" to [N, N, N, N]
    problem_set = [list(map(int, puzzle.split())) for puzzle in problem_set]

    # Define constant for num trials in task
    num_trials_in_task = 10

    # Get number of conditions
    num_conditions = len(problem_set) // num_trials_in_task

    # Create trial groups
    trial_groups = []
    for i in range(num_trials_in_task):
        trial_group = problem_set[i * num_conditions : (i + 1) * num_conditions]
        # Shuffle the trial group
        random.shuffle(trial_group)
        trial_groups.append(trial_group)

    # Create conditions
    conditions = []
    for i in range(num_conditions):
        condition = []
        for j in range(num_trials_in_task):
            condition.append(trial_groups[j][i])
        conditions.append(condition)

    # save as a javascript array
    with open("conditions.js", "w") as f:
        f.write("const conditions = " + str(conditions))


if __name__ == "__main__":
    main()
