import json
from pygments import highlight
from pygments.lexer import RegexLexer
from pygments.token import *
from pygments.formatters import TerminalFormatter

class CalcitePlanLexer(RegexLexer):
    name = 'CalcitePlan'
    tokens = {
        'root': [
            (r'^=.*', Comment),
            (r'[A-Z][a-z]\w+', Name.Function),
            # (r'\[[^\]]*\]', Number),
            (r'\$[\d\w]+', Name.Variable),
            (r'"[^"]*"', String),
            (r'\d+', Number),
            (r'[a-zA-Z_][\w#\.]*=', Name.Attribute),
            (r'\s+', Text),
            (r'null', Keyword),
            (r'[\w\-]+', Text),
            (r'[^\w]', Punctuation),
        ]
    }

def process_physical_calcite_line(line):
    if "sourceBuilder=" not in line:
        return line
    
    start_idx = line.index("sourceBuilder=") + len("sourceBuilder=")
    
    stack = 0
    for i in range(start_idx, len(line)):
        if line[i] == '{':
            stack += 1
        elif line[i] == '}':
            stack -= 1
            if stack == 0:
                end_idx = i + 1
                break
    
    json_str = line[start_idx:end_idx]
    leading_space = len(line) - len(line.lstrip())
    indent_str = ' ' * leading_space
    
    try:
        parsed_json = json.loads(json_str)
        pretty_json = json.dumps(parsed_json, indent=2)
        pretty_json = '\n'.join(indent_str + line for line in pretty_json.splitlines()).lstrip('| ')
        return line[:start_idx] + pretty_json + line[end_idx:]
    except json.JSONDecodeError:
        return line


def format_calcite_explain(err):
    report = """= Calcite Plan =
== Logical ==
$LOGICAL

== Physical ==
$PHYSICAL"""
    logical_plan = err['calcite']['logical'].splitlines()
    logical_plan = '\n'.join(logical_plan)

    physical_plan = err['calcite']['physical'].splitlines()
    physical_plan = map(process_physical_calcite_line, physical_plan)
    physical_plan = '\n'.join(physical_plan)

    report = report.replace("$LOGICAL", logical_plan)
    report = report.replace("$PHYSICAL", physical_plan)
    highlighted = highlight(report, CalcitePlanLexer(), TerminalFormatter())
    return highlighted
