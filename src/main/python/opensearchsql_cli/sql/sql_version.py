"""
SQL Version Management

Handles version selection for OpenSearch CLI.
"""

import os
import re
import subprocess
from rich.console import Console
from rich.status import Status

# Create a console instance for rich formatting
console = Console()


class SqlVersion:
    """
    Manages SQL version selection for OpenSearch CLI
    """

    def __init__(self):
        """
        Initialize the SQL Version manager
        """
        self.version = "3.1.0.0"  # Default version
        self.available_versions = ["3.1.0.0", "2.19.0.0"]

    def set_version(self, version, rebuild=False):
        """
        Set the version of OpenSearch to use

        Args:
            version: Version string (e.g., "3.1", "2.19")
            rebuild: If True, rebuild the JAR even if it exists

        Returns:
            bool: True if version is valid, False otherwise
        """

        # Validate version format first
        if not re.match(r"^[0-9]+(\.[0-9]+)*$", version):
            invalid = True
        else:
            # Add trailing zeros to make 4 parts
            parts = version.split(".")
            while len(parts) < 4:
                parts.append("0")
            self.version = ".".join(parts)

            # Check if the version is available
            invalid = self.version not in self.available_versions

        if invalid:
            # Prepare display versions (remove trailing zeros)
            display_versions = []
            for v in self.available_versions:
                v_parts = v.split(".")
                while v_parts and v_parts[-1] == "0":
                    v_parts.pop()
                display_versions.append(".".join(v_parts))

            console.print(
                f"[bold red]\nERROR:[/bold red] [red]Version {version} is currently not supported.[/red]"
            )
            console.print(
                f"[red]Available versions: {', '.join(display_versions)}\n[/red]"
            )
            return False

        # Check if the JAR file exists
        # sql-cli/src/main/python/opensearchsql_cli/sql
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # sql-cli/
        project_root = os.path.normpath(os.path.join(current_dir, "../../../../../"))
        jar_path = self.get_jar_path(project_root)

        # Create gradle task name with underscores (e.g., "2.19.1.0" -> "v2_19_1_0")
        version_parts = self.version.split(".")
        gradle_task = f"v{version_parts[0]}_{version_parts[1]}_{version_parts[2]}_{version_parts[3]}"

        # If rebuild is requested or the JAR doesn't exist
        if rebuild or not os.path.exists(jar_path):
            if rebuild and os.path.exists(jar_path):
                console.print(
                    f"[bold yellow]\nINFO:[/bold yellow] [yellow]Rebuilding v{self.version} at {jar_path}[/yellow]"
                )
            else:
                console.print(
                    f"[bold yellow]\nWARNING:[/bold yellow] [yellow]v{self.version} does not exist at {jar_path}[/yellow]"
                )

            # Run the gradle task
            print("")
            with console.status(
                f"[bold yellow]Building v{self.version}...[/bold yellow]",
                spinner="dots",
            ):
                log_file = os.path.join(project_root, "build.log")
                with open(log_file, "w") as file:
                    result = subprocess.run(
                        ["./gradlew", gradle_task],
                        cwd=project_root,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                    )

            # Check if the JAR file exists now
            if not os.path.exists(jar_path):
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to build v{self.version}. JAR file still does not exist at {jar_path}[/red]"
                )
                return False
            else:
                console.print(
                    f"[bold green]SUCCESS:[/bold green] [green]Built v{self.version} successfully at {jar_path}[/green]"
                )

        return True

    def get_jar_path(self, project_root):
        """
        Get the path to the JAR file for the specified version

        Args:
            project_root: Root directory of the project

        Returns:
            str: Path to the JAR file
        """
        return os.path.join(
            project_root, "build", "libs", f"opensearchsql-v{self.version}.jar"
        )


# Create a global instance
sql_version = SqlVersion()
