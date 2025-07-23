"""
Tests for OpenSearch Literals.

This module contains tests for the OpenSearch Literals functionality.
"""

import os
import json
import pytest
from unittest.mock import patch, mock_open
from rich.text import Text
from opensearchsql_cli.literals.opensearch_literals import Literals


class TestLiterals:
    """
    Test class for OpenSearch Literals.
    """

    @pytest.mark.parametrize(
        "language, expected_keyword, expected_function, mock_data",
        [
            (
                "ppl",
                "source",
                "count",
                {
                    "keywords": ["source", "where", "fields"],
                    "functions": ["count", "sum", "avg"],
                },
            ),
            (
                "sql",
                "FROM",
                "COUNT",
                {
                    "keywords": ["FROM", "SELECT", "WHERE"],
                    "functions": ["COUNT", "SUM", "AVG"],
                },
            ),
        ],
    )
    def test_get_literals_loads_json_files(
        self,
        language,
        expected_keyword,
        expected_function,
        mock_data,
    ):
        """
        Test case 1: Verify that the JSON files for PPL and SQL are loaded correctly.
        Uses parametrize to test both PPL and SQL literals.
        """
        print(f"\n=== Testing {language.upper()} literals loading ===")

        # Mock the file opening and reading
        with patch(
            "os.path.join",
            return_value=f"mock_path/opensearch_literals_{language}.json",
        ), patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):

            # Load literals for the specified language
            print(f"Loading {language.upper()} literals...")
            literals = Literals.get_literals(language=language)

        # Verify the structure
        assert isinstance(literals, dict)
        assert "keywords" in literals
        assert "functions" in literals
        assert isinstance(literals["keywords"], list)
        assert isinstance(literals["functions"], list)

        # Verify expected keywords and functions
        assert expected_keyword in literals["keywords"]
        assert expected_function in literals["functions"]

        # Print information
        print(
            f"{language.upper()} literals loaded successfully: {len(literals['keywords'])} keywords, {len(literals['functions'])} functions"
        )
        print(
            f"Sample {language.upper()} keywords: {', '.join(literals['keywords'][:5])}"
        )
        print(
            f"Sample {language.upper()} functions: {', '.join(literals['functions'][:5])}"
        )

    @pytest.mark.parametrize(
        "language, keyword, function",
        [("SQL", "FROM", "COUNT"), ("PPL", "source", "count")],
    )
    def test_colorize_keywords_and_functions(
        self,
        language,
        keyword,
        function,
        mock_sql_literals_data,
        mock_ppl_literals_data,
    ):
        """
        Test case 2: Verify that keywords are colorized as bold green and functions as green.
        Uses parametrize to test both SQL and PPL keywords and functions.
        """
        print(f"\n=== Testing {language} keyword and function colorization ===")

        # Use the mock literals data from fixtures
        mock_literals = (
            mock_ppl_literals_data if language == "PPL" else mock_sql_literals_data
        )

        print(
            f"Mock {language} literals created with keywords: {', '.join(mock_literals['keywords'])}"
        )
        print(
            f"Mock {language} literals created with functions: {', '.join(mock_literals['functions'])}"
        )

        print(f"\nTesting {language} keyword colorization: bold green")
        keyword_text = Literals.colorize_keywords(keyword, mock_literals)
        assert isinstance(keyword_text, Text)
        assert keyword_text.style == "bold green"
        print(f"Keyword '{keyword}' colorized with style: {keyword_text.style}")

        print(f"\nTesting {language} function colorization: green")
        function_text = Literals.colorize_keywords(function, mock_literals)
        assert isinstance(function_text, Text)
        assert function_text.style == "green"
        print(f"Function '{function}' colorized with style: {function_text.style}")

        print(f"\nTesting {language} case-insensitivity for keywords")
        keyword_text_lower = Literals.colorize_keywords(keyword.lower(), mock_literals)
        assert isinstance(keyword_text_lower, Text)
        assert keyword_text_lower.style == "bold green"
        print(
            f"Lowercase keyword '{keyword.lower()}' colorized with style: {keyword_text_lower.style}"
        )

        print(f"\nTesting {language} case-insensitivity for functions")
        function_text_lower = Literals.colorize_keywords(
            function.lower(), mock_literals
        )
        assert isinstance(function_text_lower, Text)
        assert function_text_lower.style == "green"
        print(
            f"Lowercase function '{function.lower()}' colorized with style: {function_text_lower.style}"
        )

        print(f"\nTesting {language} non-keyword, non-function text: plain text")
        plain_text = Literals.colorize_keywords("table_name", mock_literals)
        assert isinstance(plain_text, str)
        print(
            f"Non-keyword/function 'table_name' remains as type: {type(plain_text).__name__}"
        )
