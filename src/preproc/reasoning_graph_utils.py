import re


# Enhanced tokenizer function to handle negative numbers
def tokenize(expression):
    tokens = []
    i = 0
    length = len(expression)
    while i < length:
        c = expression[i]
        if c.isspace():
            i += 1
            continue
        elif c in "+-":
            # Check if this is a unary operator
            if i == 0 or expression[i - 1] in "+-*/(":
                # Unary operator: part of a number
                num = c
                i += 1
                while i < length and (expression[i].isdigit() or expression[i] == "."):
                    num += expression[i]
                    i += 1
                tokens.append(num)
            else:
                # Binary operator
                tokens.append(c)
                i += 1
        elif c.isdigit() or c == ".":
            # Number
            num = ""
            while i < length and (expression[i].isdigit() or expression[i] == "."):
                num += expression[i]
                i += 1
            tokens.append(num)
        elif c in "*/()":
            # Operator or parenthesis
            tokens.append(c)
            i += 1
        else:
            raise ValueError(f"Invalid character '{c}' in expression")
    return tokens


# Precedence function remains the same
def precedence(op):
    if op == "+" or op == "-":
        return 1
    if op == "*" or op == "/":
        return 2
    return 0


# The apply_operator function remains mostly the same
def apply_operator(operands, operator, sub_operations):
    right = operands.pop()
    left = operands.pop()

    if operator == "+":
        result = left + right
    elif operator == "-":
        result = left - right
    elif operator == "*":
        result = left * right
    elif operator == "/":
        result = left / right

    # Convert result to int if it's a float with no decimal part
    if isinstance(result, float) and result.is_integer():
        result = int(result)

    operands.append(result)

    # Convert left and right to int if they are floats without decimal part
    if isinstance(left, float) and left.is_integer():
        left = int(left)
    if isinstance(right, float) and right.is_integer():
        right = int(right)

    # Store the sub-operation as a list [left operand, operator, right operand, result]
    sub_operations.append([left, operator, right, result])

    return result


# Updated evaluate_expression function to handle negative numbers
def evaluate_expression(tokens):
    operands = []
    operators = []
    sub_operations = []
    results = []

    def apply_pending_operators():
        while operators and operators[-1] != "(":
            result = apply_operator(operands, operators.pop(), sub_operations)
            results.append(result)

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # If it's a number (including negative numbers), push to operands stack
        if re.match(r"^[+-]?(\d+(\.\d+)?)$", token):
            if "." in token:
                operands.append(float(token))
            else:
                operands.append(int(token))

        # If it's an operator
        elif token in "+-*/":
            while (
                operators
                and operators[-1] != "("
                and precedence(operators[-1]) >= precedence(token)
            ):
                result = apply_operator(operands, operators.pop(), sub_operations)
                results.append(result)
            operators.append(token)

        # If it's a left parenthesis, push to operators stack
        elif token == "(":
            operators.append(token)

        # If it's a right parenthesis, solve the entire expression inside the parentheses
        elif token == ")":
            apply_pending_operators()
            if operators and operators[-1] == "(":
                operators.pop()  # Pop the '(' from the stack
            else:
                raise ValueError("Mismatched parentheses")
        else:
            raise ValueError(f"Unknown token '{token}'")
        i += 1

    # Apply remaining operators to remaining operands
    while operators:
        if operators[-1] == "(":
            raise ValueError("Mismatched parentheses")
        result = apply_operator(operands, operators.pop(), sub_operations)
        results.append(result)

    # The final result will be the last number in the operands stack
    return results, sub_operations


# Main function remains mostly the same
def get_sub_operations(expression):
    tokens = tokenize(expression)
    results, sub_operations = evaluate_expression(tokens)
    return sub_operations


# Testing the updated code with expressions involving negative numbers
if __name__ == "__main__":
    test_expressions = [
        "-3+3",
        "2+(-5)",
        "(9-4)*3+9",
        "-1*(2+3)*4",
        "5*-3",
        "4/(-2)",
        "3-(-3)",
    ]

    for expr in test_expressions:
        sub_operations = get_sub_operations(expr)
        print(f"Expression: {expr}")
        print("Sub-operations:")
        for op in sub_operations:
            print(op)
        print("-" * 30)
