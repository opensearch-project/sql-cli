"""
Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0
"""

import mock
from textwrap import dedent

from click.testing import CliRunner

from .utils import estest, load_data, TEST_INDEX_NAME
from src.opensearch_sql_cli.main import cli
from src.opensearch_sql_cli.opensearchsql_cli import OpenSearchSqlCli

INVALID_ENDPOINT = "http://invalid:9200"
ENDPOINT = "http://localhost:9200"
# In OS >= 2.17, limit defaults to 10k, otherwise it's 200. Specify manually for consistency.
QUERY = "select * from %s LIMIT 150" % TEST_INDEX_NAME


class TestMain:
    @estest
    def test_explain(self, connection):
        doc = {"a": "aws"}
        load_data(connection, doc)

        err_message = "Can not connect to endpoint %s" % INVALID_ENDPOINT
        expected_tabular_output = dedent(
            """\
            fetched rows / total rows = 1/1
            +-----+
            | a   |
            |-----|
            | aws |
            +-----+"""
        )

        with mock.patch("src.opensearch_sql_cli.main.click.echo") as mock_echo, mock.patch(
            "src.opensearch_sql_cli.main.click.secho"
        ) as mock_secho:
            runner = CliRunner()

            # test -q -e
            result = runner.invoke(cli, [f"-q{QUERY}", "-e"])
            # The scan's "request" is the SQL plugin's internal query
            # representation, and its exact text changes between server releases
            # (PIT fields, dropped "excludes", dropped "searchDone", ...).
            # Assert the plan structure exactly and only the stable parts of the
            # request, so this does not break on every server bump.
            explain_output = mock_echo.call_args[0][0]
            root = explain_output["root"]
            assert root["name"] == "ProjectOperator"
            assert root["description"] == {"fields": "[a]"}

            scan = root["children"][0]
            assert scan["name"] == "OpenSearchIndexScan"
            assert scan["children"] == []

            request = scan["description"]["request"]
            assert "indexName=%s" % TEST_INDEX_NAME in request
            assert '"size":150' in request
            assert '"includes":["a"]' in request
            assert result.exit_code == 0

            # test -q
            result = runner.invoke(cli, [f"-q{QUERY}"])
            mock_echo.assert_called_with(expected_tabular_output)
            assert result.exit_code == 0

            # test invalid endpoint
            runner.invoke(cli, [INVALID_ENDPOINT, f"-q{QUERY}", "-e"])
            mock_secho.assert_called_with(message=err_message, fg="red")

    @estest
    def test_cli(self):
        with mock.patch.object(OpenSearchSqlCli, "connect") as mock_connect, mock.patch.object(
            OpenSearchSqlCli, "run_cli"
        ) as mock_run_cli:
            runner = CliRunner()
            result = runner.invoke(cli)

            mock_connect.assert_called_with(ENDPOINT, None)
            mock_run_cli.asset_called()
            assert result.exit_code == 0
