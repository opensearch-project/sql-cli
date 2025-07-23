"""
Interactive Shell

Handles interactive shell functionality for OpenSearch SQL CLI.
"""

import sys
import os
import traceback
from typing import Optional
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from pygments.lexers.sql import SqlLexer

from rich.console import Console
from rich.markup import escape
from .sql import sql_connection
from .query import ExecuteQuery
from .literals import Literals
from .config.config import config_manager
from .sql.sql_version import sql_version

# Create a console instance for rich formatting
console = Console()


class InteractiveShell:
    """
    Interactive Shell class for OpenSearch SQL CLI
    """

    def __init__(self, sql_connection, saved_queries):
        """
        Initialize the Interactive Shell instance

        Args:
            sql_connection: SQL connection instance
            saved_queries: SavedQueries instance
        """
        # Set up history file in the current directory name .cli_history
        self.histfile = os.path.join(os.path.dirname(__file__), ".cli_history")
        self.history_length = float("inf")

        # Create history file if it doesn't exist
        if not os.path.exists(self.histfile):
            try:
                open(self.histfile, "w").close()
            except IOError:
                console.print(
                    f"[bold yellow]WARNING:[/bold yellow] [yellow]Unable to create history file[/yellow] {self.histfile}"
                )

        # Store references to connection and saved queries
        self.sql_connection = sql_connection
        self.saved_queries = saved_queries

        # State variables
        self.language_mode = "PPL"
        self.is_ppl_mode = True
        self.format = "table"
        self.is_vertical = False
        self.latest_query = None

    @staticmethod
    def display_help_shell():
        """Display help while inside of interactive shell"""
        console.print(
            """[green]\nCommands:[/green][dim white]
                <query>                - Execute query
                -l <type>              - Change language: PPL, SQL
                -f <type>              - Change format: JSON, Table, CSV
                -v                     - Toggle vertical display mode
                -s --save <name>       - Save the latest query result with a name
                -s --load <name>       - Load and display a saved query result
                -s --remove <name>     - Remove a saved query by name
                -s --list              - List all saved query names
                -h/help                - Show this help
                exit/quit/q            - Exit interactive mode
                [/dim white]
[green]NOTE:[/green] To use a different OpenSearch SQL plug-in version, restart the CLI with --version <version>
                    """
        )

    def auto_completer(self, language_mode):
        """
        Get a WordCompleter for the current language mode

        Args:
            language_mode: Current language mode (PPL or SQL)

        Returns:
            WordCompleter: Completer for the current language mode
        """
        # Convert language mode to lowercase for get_literals
        if language_mode == "PPL":
            lang = "ppl"
        else:
            lang = "sql"

        # Get literals based on the current language mode
        literals = Literals.get_literals(lang)
        keywords = []
        for keyword in literals.get("keywords", []):
            keywords.append(keyword.upper())

        functions = []
        for function in literals.get("functions", []):
            functions.append(function.upper())

        # Add shell commands to the completer
        commands = ["-l", "-f", "-v", "-s", "help", "exit", "quit", "q"]

        # Add options for -s command
        options = ["--save", "--load", "--remove", "--list"]

        # Create a WordCompleter with all keywords, functions, and commands
        return WordCompleter(
            keywords + functions + commands + options, ignore_case=True
        )

    def execute_query(self, query):
        """
        Execute a query

        Args:
            query: Query string to execute

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Store the query for saved query
            self.latest_query = query

            # Check if the query starts with "explain"
            is_explain = query.strip().lower().startswith("explain")

            # Call ExecuteQuery directly with the appropriate language mode
            success, result, formatted_result = ExecuteQuery.execute_query(
                self.sql_connection,
                query,
                self.is_ppl_mode,
                is_explain,
                self.format,
                self.is_vertical,
                console.print,
            )
            return success
        except Exception as e:
            console.print(
                f"[bold red]ERROR:[/bold red] [red] Unable to execute [/red] {escape(str(e))}"
            )
            traceback.print_exc()
            return False

    def start(self, language=None, format=None):
        """
        Start interactive query mode

        Args:
            language: Language mode (ppl or sql)
            format: Output format (json, table, csv)
        """

        # Set language_mode based on language parameter
        lang_lower = language.lower()

        if lang_lower not in [
            "ppl",
            "sql",
        ]:
            console.print(
                f"[bold red]Invalid Language:[/bold red] [red]{language}.[/red] [bold red]\nDefaulting to PPL.[/bold red]"
            )
            lang_lower = "ppl"

        self.language_mode = lang_lower.upper()
        self.is_ppl_mode = lang_lower == "ppl"

        # Validate format
        if format.lower() not in ["json", "table", "csv"]:
            console.print(
                f"[bold red]Invalid Format:[/bold red] [red]{format}.[/red] [bold red]\nDefaulting to Table.[/bold red]"
            )
            self.format = "table"
        else:
            self.format = format.lower()

        # Track vertical display mode
        self.is_vertical = config_manager.get_boolean("Query", "vertical", False)

        # Create a PromptSession with auto-completion and syntax highlighting
        session = PromptSession(
            lexer=PygmentsLexer(SqlLexer),
            completer=self.auto_completer(self.language_mode),
            auto_suggest=AutoSuggestFromHistory(),
            history=FileHistory(self.histfile),
        )

        while True:
            try:
                # Get user input with auto-completion and syntax highlighting
                user_input = session.prompt(f"\n{self.language_mode}> ")

                if not user_input:
                    continue

                # Process special commands
                user_cmd = user_input.lower()

                # Handle exit commands
                if user_cmd in ["exit", "quit", "q"]:
                    console.print(
                        "[bold green]\nDisconnected. Goodbye!!!\n[/bold green]"
                    )
                    break

                # Handle help command
                if user_cmd in ["help", "-h", "--help"]:
                    console.print(
                        f"[green]\nSQL:[/green] [dim white]v{sql_version.version}[/dim white]"
                    )
                    console.print(
                        f"[green]Language:[/green] [dim white]{self.language_mode}[/dim white]"
                    )
                    console.print(
                        f"[green]Format:[/green] [dim white]{self.format.upper()}[/dim white]"
                    )
                    self.display_help_shell()
                    continue

                # Handle command-line style arguments
                # Language change
                if user_cmd.startswith("-l"):
                    language_type = user_input[3:].strip().lower()
                    if language_type == "ppl":
                        self.language_mode = "PPL"
                        self.is_ppl_mode = True
                        console.print(
                            f"[green]\nLanguage changed to {self.language_mode}[/green]"
                        )
                        # Update auto-completion for PPL
                        session.completer = self.auto_completer(self.language_mode)
                    elif language_type == "sql":
                        self.language_mode = "SQL"
                        self.is_ppl_mode = False
                        console.print(
                            f"[green]\nLanguage changed to {self.language_mode}[/green]"
                        )
                        # Update auto-completion for SQL
                        session.completer = self.auto_completer(self.language_mode)
                    else:
                        console.print(
                            f"[red]\nInvalid language mode: {language_type}.[/red]"
                        )
                    continue

                # Format change
                if user_cmd.startswith("-f"):
                    format_type = user_input[3:].strip().lower()
                    if format_type in ["json", "table", "csv"]:
                        self.format = format_type
                        console.print(
                            f"[green]\nOutput format changed to {self.format.upper()}[/green]"
                        )
                    else:
                        console.print(f"[red]\nInvalid format: {format_type}.[/red]")
                    continue

                # Toggle vertical table display
                if user_cmd == "-v":
                    self.is_vertical = not self.is_vertical
                    console.print(
                        f"[green]\nTable Vertical:[/green] {'[green]ON[/green]' if self.is_vertical else '[red]OFF[/red]'}"
                    )
                    continue

                # Saved query
                if user_cmd.startswith("-s"):
                    # Parse saved queries commands
                    args = user_input.split()
                    if len(args) >= 2:
                        if args[1] == "--save" and len(args) >= 3:
                            # Save the latest query
                            name = args[2]
                            self.saved_queries.saving_query(
                                name,
                                (
                                    self.latest_query
                                    if hasattr(self, "latest_query")
                                    else None
                                ),
                                self.language_mode,
                            )
                        elif args[1] == "--load" and len(args) >= 3:
                            # Load and execute a saved query
                            name = args[2]
                            success, query, result, language = (
                                self.saved_queries.loading_query(
                                    name,
                                    self.sql_connection,
                                    self.format,
                                    self.is_vertical,
                                )
                            )

                            if success:
                                # Store the latest query for saving
                                self.latest_query = query
                        elif args[1] == "--remove" and len(args) >= 3:
                            # Remove a saved query
                            name = args[2]
                            self.saved_queries.removing_query(name)
                        elif args[1] == "--list":
                            # List all saved query names
                            self.saved_queries.list_saved_queries()
                        else:
                            console.print(
                                "[red]\nInvalid -s command. \nUse --options <name>[/red]"
                            )
                    else:
                        console.print(
                            "[red]\nMissing option for -s command. Use --save, --load, --remove, or --list.[/red]"
                        )
                    continue

                # If not a special command, treat as a query
                self.execute_query(user_input)

            except KeyboardInterrupt:
                console.print("[bold green]\nDisconnected. Goodbye!!!\n[/bold green]")
                break
            except EOFError:
                console.print("[bold green]\nDisconnected. Goodbye!!!\n[/bold green]")
                break


# Create a global instance
interactive_shell = None
