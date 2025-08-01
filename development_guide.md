## Development Guide

This guide provides comprehensive information for developers who want to contribute to the OpenSearch SQL CLI project. 

- [Development Environment Set Up](#development-environment-set-up)
- [Code Architecture Details](#code-architecture-details)
- [Run CLI](#run-cli)
- [Testing](#testing)
- [Style](#style)
- [Release Guide](#release-guide)

### Development Environment Set Up
- `pip install virtualenv`
- `virtualenv venv` to create virtual environment for **Python 3**
- `source ./venv/bin/activate` activate virtual env.
- `cd` into project root folder.
- `pip install --editable .` will install all dependencies from `setup.py`.

### Code Architecture Details

#### Layered Architecture

The OpenSearch SQL CLI uses a layered architecture to bridge Python's interactive capabilities with Java's robust OpenSearch client libraries:

```
Python CLI Layer → Py4J Bridge → Java Gateway → OpenSearch Client → OpenSearch Cluster
```

1. **Python CLI Layer**
   - Handles user interaction, command parsing, and display formatting
   - Manages configuration, history, and saved queries
   - Key components: `main.py`, `interactive_shell.py`, `execute_query.py`

2. **Py4J Bridge**
   - Enables Python code to access Java objects
   - Manages communication between Python and Java processes
   - Key components: `sql_connection.py`, `sql_library_manager.py`

3. **Java Gateway**
   - Provides entry point for Python to access Java functionality
   - Initializes connections to OpenSearch
   - Key components: `Gateway.java`, `GatewayModule.java`

4. **OpenSearch Client**
   - Handles communication with OpenSearch cluster
   - Executes queries and processes results
   - Key components: `Client4.java`/`Client5.java`, `QueryExecution.java`

#### Key Classes and Their Responsibilities

##### Python Components

- **OpenSearchSQLCLI** (`main.py`): Entry point for the CLI, processes command-line arguments
- **InteractiveShell** (`interactive_shell.py`): Manages the interactive shell, command history, and user input
- **ExecuteQuery** (`execute_query.py`): Handles query execution and result formatting
- **SqlConnection** (`sql_connection.py`): Manages connection to the Java gateway
- **SqlLibraryManager** (`sql_library_manager.py`): Manages the Java process lifecycle
- **SqlVersion** (`sql_version.py`): Handles version detection and JAR file selection

##### Java Components

- **Gateway** (`Gateway.java`): Main entry point for Java functionality, exposed to Python via Py4J
- **GatewayModule** (`GatewayModule.java`): Guice module for dependency injection
- **QueryExecution** (`QueryExecution.java`): Executes queries against OpenSearch
- **Client4/Client5** (`Client4.java`/`Client5.java`): HTTP client implementations for different OpenSearch versions

#### Version-Specific JAR Building

The CLI supports multiple OpenSearch versions by dynamically building version-specific JARs. The build system automatically selects the appropriate HTTP client and its unified query packages based on the provided OpenSearch SQL version:
- For OpenSearch 3.x and above: Uses HTTP5 client
- For OpenSearch below 3.x: Uses HTTP4 client

##### 1. Version Detection and Build Triggering

The CLI supports three methods for specifying the SQL version:

1. **Maven Repository Version** (e.g., `opensearchsql -v 3.1`):
   - `sql_version.py` parses and normalizes it to a full version (e.g., `3.1.0.0`)
   - The system checks if a corresponding JAR file exists (e.g., `opensearchsql-3.1.0.0.jar`)
   - If not found, it automatically triggers the Gradle build process:
     ```bash
     # For OpenSearch SQL 3.1.0.0
     ./gradlew 3_1_0_0
     ```

2. **Local Directory** (e.g., `opensearchsql --local /path/to/sql/plugin/directory`):
   - Uses a local directory containing the SQL plugin JAR files
   - Extracts the version from the JAR filename
   - Builds a local version-specific JAR:
     ```bash
     # For local OpenSearch SQL 3.1.0.0
     ./gradlew 3_1_0_0_local -PlocalJarDir=/path/to/sql/plugin/directory
     ```

3. **Remote Git Repository** (e.g., `opensearchsql --remote https://github.com/opensearch-project/sql.git -b <branch_name>`):
   - Clones the specified git repository and branch using:
     ```bash
     git clone --branch <branch_name> --single-branch <git_url>
     ```
   - Extracts the version from the cloned repository's JAR files
   - Builds a local version-specific JAR using the cloned repository
      ```bash
      # For local OpenSearch SQL 3.1.0.0
      ./gradlew 3_1_0_0_local -PlocalJarDir=/project_root/remote/git_directory
      ```

##### 2. Dynamic Gradle Task Creation

The build system uses Gradle's task rules to dynamically create tasks based on version numbers:
- When `./gradlew 3_1_0_0` is executed, it creates configurations specific to version 3.1.0.0
- The `createVersionConfigurations` function sets up dependencies and configurations
- This allows supporting any OpenSearch version without hardcoding version-specific tasks

##### 3. HTTP Client Selection

Based on the version, the system automatically selects the appropriate HTTP client:
- HTTP5 for OpenSearch 3.x and above
- HTTP4 for OpenSearch below 3.x

This selection affects:
- Which source sets are compiled (`http4` or `http5`)
- Which dependencies are included
- How the client connects to OpenSearch

##### 4. Dependencies Configuration

The system adds shared dependencies and version-specific dependencies:
```bash
# Shared dependencies are added and its specific version dependency:
org.opensearch.query:unified-query-common:3.1.0.0-SNAPSHOT
org.opensearch.query:unified-query-core:3.1.0.0-SNAPSHOT
org.opensearch.query:unified-query-opensearch:3.1.0.0-SNAPSHOT
org.opensearch.query:unified-query-ppl:3.1.0.0-SNAPSHOT
org.opensearch.query:unified-query-sql:3.1.0.0-SNAPSHOT
org.opensearch.query:unified-query-protocol:3.1.0.0-SNAPSHOT
org.opensearch.client:opensearch-rest-high-level-client:3.1.0
org.opensearch.client:opensearch-rest-client:3.1.0
org.opensearch.client:opensearch-java:3.1.0
org.apache.httpcomponents.core5:httpcore5:5.2
org.apache.httpcomponents.client5:httpclient5:5.2.1
```

##### 5. Shadow JAR Creation

The `createShadowJarTask` function creates a task to build a fat JAR with all dependencies:
- The resulting JAR is named with the specific version (e.g., `opensearchsql-3.1.0.0.jar`)
- This JAR includes all necessary dependencies for the specified version
- The JAR is then loaded by the Python process when the CLI runs

Similarly, the `createLocalShadowJarTask` function creates a task for building a fat JAR using local JAR files:
- It accepts a local directory path containing the SQL plugin JAR files
- It includes the JAR files from the specified local directory
- The resulting JAR is named with the specific version and includes "_local" in the Gradle task name (e.g., `3_1_0_0_local`)

This architecture allows the CLI to support multiple OpenSearch versions without requiring separate installations or complex configuration.

## Run CLI
- Start an OpenSearch instance from either local, Docker with OpenSearch SQL plugin, or AWS OpenSearch
- To launch the cli, use 'wake' word `opensearchsql` followed by endpoint of your running OpenSearch instance. If not specifying any endpoint, it uses http://localhost:9200 by default. If not provided with port number, http endpoint uses 9200 and https uses 443 by default.

### CLI Flow

The OpenSearch SQL CLI follows this execution flow when processing queries:

1. **Command Invocation**: `opensearchsql` command will run with its default settings

2. **Initialization Process**:
   - Version detection determines whether to use HTTP4 (OpenSearch < 3.x) or HTTP5 (OpenSearch ≥ 3.x) client
   - Connection to OpenSearch cluster is verified
   - Java Gateway server is started via `sql_library_manager`
   - Appropriate JAR file is loaded based on OpenSearch version

3. **Query Processing Flow**:
   ```
   Input Query → Python → Java → OpenSearch → Java → Python → Output
   ```

   Detailed steps:
   1. User enters query in interactive shell
   2. `InteractiveShell.execute_query()` processes the input
   3. `ExecuteQuery.execute_query()` prepares the query
   4. `sql_connection.query_executor()` sends query to Java gateway
   5. `Gateway.queryExecution()` in Java receives the query
   6. `QueryExecution.execute()` processes the query:
      - Determines if it's PPL or SQL
      - Sends to appropriate service (pplService or sqlService)
      - Formats results based on requested format (JSON, Table, CSV)
   7. Results are returned to Python and displayed to user

4. **Component Interaction**:
   - Python components use Py4J to communicate with Java
   - Java components use OpenSearch client libraries to communicate with OpenSearch
   - HTTP4 or HTTP5 client is used based on OpenSearch version

## Testing
- Prerequisites
    - Build the application
    - Start a local OpenSearch instance.
- Pytest
    - `pip install -r requirements-dev.txt` Install test frameworks including Pytest and mock.
    - `cd` into `src/main/python/opensearchsql_cli/tests` and run `pytest`
- Refer to [README.md](src/main/python/opensearchsql_cli/tests/README.md) for manual test guidance.

## Style
- Use [black](https://github.com/psf/black) to format code.
```
# Format all Python files
black .
# Format all Java files
./gradlew spotlessApply
```

## Release guide

- Package Manager: pip
- Repository of software for Python: PyPI

### Workflow

1. Update version number
    1. Modify the version number in [`__init__.py`](`src/main/python/opensearchsql_cli/__init__.py`). It will be used by `setup.py` for release.
2. Create/Update `setup.py` (if needed)
    1. For more details refer to https://packaging.python.org/tutorials/packaging-projects/#creating-setup-py 
3. Update README.md, Legal and copyright files(if needed)
    1. Update README.md when there is a critical feature added.
    2. Update `THIRD-PARTY` files if there is a new dependency added.
4. Generate distribution archives
    1. Make sure you have the latest versions of `setuptools` and `wheel` installed:  `python3 -m pip install --user --upgrade setuptools wheel`
    2. Run this command from the same directory where `setup.py` is located: `python3 setup.py sdist bdist_wheel`
    3. Check artifacts under `sql-cli/dist/`, there should be a `.tar.gz` file and a `.whi` file with correct version. Remove other deprecated artifacts.
5. Upload the distribution archives to TestPyPI
    1. Register an account on [testPyPI](https://test.pypi.org/)
    2. `python3 -m pip install --user --upgrade twine`
    3. `python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*`
6. Install your package from TestPyPI and do manual test
    1. `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple opensearchsql`
7. Upload to PyPI
    1. Register an account on [PyPI](https://pypi.org/), note that these are two separate servers and the credentials from the test server are not shared with the main server.
    2. Use `twine upload dist/*` to upload your package and enter your credentials for the account you registered on PyPI. You don't need to specify --repository; the package will upload to https://pypi.org/ by default.
8. Install your package from PyPI using `pip install [your-package-name]`

### Reference
- https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56
- https://packaging.python.org/tutorials/packaging-projects/
- https://packaging.python.org/guides/using-testpypi/
