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
        self.available_versions = self.get_all_versions()
        # Default version is the highest version number
        self.version = self.get_latest_version()
        # Default to HTTP5 for version 3.x and above
        # HTTP4 for older versions
        self.use_http5 = self._should_use_http5(self.version)

    def get_all_versions(self):
        """
        Get all available versions from the repository website

        Returns:
            list: List of all available versions
        """
        url = "https://aws.oss.sonatype.org/content/repositories/snapshots/org/opensearch/query/unified-query-core/maven-metadata.xml"

        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="xml")

        versions = []

        # Extract version tags from XML
        for version_tag in soup.find_all("version"):
            version_str = version_tag.text
            version_str = version_str.replace("-SNAPSHOT", "")
            versions.append(version_str)

        return versions

    def get_latest_version(self):
        """
        Get the latest version from the repository website

        Returns:
            str: The latest version string or None if no versions found
        """
        versions = self.get_all_versions()

        if not versions:
            return None

        try:
            parsed_versions = [(v, version.parse(v)) for v in versions]
            # Sort by parsed version objects with descending order
            parsed_versions.sort(key=lambda x: x[1], reverse=True)

            return parsed_versions[0][0]
        except Exception as e:
            # Falling back to string sorting
            versions.sort(reverse=True)
            return versions[0]

    def set_version(self, version, rebuild=False):
        """
        Set the version of OpenSearch to use

        Args:
            version: Version string (e.g., "3.1", "3.0.0.0-alpha1")
            rebuild: If True, rebuild the JAR even if it exists

        Returns:
            bool: True if version is valid, False otherwise
        """
        # Check if the version contains a suffix (like -alpha1)
        if "-" in version:
            # For versions with suffixes, use as is
            self.version = version
        else:
            # For simple versions, add trailing zeros to make 4 parts
            parts = version.split(".")
            while len(parts) < 4:
                parts.append("0")
            self.version = ".".join(parts)

        # Update HTTP client version flag
        self.use_http5 = self._should_use_http5(self.version)

        # Check if the version is available
        invalid = self.version not in self.available_versions

        if invalid:
            # Display available versions
            console.print(
                f"[bold red]\nERROR:[/bold red] [red]Version {version} is currently not supported.[/red]"
            )
            console.print(
                f"[red]Available versions: {', '.join(self.available_versions)}\n[/red]"
            )
            return False

        # Check if the JAR file exists
        jar_path = self.get_jar_path()

        # Create gradle task name with underscores (e.g., "2.19.1.0" -> "2_19_1_0")
        version_parts = self.version.split(".")
        gradle_task = f"{version_parts[0]}_{version_parts[1]}_{version_parts[2]}_{version_parts[3]}"

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
                log_file = os.path.join(PROJECT_ROOT, "sqlcli_build.log")
                with open(log_file, "w") as file:
                    result = subprocess.run(
                        ["./gradlew", gradle_task],
                        cwd=PROJECT_ROOT,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                    )

            # Check if the JAR file exists now
            if not os.path.exists(jar_path):
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to build v{self.version}. JAR file still does not exist at {jar_path}[/red]"
                )
                console.print(
                    f"Please check file [blue]sqlcli_build.log[/blue] for more information"
                )
                return False
            else:
                console.print(
                    f"[bold green]SUCCESS:[/bold green] [green]Built v{self.version} successfully at {jar_path}[/green]"
                )

        return True

    def get_jar_path(self):
        """
        Get the path to the JAR file for the specified version

        Returns:
            str: Path to the JAR file
        """
        return os.path.join(
            PROJECT_ROOT, "build", "libs", f"opensearchsqlcli-{self.version}.jar"
        )

    def _should_use_http5(self, version_str):
        """
        Determine if HTTP5 should be used based on version

        Args:
            version_str: Version string

        Returns:
            bool: True if HTTP5 should be used, False for HTTP4
        """
        try:
            major_version = int(version_str.split(".")[0])
            # Use HTTP5 for version 3.x and above
            return major_version >= 3
        except (ValueError, IndexError):
            # Default to HTTP5 if version parsing fails
            return True

    def _extract_version_from_jar(self, jar_file):
        """
        Extract version from JAR filename

        Args:
            jar_file: JAR filename (e.g., opensearch-sql-3.1.0.0-SNAPSHOT.jar)

        Returns:
            str: Extracted version (e.g., 3.1.0.0) or latest version if extraction fails
        """
        match = re.search(r"opensearch-sql-([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", jar_file)
        if match:
            return match.group(1)
        else:
            # Default to latest version if version can't be extracted
            version = self.get_latest_version()
            console.print(
                f"[bold yellow]WARNING:[/bold yellow] [yellow]Could not extract version from JAR filename, using latest version: {version}[/yellow]"
            )
            return version

    def _clone_repository(self, branch_name, git_url, git_dir):
        """
        Clone a git repository

        Args:
            branch_name: Git branch name to clone
            git_url: Git repository URL
            git_dir: Directory to clone into

        Returns:
            tuple: (success, result) where success is a boolean and result is the subprocess.CompletedProcess object
        """
        result = subprocess.run(
            [
                "git",
                "clone",
                "--branch",
                branch_name,
                "--single-branch",
                git_url,
                git_dir,
            ],
            capture_output=True,
            text=True,
        )

        return result.returncode == 0, result

    def set_remote_version(self, branch_name, git_url, rebuild=False):
        """
        Set the version by cloning a git repository and building from it

        Args:
            branch_name: Git branch name to clone
            git_url: Git repository URL
            rebuild: If True, rebuild the JAR even if it exists

        Returns:
            bool: True if successful, False otherwise
        """
        # Extract repository name from git URL
        # Example: https://github.com/opensearch-project/sql.git -> sql
        repo_name = os.path.basename(git_url)
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]  # Remove .git suffix

        # Create a directory path for the cloned repository
        git_dir = os.path.join(PROJECT_ROOT, "remote", repo_name)

        # Clone the repository
        print("")
        with console.status(
            f"[bold yellow]Cloning repository {git_url} branch {branch_name}...[/bold yellow]",
            spinner="dots",
        ):
            success, result = self._clone_repository(branch_name, git_url, git_dir)

        if not success:
            # If the error is because the directory already exists
            # Then ask if user wants to reclone
            if "fatal: destination path" in result.stderr:
                console.print(
                    f"[bold yellow]INFO:[/bold yellow] [yellow]Directory already exists: {git_dir}[/yellow]"
                )
                reclone = (
                    input("Do you want to delete and reclone the repository? (y/n): ")
                    .strip()
                    .lower()
                )

                if reclone == "y" or reclone == "yes":
                    shutil.rmtree(git_dir)
                    success, result = self._clone_repository(
                        branch_name, git_url, git_dir
                    )

                    if not success:
                        console.print(
                            f"[bold red]ERROR:[/bold red] [red]Failed to clone repository: {result.stderr}[/red]"
                        )
                        return False
                else:
                    console.print(
                        f"[bold yellow]INFO:[/bold yellow] [yellow]Using existing directory: {git_dir}[/yellow]"
                    )
            elif "git: command not found" in result.stderr:
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Git is not installed or not found in PATH.[/red]"
                )
                console.print(
                    f"[yellow]Please install Git by following the guide:[/yellow] [blue]https://github.com/git-guides/install-git[/blue]"
                )
                console.print(f"[blue]https://github.com/git-guides/install-git[/blue]")
                return False
            else:
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to clone repository: {result.stderr}[/red]"
                )
                return False

        # Use set_local_version to build from the cloned repository
        return self.set_local_version(git_dir, rebuild)

    def set_local_version(self, local_dir, rebuild=False):
        """
        Set the version using a local directory

        Args:
            local_dir: Path to directory containing the SQL project
            rebuild: If True, rebuild the JAR even if it exists

        Returns:
            bool: True if successful, False otherwise
        """
        # Ensure the directory exists
        if not os.path.exists(local_dir):
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Directory {local_dir} does not exist[/red]"
            )
            return False

        # Find the JAR file in the distributions directory
        distributions_dir = os.path.join(local_dir, "build", "distributions")
        jar_file = None

        # If distributions directory exists, look for JAR file
        if os.path.exists(distributions_dir):
            for f in os.listdir(distributions_dir):
                if f.endswith(".jar") and f.startswith("opensearch-sql-"):
                    jar_file = f
                    break

        # Extract version from JAR filename if it exists
        if jar_file:
            # Extract version from JAR filename
            self.version = self._extract_version_from_jar(jar_file)
        else:
            # If no JAR file found, build it first
            # Run ./gradlew clean assemble in the local directory
            with console.status(
                f"[bold yellow]Creating JARs in {local_dir}...[/bold yellow]",
                spinner="dots",
            ):
                log_file = os.path.join(PROJECT_ROOT, "sql_build.log")
                with open(log_file, "w") as file:
                    result = subprocess.run(
                        ["./gradlew", "clean", "assemble"],
                        cwd=local_dir,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                    )

                if result.returncode != 0:
                    console.print(
                        f"[bold red]ERROR:[/bold red] [red]Failed to build from {local_dir}: {result.stderr}[/red]"
                    )
                    console.print(
                        f"Please check file [blue]sql_build.log[/blue] for more information"
                    )
                    return False

            # Look for JAR file again after building
            if os.path.exists(distributions_dir):
                for f in os.listdir(distributions_dir):
                    if f.endswith(".jar") and f.startswith("opensearch-sql-"):
                        jar_file = f
                        break

                if jar_file:
                    # Extract version from JAR filename
                    self.version = self._extract_version_from_jar(jar_file)
                else:
                    console.print(
                        f"[bold red]ERROR:[/bold red] [red]No JAR file found after build in {distributions_dir}[/red]"
                    )
                    return False
            else:
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Distributions directory not found after build: {distributions_dir}[/red]"
                )
                return False

        # Update HTTP client version flag
        self.use_http5 = self._should_use_http5(self.version)

        # Create gradle task name with underscores (e.g., "3.1.0.0" -> "3_1_0_0_local")
        version_parts = self.version.split(".")
        gradle_task = f"{version_parts[0]}_{version_parts[1]}_{version_parts[2]}_{version_parts[3]}_local"

        # Check if the JAR file exists
        jar_path = self.get_jar_path()

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

            # Run the gradle task with the localJarDir property
            print("")
            with console.status(
                f"[bold yellow]Building v{self.version}...[/bold yellow]",
                spinner="dots",
            ):
                log_file = os.path.join(PROJECT_ROOT, "sqlcli_build.log")
                with open(log_file, "w") as file:
                    result = subprocess.run(
                        ["./gradlew", gradle_task, f"-PlocalJarDir={local_dir}"],
                        cwd=PROJECT_ROOT,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                    )

            # Check if the JAR file exists now
            if not os.path.exists(jar_path):
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to build v{self.version}. JAR file does not exist at {jar_path}[/red]"
                )
                console.print(
                    f"Please check file [blue]sqlcli_build.log[/blue] for more information"
                )
                return False
            else:
                console.print(
                    f"[bold green]SUCCESS:[/bold green] [green]Built v{self.version} successfully at {jar_path}[/green]"
                )

        return True


# Create a global instance
sql_version = SqlVersion()
