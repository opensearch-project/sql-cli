
[![SQL CLI Test and Build](https://github.com/opensearch-project/sql-cli/workflows/SQL%20CLI%20Test%20and%20Build/badge.svg)](https://github.com/opensearch-project/sql-cli/actions)
[![Latest Version](https://img.shields.io/pypi/v/opensearchsql.svg)](https://pypi.python.org/pypi/opensearchsql/)
[![Documentation](https://img.shields.io/badge/documentation-blue.svg)](https://opensearch.org/docs/latest/search-plugins/sql/cli/)
[![Chat](https://img.shields.io/badge/chat-on%20forums-blue)](https://forum.opensearch.org/c/plugins/sql)
![PyPi Downloads](https://img.shields.io/pypi/dm/opensearchsql.svg)
![PRs welcome!](https://img.shields.io/badge/PRs-welcome!-success)

# OpenSearch SQL CLI

Interactive command-line interface (CLI) for executing PPL (Piped Processing Language) and SQL queries against OpenSearch clusters. Supports secure and insecure endpoints, AWS SigV4 authentication, autocomplete, syntax highlighting, configurable output formats (Table, JSON, CSV), and saved query history. Easily toggle language modes, SQL plugin versions, and vertical display formatting - all from a single terminal session.

The SQL CLI component in OpenSearch is a stand-alone Python application and can be launched by a 'wake' word `opensearchsql`. 

![](screenshots/usage.gif)

### Query Compatibility Testing

Users can test their existing queries against newer OpenSearch SQL plug-in versions before upgrading their OpenSearch clusters.

For example, user is currently using version **2.19** may want to validate query compatibility with version **3.1** first.

By using this CLI tool, they can:
- Load and run SQL 3.1 logic locally, without upgrading their OpenSearch cluster.
- Verify that their current queries execute as expected under the new SQL engine.
- Avoid potential breaking changes and reduce the need for rollback in production.

This CLI acts as a safe testing environment, allowing smooth transitions between versions with confidence.

### SQL CLI

|       |                                                 |
| ----- | ----------------------------------------------- |
| Test and build | [![SQL CLI CI][sql-cli-build-badge]][sql-cli-build-link] |

[sql-cli-build-badge]: https://github.com/opensearch-project/sql-cli/actions/workflows/sql-cli-test-and-build-workflow.yml/badge.svg
[sql-cli-build-link]: https://github.com/opensearch-project/sql-cli/actions/workflows/sql-cli-test-and-build-workflow.yml

## Features

- **Autocomplete** for SQL and PPL
- **Syntax highlighting**
- **Formatted output**
  - Table
  - JSON
  - CSV
- **Field names** displayed with color
- **Horizontal display** for table format
  - Vertical display automatically used when output is too wide
  - Toggle vertical mode on/off with `-v`
- **Connect to OpenSearch**
  - Works with or without OpenSearch security enabled
  - Supports Amazon OpenSearch Service domains
- **Query operations**
  - Execute queries
  - Explain plans
  - Save and load queries
- **SQL plugin version selection**
- **Command history**
  - `src/main/python/opensearchsql_cli/.cli_history`
- **Configuration file**
  - `src/main/python/opensearchsql_cli/config/config_file.yaml`
- **SQL plug-in connection log**
  - `src/main/java/sql_library.log`
- **Gradle log**
  - `build.log`

## Version
Unlike plugins which use 4-digit version number. SQl-CLI uses `x.x.x` as version number same as other python packages in OpenSearch family. As a client for OpenSearch SQL, it has independent release. 
SQL-CLI should be compatible to all OpenSearch SQL versions. However since the codebase is in a monorepo, 
so we'll cut and name sql-cli release branch and tags differently. E.g.
```
release branch: sql-cli-1.0
release tag: sql-cli-v1.0.0 
```

## Install

Launch your local OpenSearch instance and make sure you have the OpenSearch SQL plugin installed.

To install the SQL CLI:


1. We suggest you install and activate a python3 virtual environment to avoid changing your local environment:

    ```
    pip install virtualenv
    virtualenv venv
    cd venv
    source ./bin/activate
    ```


1. Install the CLI:

    ```
    pip3 install opensearchsql
    ```

    The SQL CLI only works with Python 3, since Python 2 is no longer maintained since 01/01/2020. See https://pythonclock.org/


1. To launch the CLI, run:

    ```
    opensearchsql 
    ```
    By default, the `opensearchsql` command connects to [http://localhost:9200](http://localhost:9200/).

## Startup Commands

### Defaults: if no arguments provided
- **Language**: PPL  
- **Endpoint**: `http://localhost:9200`  
- **Output Format**: Table  
- **SQL Plugin Version**: `3.1.0.0`

### If not specify protocol or port number
  - The default protocol is **HTTP** with port number **9200**. 
  - If using **HTTPS** without specifying a port, port **443** is used by default.

| Options                               | Description                                                                   |
|---------------------------------------|-------------------------------------------------------------------------------|
| `-e`, `--endpoint` `<host:port>`      | Set the OpenSearch endpoint (e.g., `protocol://domain:port`) |
| `-u`, `--user` `<username:password>`  | Provide credentials for secure clusters                                       |
| `-k`, `--insecure`                    | Ignore SSL certificate verification (use with `https` protocol)                     |
| `-l`, `--language` `<language>`       | Choose query language: `ppl` or `sql`                                         |
| `-f`, `--format` `<format>`           | Set output format: `table`, `json`, or `csv`                                  |
| `-v`, `--version` `<version>`         | Set OpenSearch SQL plugin version (e.g., `3.1`, `2.19`)                       |
| `--rebuild`                           | Rebuild or update the corresponding JAR file                                  |
| `-c`, `--config`                      | Show current configuration values                                             |
| `--help`                              | Show help message and usage examples                                          |

### Example Usages

```bash
# Start with all defaults
opensearchsql

# Use secure endpoint with credentials
opensearchsql -e https://localhost:9200 -u admin:password -k

# Use AWS SigV4 connection
opensearchsql --aws-auth amazon.com

# Use SQL and JSON output
opensearchsql -l sql -f json

# Load specific plugin version
opensearchsql -v 2.19
```

## Interactive Mode Commands

### Current Settings Displayed on Start
- **SQL Version**: `v3.1.0.0`
- **Language**: `PPL` or `SQL`
- **Format**: `TABLE`, `JSON`, or `CSV`

| Options                          | Description                                           |
|----------------------------------|-------------------------------------------------------|
| `<query>`                        | Execute a query                                       |
| `-l <type>`                      | Change language: `PPL`, `SQL`                         |
| `-f <type>`                      | Change output format: `JSON`, `TABLE`, or `CSV`       |
| `-v`                             | Toggle vertical table display mode                    |
| `-s --save <name>`               | Save the latest query result with a given name        |
| `-s --load <name>`               | Load and display a saved query result                 |
| `-s --remove <name>`             | Remove a saved query by name                          |
| `-s --list`                      | List all saved query names                            |
| `help`                           | Show this help message                                |
| `exit`, `quit`, `q`              | Exit the interactive mode                             |

### Version Switching
To use a different OpenSearch SQL plug-in version, restart the CLI with
```bash
opensearchsql -v <version number>
```

## Configure

When you first launch the SQL CLI, a configuration file is automatically created at `main/opensearchsql_cli/config/config_file` (for MacOS and Linux), the configuration is auto-loaded thereafter.

You can also configure the following connection properties:


### Connection Settings

| Key        | Description                                                                                   | Example             | Default         |
|------------|-----------------------------------------------------------------------------------------------|---------------------|-----------------|
| `endpoint` | OpenSearch URL (`http://localhost:9200`, `https://localhost:9200`, or AWS SigV4 endpoint)    | `localhost:9200`    | `localhost:9200` |
| `username` | Username for HTTPS authentication *(use `""` if not set)*                                     | `"admin"`           | `""`            |
| `password` | Password for HTTPS authentication *(use `""` if not set)*                                     | `"admin"`           | `""`            |
| `insecure` | Skip certificate validation (`-k` flag)                                                       | `true` / `false`    | `false`         |
| `aws_auth` | Use AWS SigV4 authentication                                                                  | `true` / `false`    | `false`         |

> ⚠️ **Security Warning**: Passwords stored in this file are not encrypted. Consider using `-u username:password` instead for sensitive environments.

### Query Settings

| Key        | Description                            | Options                    | Default  |
|------------|----------------------------------------|----------------------------|----------|
| `language` | Query language                         | `ppl`, `sql`               | `ppl`    |
| `format`   | Output format                          | `table`, `json`, `csv`     | `table`  |
| `vertical` | Use vertical table display mode        | `true` / `false`           | `false`  |
| `version`  | SQL plugin version (as a string)       | `"2.19"`                   | `""`     |

### SQL Plugin Settings

| Key                                             | Description                                                                 | Default  |
|--------------------------------------------------|-----------------------------------------------------------------------------|----------|
| `QUERY_SIZE_LIMIT`                              | Maximum number of rows returned per query                                  | `200`  |
| `FIELD_TYPE_TOLERANCE`                          | Tolerate field type mismatches                                             | `true`   |
| `CALCITE_ENGINE_ENABLED`                        | Enable the Calcite SQL engine                                              | `true`   |
| `CALCITE_FALLBACK_ALLOWED`                      | Fallback to legacy engine if Calcite fails                                 | `true`   |
| `CALCITE_PUSHDOWN_ENABLED`                      | Enable pushdown optimization in Calcite                                    | `true`   |
| `CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR`   | Row count estimation factor for pushdown                                   | `1.0`    |
| `SQL_CURSOR_KEEP_ALIVE`                         | Cursor keep-alive time in minutes                                          | `1`      |

> **Note**: **PPL Calcite** result is limited by `QUERY_SIZE_LIMIT` number

For a list of all available configurations, see [config.yaml](src/main/python/opensearchsql_cli/config/config.yaml).



## Using the CLI

1. Save the sample [accounts test data](https://github.com/opensearch-project/sql/blob/main/integ-test/src/test/resources/accounts.json) file.
2. Index the sample data.

    ```
    curl -H "Content-Type: application/x-ndjson" -POST https://localhost:9200/data/_bulk -u admin:< Admin password > --insecure --data-binary "@accounts.json"
    ```


1. Run a simple SQL/PPL command in OpenSearch SQL CLI:

    ```sql
    # PPL
    source=accounts
    # SQL
    SELECT * FROM accounts
    ```

The CLI supports all types of query that OpenSearch PPL/SQL supports. Refer to [OpenSearch SQL basic usage documentation.](https://github.com/opensearch-project/sql/blob/main/docs/user/dql/basics.rst)


## Code of Conduct

This project has adopted an [Open Source Code of Conduct](CODE_OF_CONDUCT.md).


## Security issue notifications

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue for security bugs you report.

## Licensing

See the [LICENSE](LICENSE.TXT) file for our project's licensing. We will ask you to confirm the licensing of your contribution.

## Copyright

Copyright OpenSearch Contributors. See [NOTICE](NOTICE) for details.
