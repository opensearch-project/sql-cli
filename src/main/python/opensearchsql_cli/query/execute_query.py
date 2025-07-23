"""
Query Execution

This module provides functionality for executing queries and formatting results.
"""

from rich.console import Console
from rich.status import Status
from rich.markup import escape
from .query_results import QueryResults
from .explain_results import ExplainResults

# Create a console instance for rich formatting
console = Console()


class ExecuteQuery:
    """
    Class for executing queries and formatting results
    """

    @staticmethod
    def execute_query(
        connection,
        query,
        is_ppl_mode,
        is_explain,
        format,
        is_vertical=False,
        print_function=None,
    ):
        """
        Execute a query and format the result

        Args:
            connection: Connection object to execute the query
            query: Query string to execute
            is_ppl_mode: Whether to use PPL mode (True) or SQL mode (False)
            is_explain: Whether this is Explain or Execute query
            format: Output format (json, table, csv)
            is_vertical: Whether to display results in vertical format
            print_function: Function to use for printing (default: console.print)

        Returns:
            tuple: (success, result, formatted_result)
        """
        if print_function is None:
            print_function = console.print

        console.print(f"\nExecuting: [yellow]{query}[/yellow]\n")

        # Execute the query
        with console.status("Executing the query...", spinner="dots"):
            result = connection.query_executor(query, is_ppl_mode, format)

        # Errors handling
        # print_function(f"Before format: \n" + escape(result) + "\n")
        if result.startswith("Invalid query") or result.startswith(
            "queryExecution Error"
        ):
            if "index_not_found_exception" in result:
                print_function("[bold red]Index does not exist[/bold red]")
            elif "SyntaxCheckException" in result:
                error_parts = result.split("SyntaxCheckException:", 1)
                print_function(
                    f"[bold red]Syntax Error: [/bold red][red]{escape(error_parts[1].strip())}[/red]\n"
                )
            elif "SemanticCheckException" in result:
                error_parts = result.split("SemanticCheckException:", 1)
                print_function(
                    f"[bold red]Semantic Error: [/bold red][red]{escape(error_parts[1].strip())}[/red]\n"
                )
            elif '"statement" is null' in result:
                print_function("[bold red]Statement is null[/bold red]")
            else:
                print_function(f"[bold red]Error:[/bold red] {escape(str(result))}")
            return False, result, result

        print_function(f"Result:\n")
        with console.status("Formatting results...", spinner="dots"):
            # For explain query
            if is_explain:
                if "calcite" in result:
                    explain_result = ExplainResults.explain_calcite(result)
                    print_function(explain_result)
                    return True, result, result
                elif "root" in result:
                    explain_result = ExplainResults.explain_legacy(result)
                    print_function(explain_result)
                    return True, result, result
                else:
                    print_function(f"{result}")
            # For execute query
            else:
                if format.lower() == "table":
                    table_data = QueryResults.table_format(result, is_vertical)
                    if "error" in table_data and table_data["error"]:
                        print_function(
                            f"[bold red]Error:[/bold red] {table_data['message']}"
                        )
                        return False, result, table_data["result"]
                    else:
                        # Display table
                        QueryResults.display_table_result(table_data, print_function)
                        return True, result, str(table_data)
                elif format.lower() == "csv":
                    # return the result with white color
                    # because Rich automatically pretty-printing
                    print_function(f"[white]{escape(result)}[/white]")
                    return True, result, result
                else:
                    # For other formats, use the result directly
                    # Right now, only JSON
                    print_function(f"{escape(result)}")
                    return True, result, result
