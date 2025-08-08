import json
import re


class ExplainResults:
    """
    Class for formatting explain results
    """

    def explain_legacy(result):
        """
        Format legacy explain

        Args:
            result: legacy explain result

        Returns:
            string: format_result
        """

        data = json.loads(result)

        fields_str = data["root"]["description"]["fields"]
        fields_list = [
            f.strip() for f in fields_str.strip("[]").split(",") if f.strip()
        ]
        data["root"]["description"]["fields"] = fields_list

        # Extract the request string
        request_str = data["root"]["children"][0]["description"]["request"]
        match = re.match(r"(\w+)\((.*)\)", request_str)

        # Parse the request string into components
        if match:
            request_type = match.group(1)  # "OpenSearchQueryRequest"
            inner = match.group(2)  # inside the parentheses

            # Split by comma + space only on top level
            parts = re.split(r", (?=\w+=)", inner)

            request_obj = {}

            for part in parts:
                key, val = part.split("=", 1)

                # Parse JSON for sourceBuilder
                if key == "sourceBuilder":
                    val_obj = json.loads(val)
                else:
                    val_obj = val
                request_obj[key] = val_obj

            # Update the request structure
            data["root"]["children"][0]["description"]["request"] = {
                request_type: request_obj
            }

        explain_result = json.dumps(data, indent=2)
        return explain_result

    def explain_calcite(result):
        """
        Format calcite explain

        Args:
            result: calcite explain result

        Returns:
            string: format_result
        """

        data = json.loads(result)

        # Process logical plan dynamically
        logical_str = data["calcite"]["logical"]
        logical_structured = parse_plan_tree(logical_str)

        # Process physical plan dynamically
        physical_str = data["calcite"]["physical"]
        physical_structured = parse_plan_tree(physical_str)

        # Update the whole data structure
        data["calcite"]["logical"] = logical_structured
        data["calcite"]["physical"] = physical_structured

        explain_result = json.dumps(data, indent=2)
        return explain_result


def parse_plan_tree(plan_str):
    """
    Dynamically parse a plan tree string into structured format.

    Args:
        plan_str (str): The plan string with operators and their parameters

    Returns:
        dict: Parsed plan structure
    """
    if not plan_str or not plan_str.strip():
        return {}

    result = {}
    lines = plan_str.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract operator name and parameters
        operator_match = re.match(r"(\w+)\((.*)\)$", line)
        if operator_match:
            operator_name = operator_match.group(1)
            params_str = operator_match.group(2)

            # Parse dynamically
            params = parse_parameters(params_str)
            result[operator_name] = params

    return result


def parse_respecting_nesting(content, target_char, split_mode=True):
    """
    Parse content while respecting nested brackets, parentheses, braces, and quotes.
    Can either split on target_char or find first occurrence of target_char.

    Args:
        content (str): Content to parse
        target_char (str): Character to split on or find
        split_mode (bool): If True, split on target_char. If False, find first occurrence.

    Returns:
        list or int: List of split elements if split_mode=True, position if split_mode=False (-1 if not found)
    """
    if not content.strip():
        return [] if split_mode else -1

    elements = [] if split_mode else None
    current_element = "" if split_mode else None
    bracket_depth = 0
    paren_depth = 0
    brace_depth = 0
    in_quotes = False
    quote_char = None

    i = 0
    while i < len(content):
        char = content[i]

        if char in ['"', "'"] and not in_quotes:
            in_quotes = True
            quote_char = char
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
        elif not in_quotes:
            if char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif (
                char == target_char
                and bracket_depth == 0
                and paren_depth == 0
                and brace_depth == 0
            ):
                if split_mode:
                    # A separator
                    if current_element.strip():
                        elements.append(current_element.strip())
                    current_element = ""
                    i += 1
                    continue
                else:
                    # Found the first unescaped character
                    return i

        if split_mode:
            current_element += char
        i += 1

    if split_mode:
        # Last element
        if current_element.strip():
            elements.append(current_element.strip())
        return elements
    else:
        # Character not found
        return -1


def split_respecting_nesting(content, separator):
    """
    Split content on separator while respecting nested structures.

    Args:
        content (str): Content to split
        separator (str): Character to split on

    Returns:
        list: List of split elements

    Example:
        Input: "table=[[OpenSearch, employees]], PushDownContext=[[PROJECT->[name]]]"
        Output: ["table=[[OpenSearch, employees]]", "PushDownContext=[[PROJECT->[name]]]"]
    """
    return parse_respecting_nesting(content, separator, split_mode=True)


def find_first_unescaped_char(content, target_char):
    """
    Find the first occurrence of target_char that's not inside nested structures.

    Args:
        content (str): Content to search in
        target_char (str): Character to find

    Returns:
        int: Position of first unescaped character, or -1 if not found

    Example:
        Input: "table=[[OpenSearch, employees]]", "="
        Output: 5
    """
    return parse_respecting_nesting(content, target_char, split_mode=False)


def parse_parameters(params_str):
    """
    Dynamically parse parameter string into structured format.

    Args:
        params_str (str): Parameter string

    Returns:
        dict: Parsed parameters

    Example:
        Input: "group=[{}], sum(aa)=[SUM($0)]"
        Output: {
            "group": [{}],
            "sum(aa)": "[SUM($0)]"
        }
    """
    if not params_str or not params_str.strip():
        return {}

    params = {}

    # Use the common splitting function
    param_parts = split_respecting_nesting(params_str, ",")

    for param_part in param_parts:
        param_part = param_part.strip()
        if not param_part:
            continue

        # Find the first unescaped '=' sign
        eq_pos = find_first_unescaped_char(param_part, "=")

        if eq_pos > 0:
            key = param_part[:eq_pos].strip()
            value = param_part[eq_pos + 1 :].strip()

            # Special handling for JSON values
            if value.startswith("{") and value.endswith("}"):
                try:
                    # Try to parse as JSON
                    json_obj = json.loads(value)
                    params[key] = json_obj
                except json.JSONDecodeError:
                    # If fails then treat as regular parameter value
                    params[key] = parse_parameter_value(value)
            else:
                params[key] = parse_parameter_value(value)
        else:
            # No valid '=' found, treat as boolean parameter
            params[param_part] = True

    return params


def parse_arrow_structure(content):
    """
    Parse PROJECT->[field1, field2, ...] structure.

    Args:
        content (str): Content to parse

    Returns:
        dict: Parsed structure

    Example:
        Input: "PROJECT->[field1, field2, ...]"
        Output: {"PROJECT->": ["field1", "field2", ...]}
    """
    arrow_pos = content.find("->")
    if arrow_pos <= 0:
        return content

    key = content[:arrow_pos].strip()
    value_part = content[arrow_pos + 2 :].strip()

    if value_part.startswith("[") and value_part.endswith("]"):
        # Parse the array part
        array_content = value_part[1:-1].strip()
        if array_content:
            fields = split_respecting_nesting(array_content, ",")
            return {key + "->": [field.strip() for field in fields]}
        else:
            return {key + "->": []}
    else:
        return {key + "->": value_part}


def parse_parameter_value(value_str):
    """
    Parse a parameter value, handling arrays, nested structures, function calls, etc.

    Args:
        value_str (str): Value string to parse

    Returns:
        Parsed value (list, dict, or string)
    """
    value_str = value_str.strip()

    # Handle arrays
    if value_str.startswith("[") and value_str.endswith("]"):
        inner_content = value_str[1:-1].strip()

        if not inner_content:
            return []
        elif inner_content == "{}":
            return [{}]
        else:
            # Check if it contains -> syntax (either direct or nested)
            if "->" in inner_content:
                # Direct arrow syntax like PROJECT->[...]
                if not inner_content.startswith("["):
                    return parse_arrow_structure(inner_content)

                # Complex array with nested arrow structures
                items = split_respecting_nesting(inner_content, ",")
                parsed_items = []

                for item in items:
                    item = item.strip()
                    if item.startswith("[") and item.endswith("]") and "->" in item:
                        # Nested structure like [PROJECT->[...]]
                        nested_inner = item[1:-1].strip()
                        parsed_items.append(parse_arrow_structure(nested_inner))
                    else:
                        parsed_items.append(parse_parameter_value(item))

                return parsed_items

            # Check if it's a simple array (no complex nested structures)
            elif not any(
                item.strip().startswith("[") and item.strip().endswith("]")
                for item in split_respecting_nesting(inner_content, ",")
            ):
                # Keep simple arrays as string representation
                return value_str

            # Parse other complex array elements
            else:
                items = split_respecting_nesting(inner_content, ",")
                return [parse_parameter_value(item.strip()) for item in items]

    # Only parse as function calls if they contain key=value parameters
    elif (
        "(" in value_str
        and value_str.endswith(")")
        and "=" in value_str[value_str.find("(") + 1 : value_str.rfind(")")]
    ):
        paren_pos = value_str.find("(")
        func_name = value_str[:paren_pos].strip()
        params_str = value_str[paren_pos + 1 : -1].strip()

        if params_str:
            params = parse_parameters(params_str)
            return {func_name: params}
        else:
            return {func_name: {}}

    else:
        return value_str
