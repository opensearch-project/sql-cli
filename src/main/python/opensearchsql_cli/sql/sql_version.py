"""
SQL Version Management

Handles version selection for OpenSearch CLI.
"""

import os
import re
import subprocess
import requests
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from packaging import version
from rich.console import Console
from rich.status import Status

# Create a console instance for rich formatting
console = Console()

# sql-cli/src/main/python/opensearchsql_cli/sql
current_dir = os.path.dirname(os.path.abspath(__file__))
# sql-cli/
PROJECT_ROOT = os.path.normpath(os.path.join(current_dir, "../../../../../"))
# Java directory: sql-cli/src/main/java
JAVA_DIR = os.path.join(PROJECT_ROOT, "src", "main", "java")


class SqlVersion:
    """
    Manages SQL version selection for OpenSearch CLI
    """

    def __init__(self):
        """
        Initialize the SQL Version manager
        """
        self.version = "live"

    def load_jar_path(self, rebuild=False):
        """
        Get the path to the JAR file for the specified version

        Returns:
            str: Path to the JAR file
        """
        self._build_sqlcli_jar(rebuild)
        return self._get_jar_path()

    def _get_jar_path(self):
        return os.path.join(
            PROJECT_ROOT, "build", "libs", f"opensearchsqlcli-live-all.jar"
        )

    def _build_sqlcli_jar(self, rebuild=False):
        """
        Build the sqlcli JAR for the current version

        Args:
            rebuild: If True, rebuild the JAR even if it exists
            local_dir: Path to directory containing the SQL project (for local builds)

        Returns:
            bool: True if successful, False otherwise
        """
        jar_path = self._get_jar_path()

        # Run ./gradlew clean if rebuild
        if rebuild:
            subprocess.run(
                ["./gradlew", "clean"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

        if not os.path.exists(jar_path):
            cmd_args = ["./gradlew", "shadowJar"]

            with console.status(
                f"[bold yellow]Building SQL CLI Jars...[/bold yellow]",
                spinner="dots",
            ):
                log_file = os.path.join(PROJECT_ROOT, "logs", "sqlcli_build.log")
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, "w") as file:
                    result = subprocess.run(
                        cmd_args,
                        cwd=PROJECT_ROOT,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                    )

            if not os.path.exists(jar_path):
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to build SQL CLI. JAR file does not exist at {jar_path}[/red]"
                )
                console.print(
                    f"[red]Please check file [blue]sqlcli_build.log[/blue] for more information[/red]"
                )
                return False
            else:
                console.print(
                    f"[bold green]SUCCESS:[/bold green] [green]Built SQL CLI at {jar_path}[/green]"
                )

        return True


# Create a global instance
sql_version = SqlVersion()
