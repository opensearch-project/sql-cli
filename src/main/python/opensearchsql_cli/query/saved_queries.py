"""
Saved Queries Management

This module provides functionality to save, load, and list query results.
"""

import os
import json
import traceback
from rich.console import Console
from datetime import datetime
from .execute_query import ExecuteQuery

# Create a console instance for rich formatting
console = Console()


class SavedQueries:
    """
    Class for managing saved queries and their results
    """

    def __init__(self, base_dir=None):
        """
        Initialize SavedQueries instance

        Args:
            base_dir: Base directory for saved queries files (default: root directory/save_query)
        """
        if base_dir is None:
            module_dir = os.path.dirname(__file__)
            self.base_dir = os.path.join(module_dir, "save_query")
        else:
            self.base_dir = base_dir

        # Ensure the directory exists
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir)
            except OSError:
                console.print(
                    f"[bold yellow]WARNING:[/bold yellow] [yellow]Could not create directory[/yellow] {self.base_dir}"
                )

        # Define file path for saved queries
        self.saved_file = os.path.join(self.base_dir, "saved.txt")

        # Create file if it doesn't exist
        if not os.path.exists(self.saved_file):
            try:
                with open(self.saved_file, "w") as f:
                    json.dump({}, f)
            except IOError:
                console.print(
                    f"[bold yellow]WARNING:[/bold yellow] [yellow]Could not create file[/yellow] {self.saved_file}"
                )

    def _load_saved_data(self):
        """
        Load saved queries data from file

        Returns:
            dict: Dictionary of saved queries
        """
        try:
            with open(self.saved_file, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return {}

    def _save_data(self, data):
        """
        Save queries data to file

        Args:
            data: Dictionary of saved queries

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.saved_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except IOError:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Could not write to file[/red] {self.saved_file}"
            )
            return False

    def save_query(self, name, query, language):
        """
        Save a query

        Args:
            name: Name to save the query under
            query: The query string
            language: Query language (PPL or SQL)

        Returns:
            bool: - True if success, else False
        """
        # Load existing saved queries
        saved_data = self._load_saved_data()

        # Check if name already exists
        if name in saved_data:
            console.print(f"A query with name '[green]{name}[/green]' already exists.")
            console.print(f"[red]\nUse a different name or replace it.[/red]")
            return False

        # Add new saved query
        saved_data[name] = {
            "query": query,
            "language": language,
            "timestamp": datetime.now().isoformat(),
        }

        # Save updated data
        if self._save_data(saved_data):
            console.print(f"Query saved as '[green]{name}[/green]'")
            return True
        else:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Could not save query[/red] [white](name: {name})[/white"
            )
            return False

    def replace_query(self, name, query, language):
        """
        Replace an existing saved query

        Args:
            name: Name of the query to replace
            query: The new query string
            language: Query language (PPL or SQL)

        Returns:
            bool: True if successful, False otherwise
        """
        # Load existing saved queries
        saved_data = self._load_saved_data()

        # Check if name exists
        if name not in saved_data:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]No query named[/red] '[white]{name}[/white]' [red]exists.[/red]"
            )
            return False

        # Update saved query
        saved_data[name] = {
            "query": query,
            "language": language,
            "timestamp": datetime.now().isoformat(),
        }

        # Save updated data
        if self._save_data(saved_data):
            console.print(f"Query '[green]{name}[/green]' replaced")
            return True
        else:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Failed to replace query[/red] '[green]{name}[/green]'"
            )
            return False

    def load_query(self, name):
        """
        Load a saved query

        Args:
            name: Name of the query to load

        Returns:
            tuple: (bool, dict) - (success, query_data)
        """
        # Load existing saved queries
        saved_data = self._load_saved_data()

        # Check if name exists
        if name not in saved_data:
            console.print(
                f"[bold red]ERROR:[/bold red] Saved Query '[green]{name}[/green]' does not exist."
            )
            return (False, None)

        return (True, saved_data[name])

    def remove_query(self, name):
        """
        Remove a saved query

        Args:
            name: Name of the query to remove

        Returns:
            bool: True if successful, False otherwise
        """
        # Load existing saved queries
        saved_data = self._load_saved_data()

        # Check if name exists
        if name not in saved_data:
            console.print(
                f"[bold red]ERROR:[/bold red] Saved Query '[green]{name}[/green]' does not exist."
            )
            return False

        # Remove the query
        del saved_data[name]

        # Save updated data
        if self._save_data(saved_data):
            console.print(f"Query '[green]{name}[/green]' removed")
            return True
        else:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Unable to remove[/red] '[green]{name}[/green]'"
            )
            return False

    def list_queries(self):
        """
        List all saved queries

        Returns:
            dict: Dictionary of saved queries
        """
        return self._load_saved_data()

    def saving_query(self, name, latest_query, language_mode):
        """
        Save a query with confirmation for overwriting if it already exists

        Args:
            name: Name to save the query under
            latest_query: The query string
            language_mode: Query language (PPL or SQL)

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if there's a query to save
        if not latest_query:
            console.print(
                "[bold red]ERROR:[/bold red] [red]Please execute a query first.[/red]"
            )
            return False

        # Check if name already exists
        saved_data = self._load_saved_data()
        if name in saved_data:
            # Ask user to choose another name or replace it
            console.print(
                f"A query with name '[green]{name}[/green]' already exists. [red]\nUse a different name or replace it.[/red]"
            )
            console.print(
                f"Do you want to replace saved query '[green]{name}[/green]'? (y/n): ",
                end="",
            )
            confirm = input().lower()
            if confirm == "y" or confirm == "yes":
                return self.replace_query(name, latest_query, language_mode)
            else:
                console.print(
                    f"Query '[green]{name}[/green]' was [red]NOT[/red] replaced."
                )
                return False
        else:
            # Save new query
            return self.save_query(name, latest_query, language_mode)

    def loading_query(self, name, connection, format="table", is_vertical=False):
        """
        Load and execute a saved query

        Args:
            name: Name of the query to load
            connection: Connection object to execute the query
            format: Output format (json, table, csv)
            is_vertical: Whether to display results in vertical format

        Returns:
            bool: True if successful, False otherwise
        """

        success, query_data = self.load_query(name)

        if not success:
            return False, "", "", ""

        query = query_data.get("query", "")
        language = query_data.get("language", "PPL")
        is_ppl_mode = language.upper() == "PPL"
        is_explain = query.strip().lower().startswith("explain")

        try:
            # Execute query using ExecuteQuery class
            success, result, formatted_result = ExecuteQuery.execute_query(
                connection,
                query,
                is_ppl_mode,
                is_explain,
                format,
                is_vertical,
                console.print,
            )
            return success, query, formatted_result, language

        except Exception as e:
            console.print(
                f"[bold red]ERROR:[/bold red] [red] Unable to execute [/red] {e}"
            )
            traceback.print_exc()
            return False, "", "", ""

    def removing_query(self, name):
        """
        Remove a saved query with confirmation

        Args:
            name: Name of the query to remove

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if the query exists first
        saved_queries = self.list_queries()
        if name not in saved_queries:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Query[/red] '[green]{name}[/green]' [red]not found.[/red]"
            )
            return False

        # Ask for confirmation before removing
        console.print(
            f"Are you sure you want to remove saved query '[green]{name}[/green]'? (y/n): ",
            end="",
        )
        confirm = input().lower()
        if confirm == "y" or confirm == "yes":
            return self.remove_query(name)
        else:
            console.print(f"Query '[green]{name}[/green]' was [red]NOT[/red] removed.")
            return False

    def list_saved_queries(self):
        """
        List all saved queries with formatted output

        Returns:
            bool: True if queries were found and listed, False otherwise
        """
        saved_queries = self.list_queries()

        if not saved_queries:
            console.print("[yellow]No saved queries found.[/yellow]")
            return False

        for name, data in saved_queries.items():
            query = data.get("query", "Unknown")
            timestamp = data.get("timestamp", "Unknown")

            if timestamp != "Unknown":
                try:
                    # Convert ISO format to datetime object
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            console.print(f"\n- [green]{name}[/green]")
            console.print(f"\t[yellow]{query}[/yellow]")
            console.print(f"\t[dim white]{timestamp}[/dim white]")

        return True
