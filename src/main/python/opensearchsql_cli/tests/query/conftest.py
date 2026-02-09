"""
Pytest configuration file for opensearchsql-cli query tests.

This file contains fixtures and configuration for pytest tests.
"""

import os
import sys
import json
import pytest
import tempfile
import warnings
from unittest.mock import MagicMock, patch


# Fixtures for query execution
@pytest.fixture
def mock_csv_response():
    """
    Fixture that returns a mock CSV response.
    """
    return "name,hire_date,department,age\nTest,1999-01-01 00:00:00,Engineering,20"


@pytest.fixture
def mock_json_response():
    """
    Fixture that returns a mock JSON/table response.
    This can be used for both JSON format and table format (horizontal/vertical).
    """
    return """
    {
    "schema": [
        {
        "name": "name",
        "type": "string"
        },
        {
        "name": "hire_date",
        "type": "timestamp"
        },
        {
        "name": "department",
        "type": "string"
        },
        {
        "name": "age",
        "type": "integer"
        }
    ],
    "datarows": [
        [
        "Test",
        "1999-01-01 00:00:00",
        "Engineering",
        20
        ]
    ],
    "total": 1,
    "size": 1
    }
    """


@pytest.fixture
def mock_table_response():
    """
    Fixture that returns a mock table response.
    This is the formatted horizontal table output for display.
    """
    return """
Fetched 1 rows with a total of 1 hits
┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━┓
┃ name  ┃ hire_date           ┃ department  ┃ age ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━┩
│ Test  │ 1999-01-01 00:00:00 │ Engineering │ 20  │
├───────┼─────────────────────┼─────────────┼─────┤
"""


@pytest.fixture
def mock_vertical_response():
    """
    Fixture that returns a mock vertical table response.
    This is the formatted vertical table output for display.
    """
    return """
Fetched 1 rows with a total of 1 hits
              RECORD 1              
┌────────────┬─────────────────────┐
│ name       │ Test                │
├────────────┼─────────────────────┤
│ hire_date  │ 1999-01-01 00:00:00 │
├────────────┼─────────────────────┤
│ department │ Engineering         │
├────────────┼─────────────────────┤
│ age        │ 20                  │
└────────────┴─────────────────────┘
"""


@pytest.fixture
def mock_calcite_explain():
    """
    Fixture that returns a mock Calcite explain plan.
    """
    return r"""
{
"calcite": {
"logical": "LogicalProject(name=[$0], hire_date=[$1], department=[$2], age=[$3])\n  CalciteLogicalIndexScan(table=[[OpenSearch, employees]])\n",
"physical": "CalciteEnumerableIndexScan(table=[[OpenSearch, employees]], PushDownContext=[[PROJECT->[name, hire_date, department, age]], OpenSearchRequestBuilder(sourceBuilder={\"from\":0,\"timeout\":\"1m\",\"_source\":{\"includes\":[\"name\",\"hire_date\",\"department\",\"age\"],\"excludes\":[]}}, requestedTotalSize=99999, pageSize=null, startFrom=0)])\n"
}
}
    """


@pytest.fixture
def mock_legacy_explain():
    """
    Fixture that returns a mock Calcite explain plan.
    """
    return r"""{
"root": {
"name": "ProjectOperator",
"description": {
"fields": "[name, hire_date, department, age]"
},
"children": [
{
"name": "OpenSearchIndexScan",
"description": {
"request": "OpenSearchQueryRequest(indexName=employees, sourceBuilder={\"from\":0,\"size\":10000,\"timeout\":\"1m\",\"_source\":{\"includes\":[\"name\",\"hire_date\",\"department\",\"age\"],\"excludes\":[]}}, needClean=true, searchDone=false, pitId=s9y3QQEJZW1wbG95ZWVzFmNsWWhicUdrVFBXUXRpM1FKdHBrSVEAFmpMNjJzN3QzUjR1QzB1NURUNDAwUHcAAAAAAAAAAAcWVi1KUEZNdDJTQ0dIMjlXbDhrUDl6UQEWY2xZaGJxR2tUUFdRdGkzUUp0cGtJUQAA, cursorKeepAlive=1m, searchAfter=null, searchResponse=null)"
},
"children": []
}
]
}
}"""


@pytest.fixture
def mock_syntax_error_response():
    """
    Fixture that returns a mock syntax error response.
    """
    return "Invalid query: queryExecution Error: org.opensearch.sql.common.antlr.SyntaxCheckException:"


@pytest.fixture
def mock_semantic_error_response():
    """
    Fixture that returns a mock semantic error response.
    """
    return "Invalid query: queryExecution Error: org.opensearch.sql.common.antlr.SyntaxCheckException:"


@pytest.fixture
def mock_index_not_found_response():
    """
    Fixture that returns a mock index not found error response.
    """
    return "Invalid query: queryExecution Error: java.lang.RuntimeException: [a] OpenSearchStatusException[OpenSearch exception [type=index_not_found_exception, reason=no such index [a]]]"


@pytest.fixture
def mock_null_statement_response():
    """
    Fixture that returns a mock null statement error response.
    """
    return 'Invalid query: queryExecution Execution Error: java.lang.NullPointerException: Cannot invoke "Object.getClass()" because "statement" is null'


# Fixtures for saved queries tests
@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for saved queries.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def saved_queries(temp_dir):
    """
    Create a SavedQueries instance with a temporary directory.
    """
    from opensearchsql_cli.query.saved_queries import SavedQueries

    return SavedQueries(base_dir=temp_dir)


@pytest.fixture
def mock_console():
    """
    Mock the console.print method.
    """
    with patch("opensearchsql_cli.query.saved_queries.console") as mock_console:
        yield mock_console


@pytest.fixture
def mock_connection():
    """
    Mock the SQL connection.
    """
    mock_connection = MagicMock()
    mock_connection.query_executor.return_value = (
        '{"schema":[{"name":"test"}],"datarows":[["value"]]}'
    )
    return mock_connection


# Fixtures for enhanced error reports (ErrorReport format)
@pytest.fixture
def mock_error_report_syntax():
    """
    Fixture that returns a mock syntax error in ErrorReport format.
    """
    return """Exception: {
  "status": 400,
  "error": {
    "type": "ErrorReport",
    "code": "SYNTAX_ERROR",
    "reason": "Invalid Query",
    "details": "[fieldz] is not a valid term at this part of the query: 'source=big5 | fieldz' <-- HERE. Expecting one of 48 possible tokens. Some examples: 'WHERE', 'FIELDS', 'TABLE', 'RENAME', 'STATS', ...",
    "location": [
      "while parsing the query"
    ],
    "context": {
      "query": "source=big5 | fieldz message",
      "position": {
        "line": 1,
        "column": 14
      },
      "offending_token": "fieldz"
    },
    "suggestion": "Expected one of 48 possible tokens. Examples: 'WHERE', 'FIELDS', 'TABLE', 'RENAME', 'STATS'"
  }
}"""


@pytest.fixture
def mock_error_report_field():
    """
    Fixture that returns a mock field not found error in ErrorReport format.
    """
    return """Exception: {
  "status": 400,
  "error": {
    "type": "ErrorReport",
    "code": "FIELD_NOT_FOUND",
    "reason": "Invalid Query",
    "details": "Field [messag] not found.",
    "location": [
      "while resolving field references"
    ],
    "context": {
      "field_name": "messag",
      "position": {
        "line": 1,
        "column": 21
      },
      "available_fields": ["agent", "agent.ephemeral_id", "agent.id", "agent.name", "agent.type", "event.dataset", "host.name", "message"]
    },
    "suggestion": "Did you mean: 'message'?"
  }
}"""


@pytest.fixture
def mock_error_report_field_removed():
    """
    Fixture that returns a mock field removed by fields command error in ErrorReport format.
    """
    return """Exception: {
  "status": 400,
  "error": {
    "type": "ErrorReport",
    "code": "FIELD_NOT_FOUND",
    "reason": "Invalid Query",
    "details": "Field [host.name] not found.",
    "location": [
      "while resolving field references"
    ],
    "context": {
      "field_name": "host.name",
      "position": {
        "line": 1,
        "column": 37
      },
      "fields_command_used": true,
      "available_fields": ["message"]
    },
    "suggestion": "Field [host.name] not in current context. Note: A 'fields' command earlier in the query removed fields not explicitly listed. Current fields: 'message'"
  }
}"""


@pytest.fixture
def mock_error_report_is_not_null():
    """
    Fixture that returns a mock IS NOT NULL syntax error in ErrorReport format.
    """
    return """Exception: {
  "status": 400,
  "error": {
    "type": "ErrorReport",
    "code": "SYNTAX_ERROR",
    "reason": "Invalid Query",
    "details": "[is] is not a valid term at this part of the query: '...ig5 | where message is' <-- HERE. Expecting one of 24 possible tokens. Some examples: EOF, 'IN', 'NOT', 'OR', 'AND', ...",
    "location": [
      "while parsing the query"
    ],
    "context": {
      "query": "source=big5 | where message is not null",
      "position": {
        "line": 1,
        "column": 28
      },
      "offending_token": "is"
    },
    "suggestion": "PPL doesn't support 'IS NOT NULL' syntax. Use isnotnull(message) function instead."
  }
}"""
