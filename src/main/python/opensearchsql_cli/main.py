"""
CLI Commands and Interactive Mode

Handles command-line interface, interactive mode, and user interactions.
"""

import typer
import sys
import atexit
import signal
import pyfiglet

from rich.console import Console
from rich.status import Status
from .sql import sql_connection
from .query import SavedQueries
from .sql.sql_library_manager import sql_library_manager
from .sql.sql_version import sql_version
from .config.config import config_manager
from .interactive_shell import InteractiveShell

# Create a console instance for rich formatting
console = Console()


class OpenSearchSqlCli:
    """
    OpenSearch SQL CLI class for managing command-line interface and interactive mode
    """

    def __init__(self):
        """
        Initialize the OpenSearch SQL CLI instance
        """
        # Create a connection instance
        self.sql_connection = sql_connection

        # Create SavedQueries instance
        self.saved_queries = SavedQueries()

        # Create InteractiveShell instance
        self.shell = InteractiveShell(self.sql_connection, self.saved_queries)

        self.app = typer.Typer(
            help="OpenSearch SQL CLI - Command Line Interface for OpenSearch SQL Plug-in"
        )

        # Register commands
        self.register_commands()

        # Register cleanup function
        atexit.register(self.cleanup_on_exit)

    def cleanup_on_exit(self):
        """Cleanup function called when CLI exits"""
        # Stop the SQL Library server
        if sql_library_manager.started:
            sql_library_manager.stop()

    def register_commands(self):
        """Register commands with the Typer app"""

        @self.app.callback(invoke_without_command=True)
        def main(
            ctx: typer.Context,
            endpoint: str = typer.Option(
                None,
                "--endpoint",
                "-e",
                help="OpenSearch endpoint: localhost:9200, https://localhost:9200",
            ),
            username_password: str = typer.Option(
                None,
                "--user",
                "-u",
                help="Username and password in format username:password",
            ),
            insecure: bool = typer.Option(
                False,
                "--insecure",
                "-k",
                is_flag=True,
                help="Ignore SSL certificate validation",
            ),
            aws_auth: str = typer.Option(
                None,
                "--aws-auth",
                help="Use AWS SigV4 authentication for the provided URL",
            ),
            language: str = typer.Option(
                None,
                "--language",
                "-l",
                help="Set language mode: PPL, SQL",
                autocompletion=lambda ctx, incomplete: [
                    "PPL",
                    "SQL",
                ],
            ),
            format: str = typer.Option(
                None,
                "--format",
                "-f",
                help="Set output format: Table, JSON, CSV",
                autocompletion=lambda ctx, incomplete: [
                    "TABLE",
                    "JSON",
                    "CSV",
                ],
            ),
            version: str = typer.Option(
                None,
                "--version",
                help="Set OpenSearch SQL plug-in version: 3.1, 2.19",
                autocompletion=lambda ctx, incomplete: [
                    "3.1",
                    "2.19",
                ],
            ),
            local_dir: str = typer.Option(
                None,
                "--local",
                help="Use a local directory containing the SQL plugin JAR",
            ),
            remote: str = typer.Option(
                None,
                "--remote",
                help='Clone from a git repository: --remote "https://github.com/opensearch-project/sql.git"',
            ),
            branch: str = typer.Option(
                None,
                "--branch",
                "-b",
                help='Branch name to clone (defaults to config value or "main")',
            ),
            remote_output: str = typer.Option(
                None,
                "--output",
                "-o",
                help="Custom output directory for cloned repository (used with --remote)",
            ),
            rebuild: bool = typer.Option(
                False,
                "--rebuild",
                help="Rebuild the JAR file to update to latest timestamp version",
            ),
            query: str = typer.Option(
                None,
                "--query",
                "-q",
                help="Execute a query (non-interactive mode)",
            ),
            config: bool = typer.Option(
                False,
                "--config",
                "-c",
                help="Display current configuration settings",
            ),
        ):
            """
            OpenSearch SQL CLI - Command Line Interface for OpenSearch SQL Plug-in
            """

            # Display config if requested
            if config:
                config_manager.display()
                return

            print("")
            # Version selection logic with priority
            # Command arg has priority over config then default
            version_to_use = version
            local_dir_to_use = local_dir
            remote_to_use = remote

            # If command line options not provided, try config file
            if not (version_to_use or local_dir_to_use or remote_to_use):
                version_to_use = config_manager.get("SqlVersion", "version", "")
                local_dir_to_use = config_manager.get("SqlVersion", "local", "")
                remote_to_use = config_manager.get("SqlVersion", "remote", "")

            # Process based on which option is available
            # --version > --local > --remote priority
            if version_to_use:
                # Version provided
                success = sql_version.set_version(
                    version=version_to_use, rebuild=rebuild
                )
                if not success:
                    return
            elif local_dir_to_use:
                # Local directory provided
                success = sql_version.set_local_version(
                    local_dir_to_use, rebuild=rebuild
                )
                if not success:
                    return
            elif remote_to_use:
                # Remote git info provided
                git_url = remote_to_use

                # Get branch name from config if not provided via command line
                if branch is None:
                    branch_name = config_manager.get(
                        "SqlVersion", "branch_name", "main"
                    )
                else:
                    branch_name = branch

                # Get remote_output from config if not provided via command line
                if remote_output is None:
                    remote_output = config_manager.get(
                        "SqlVersion", "remote_output", ""
                    )

                success = sql_version.set_remote_version(
                    branch_name,
                    git_url,
                    rebuild=rebuild,
                    remote_output=remote_output,
                )
                if not success:
                    return
            else:
                # Use the default latest version if no options provided
                success = sql_version.set_version(sql_version.version, rebuild)
                if not success:
                    return

            # Get defaults from config if not provided
            if language is None:
                language = config_manager.get("Query", "language", "ppl")
            if format is None:
                format = config_manager.get("Query", "format", "table")

            # Initialize OpenSearch connection
            if endpoint is None or endpoint == "":
                host_port = config_manager.get("Connection", "endpoint", "localhost")
            else:
                host_port = endpoint

            # Use config value for insecure if not provided
            if insecure is None:
                ignore_ssl = config_manager.get_boolean("Connection", "insecure", False)
            else:
                ignore_ssl = insecure

            # Use config values for username and password if not provided
            if username_password is None:
                username = config_manager.get("Connection", "username", "")
                password = config_manager.get("Connection", "password", "")
                if username and password:
                    username_password = f"{username}:{password}"

            # If aws_auth is specified as a command-line argument, use it as the endpoint
            if aws_auth:
                host_port = aws_auth
                aws_auth = True
            elif config_manager.get_boolean("Connection", "aws_auth", False):
                aws_auth = True
            else:
                aws_auth = False

            with console.status("Verifying OpenSearch connection...", spinner="dots"):
                if not self.sql_connection.verify_opensearch_connection(
                    host_port, username_password, ignore_ssl, aws_auth
                ):
                    if (
                        hasattr(self.sql_connection, "error_message")
                        and self.sql_connection.error_message
                    ):
                        console.print(
                            f"[bold red]ERROR:[/bold red] [red]{self.sql_connection.error_message}[/red]\n"
                        )
                    return

            with console.status("Initializing SQL Library...", spinner="dots"):
                if not self.sql_connection.initialize_sql_library(
                    host_port, username_password, ignore_ssl, aws_auth
                ):
                    if (
                        hasattr(self.sql_connection, "error_message")
                        and self.sql_connection.error_message
                    ):
                        console.print(
                            f"[bold red]ERROR:[/bold red] [red]{self.sql_connection.error_message}[/red]\n"
                        )
                    return

            # print Banner
            banner = pyfiglet.figlet_format("OpenSearch", font="slant")
            print(banner)

            # Display OpenSearch connection information
            console.print(
                f"[green]OpenSearch:[/green] [dim white]v{self.sql_connection.cluster_version}[/dim white]"
            )
            console.print(f"[green]Endpoint:[/green] {self.sql_connection.url}")
            if self.sql_connection.username:
                if aws_auth:
                    # For AWS connections, display the region
                    console.print(
                        f"[green]Region:[/green] [dim white]{self.sql_connection.username}[/dim white]"
                    )
                else:
                    # For regular connections, display the username
                    console.print(
                        f"[green]User:[/green] [dim white]{self.sql_connection.username}[/dim white]"
                    )
            console.print(
                f"[green]SQL:[/green] [dim white]v{sql_version.version}[/dim white]"
            )
            console.print(
                f"[green]Language:[/green] [dim white]{language.upper()}[/dim white]"
            )
            console.print(
                f"[green]Format:[/green] [dim white]{format.upper()}[/dim white]"
            )

            # Execute single query non-interactive mode
            if query:
                # Initialize the interactive shell
                self.shell.language_mode = language.lower()
                self.shell.is_ppl_mode = language.lower() == "ppl"
                self.shell.format = format.lower()
                self.shell.execute_query(query)
                print("")
                return

            # Start interactive shell
            self.shell.start(language, format)


def main():
    """Main entry point"""
    try:
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal. Shutting down...")
            # Stop the SQL Library server
            if sql_library_manager.started:
                sql_library_manager.stop()
            sys.exit(0)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create CLI instance
        cli = OpenSearchSqlCli()

        # Run the Typer app
        return cli.app()
    except Exception as e:
        print(f"Error starting OpenSearch SQL CLI: {e}")
        import traceback

        traceback.print_exc()

        # Make sure to stop the SQL Library process on error
        if sql_library_manager.started:
            sql_library_manager.stop()

        return 1


if __name__ == "__main__":
    sys.exit(main())
