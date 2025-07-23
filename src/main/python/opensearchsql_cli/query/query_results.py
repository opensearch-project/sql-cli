"""
Query Result Handling

This module provides table formatting for query results.
Other formats are handled by the Java formatters in the SQL library.
"""

import json
from rich.console import Console
from rich.table import Table
from rich.box import HEAVY_HEAD

# Create a console instance for rich formatting
console = Console()


class QueryResults:
    """
    Class for formatting execute query results
    """

    def display_table_result(table_data, print_function=None):
        """
        Display table result using the provided print function or console.print

        Args:
            table_data: Dictionary containing table data from table_format
            print_function: Function to use for printing (default: console.print)
        """
        if print_function is None:
            print_function = console.print

        # Check if there's an error
        if "error" in table_data and table_data["error"]:
            print_function(f"[bold red]Error:[/bold red] {table_data['message']}")
            return

        # Print the message
        print_function(table_data["message"])

        # Print the table
        if "result" in table_data and (
            "calcite" in table_data["result"].lower()
            or "root" in table_data["result"].lower()
        ):
            # For explain results, just print the raw result
            print_function(table_data["result"])
        elif table_data.get("vertical", False) and "tables" in table_data:
            # For vertical format, print each table
            for table in table_data["tables"]:
                print_function(table)
                print_function("")  # Add a blank line between tables
        elif "table" in table_data:
            # For horizontal format, print the single table
            print_function(table_data["table"])
        else:
            # Fallback for unexpected data structure
            print_function("[bold red]Error:[/bold red] Unable to display table data")

        # Print warning if present
        if table_data.get("warning"):
            print_function(table_data["warning"])

    def table_format(result: str, vertical: bool = False):
        """
        Format the result as a table using Rich Table

        Args:
            result: JSON result string from Java in JDBC format
            vertical: Whether to force vertical output format (default: False)

        Returns:
            dict: Dictionary containing message, table object, and warning
        """
        try:
            data = json.loads(result)

            if isinstance(data, dict) and "schema" in data and "datarows" in data:
                # Extract schema and data
                schema = data["schema"]
                datarows = data["datarows"]
                total_hits = data["total"]
                cur_size = data["size"]

                # Create message
                message = f"Fetched {cur_size} rows with a total of {total_hits} hits"

                if vertical:
                    # Create a list to hold all record tables
                    record_tables = []

                    # Vertical format (one row per record)
                    for row_idx, row in enumerate(datarows):
                        record_table = Table(
                            title=f"RECORD {row_idx + 1}",
                            title_style="bold yellow",
                            box=HEAVY_HEAD,
                            show_header=False,
                            header_style="bold green",
                            show_lines=True,
                            border_style="bright_black",
                        )
                        record_table.add_column("Field", style="bold green")
                        record_table.add_column("Value", style="white")

                        for field_idx, field in enumerate(schema):
                            field_name = field.get("alias", field["name"])
                            value = row[field_idx] if field_idx < len(row) else "<null>"
                            value_str = str(value) if value is not None else "<null>"
                            record_table.add_row(field_name, value_str)

                        record_tables.append(record_table)

                    return {
                        "message": message,
                        "tables": record_tables,
                        "vertical": True,
                    }
                else:
                    # Horizontal format (traditional table)
                    table = Table(
                        box=HEAVY_HEAD,
                        show_header=True,
                        header_style="bold green",
                        show_lines=True,
                        border_style="bright_black",
                    )

                    # Add columns with styling
                    for field in schema:
                        field_name = field.get("alias", field["name"])
                        table.add_column(field_name, style="bold green")

                    # Add data rows
                    for row in datarows:
                        # Convert all values to strings
                        str_row = [
                            str(val) if val is not None else "<null>" for val in row
                        ]
                        table.add_row(*str_row, style="white")

                    return {"message": message, "table": table, "vertical": False}
            else:
                # If not in a recognized format, return as is
                console.print("[bold red]Error formatting.[/bold red]")
                return {"message": "Error formatting.", "error": True, "result": result}
        except json.JSONDecodeError:
            # If not valid JSON, return as is
            console.print("[bold red]Error decoding JSON.[/bold red]")
            return {"message": "Error decoding JSON.", "error": True, "result": result}
        except Exception as e:
            # Handle other exceptions
            console.print(f"[bold red]Error during formatting:[/bold red] {e}")
            return {
                "message": f"Error during formatting: {e}",
                "error": True,
                "result": result,
            }
