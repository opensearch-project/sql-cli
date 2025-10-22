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
        url = "https://central.sonatype.com/repository/maven-snapshots/org/opensearch/query/unified-query-core/maven-metadata.xml"

        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="xml")

        versions = []

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

    def get_jar_path(self):
        """
        Get the path to the JAR file for the specified version

        Returns:
            str: Path to the JAR file
        """
        return os.path.join(
            PROJECT_ROOT, "build", "libs", f"opensearchsqlcli-{self.version}.jar"
        )

    def set_version(self, version, rebuild=False):
        """
        Set the version of OpenSearch to use

        Args:
            version: Version string (e.g., "3.1", "3.0.0.0-alpha1")
            rebuild: If True, rebuild the JAR even if it exists

        Returns:
            bool: True if version is valid, False otherwise
        """
        self.version = self._normalize_version(version)
        self.use_http5 = self._should_use_http5(self.version)

        if self.version not in self.available_versions:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Version {version} is currently not supported[/red]"
            )
            console.print(
                f"[red]Available versions: {', '.join(self.available_versions)}[/red]"
            )
            return False

        return self._build_sqlcli_jar(rebuild=rebuild)

    def set_remote_version(
        self, branch_name, git_url, rebuild=False, remote_output=None
    ):
        """
        Set the version by cloning a git repository and building from it

        Args:
            branch_name: Git branch name to clone
            git_url: Git repository URL
            rebuild: If True, rebuild the JAR even if it exists
            remote_output: Custom directory to clone the repository into (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        # Extract repository name from git URL
        # Example: https://github.com/opensearch-project/sql.git -> sql
        repo_name = os.path.basename(git_url)
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]  # Remove .git suffix

        if remote_output:
            git_dir = remote_output
        else:
            git_dir = os.path.join(PROJECT_ROOT, "remote", repo_name)

        success, result = self._clone_repository(branch_name, git_url, git_dir)

        if not success:
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
                    rebuild = True

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
                    f"[bold red]ERROR:[/bold red] [red]Git is not installed or not found in PATH[/red]"
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
        if not os.path.exists(local_dir):
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Directory {local_dir} does not exist[/red]"
            )
            return False

        if rebuild and not self._build_sql_jars(local_dir):
            return False

        jar_file = self._find_sql_jar(local_dir)

        if not jar_file:
            if not self._build_sql_jars(local_dir):
                return False

            jar_file = self._find_sql_jar(local_dir)

            if not jar_file:
                return False

        self.version = self._extract_version_from_jar(jar_file)
        self.use_http5 = self._should_use_http5(self.version)

        return self._build_sqlcli_jar(rebuild=rebuild, local_dir=local_dir)

    def _normalize_version(self, version_str):
        """
        Normalize version string to ensure it has 4 parts

        Args:
            version_str: Version string to normalize

        Returns:
            str: Normalized version string
        """
        if "-" in version_str:
            return version_str

        parts = version_str.split(".")
        while len(parts) < 4:
            parts.append("0")
        return ".".join(parts)

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
            version = self.get_latest_version()
            console.print(
                f"[bold yellow]WARNING:[/bold yellow] [yellow]Could not extract version from JAR filename, using latest version: {version}[/yellow]"
            )
            return version

    def _find_sql_jar(self, local_dir):
        """
        Find SQL JAR file in the distributions directory

        Args:
            local_dir: Path to directory containing the SQL project

        Returns:
            str: JAR filename if found, None otherwise
        """
        distributions_dir = os.path.join(local_dir, "build", "distributions")

        if os.path.exists(distributions_dir):
            for f in os.listdir(distributions_dir):
                if f.endswith(".jar") and f.startswith("opensearch-sql-"):
                    return f

        return None

    def _build_sql_jars(self, local_dir):
        """
        Build SQL JARs in the local directory by running ./gradlew clean assemble

        Args:
            local_dir: Path to directory containing the SQL project

        Returns:
            bool: True if successful, False otherwise
        """
        with console.status(
            f"[bold yellow]Creating SQL JARs in {local_dir}...[/bold yellow]",
            spinner="dots",
        ):
            log_file = os.path.join(PROJECT_ROOT, "logs", "sql_build.log")
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, "w") as file:
                result = subprocess.run(
                    ["./gradlew", "clean", "assemble"],
                    cwd=local_dir,
                    stdout=file,
                    stderr=subprocess.STDOUT,
                )

            if result.returncode != 0:
                console.print(
                    f"[bold red]ERROR:[/bold red] [red]Failed to build from {local_dir}[/red]"
                )
                console.print(
                    f"[red]Please check file [blue]sql_build.log[/blue] for more information[/red]"
                )
                return False

            console.print(
                f"[bold green]SUCCESS:[/bold green] [green]Built SQL JARs in {local_dir}[/green]"
            )
            return True

    def _build_sqlcli_jar(self, rebuild=False, local_dir=None):
        """
        Build the sqlcli JAR for the current version

        Args:
            rebuild: If True, rebuild the JAR even if it exists
            local_dir: Path to directory containing the SQL project (for local builds)

        Returns:
            bool: True if successful, False otherwise
        """
        jar_path = self.get_jar_path()

        version_parts = self.version.split(".")
        gradle_task = f"{version_parts[0]}_{version_parts[1]}_{version_parts[2]}_{version_parts[3]}"

        # Add _local suffix for local builds
        if local_dir:
            gradle_task += "_local"

        # Run ./gradlew clean if rebuild
        if rebuild:
            subprocess.run(
                ["./gradlew", "clean"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

        if not os.path.exists(jar_path):
            cmd_args = ["./gradlew", gradle_task]

            # Add localJarDir property for local builds
            if local_dir:
                cmd_args.append(f"-PlocalJarDir={local_dir}")

            with console.status(
                f"[bold yellow]Building SQL CLI v{self.version}...[/bold yellow]",
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
        if re.match(r"^\d+(\.\d+)*$", branch_name):
            # Branch is semver, append 0s until length 4 to get the tag
            parts = branch_name.split(".")
            parts += ["0"] * (4 - len(parts))
            branch_name = ".".join(parts)

        with console.status(
            f"[bold yellow]Cloning repository {git_url} branch {branch_name}...[/bold yellow]",
            spinner="dots",
        ):
            # If the branch is a version number, we actually want the tag, to sync with what was actually released
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


# Create a global instance
sql_version = SqlVersion()
