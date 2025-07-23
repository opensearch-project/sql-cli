"""
Tests for verify_cluster.py using VCR with parametrized tests.

This module contains tests for the VerifyCluster class that handles
verification of connections to OpenSearch clusters,
using vcrpy to record and replay HTTP interactions.
"""

import pytest
import vcr
from unittest.mock import patch, MagicMock
from opensearchsql_cli.sql.verify_cluster import VerifyCluster

# Create a custom VCR instance with specific settings
my_vcr = vcr.VCR(
    cassette_library_dir="src/main/python/opensearchsql_cli/tests/sql/vcr_cassettes",
    record_mode="once",
    match_on=["uri", "method"],
    filter_headers=["authorization"],  # Don't record authorization headers
)


class TestVerifyCluster:
    """
    Test class for VerifyCluster functionality using VCR.
    """

    @pytest.mark.parametrize(
        "test_id,"
        "description,"
        "host,"
        "port,"
        "protocol,"
        "username,"
        "password,"
        "ignore_ssl,"
        "expected_success,"
        "expected_message",
        [
            # HTTP Tests
            (
                1,
                "HTTP success",
                "localhost",
                9200,
                "http",
                None,
                None,
                False,
                True,
                "success",
            ),
            # HTTPS Tests
            (
                2,
                "HTTPS success with auth",
                "localhost",
                9201,
                "https",
                "admin",
                "correct",
                True,
                True,
                "success",
            ),
            (
                3,
                "HTTPS fail with no auth provided",
                "localhost",
                9201,
                "https",
                None,
                None,
                True,
                False,
                "Unautorized 401",
            ),
            (
                4,
                "HTTPS fail with incorrect auth",
                "localhost",
                9201,
                "https",
                "admin",
                "wrong",
                True,
                False,
                "Unautorized 401",
            ),
        ],
    )
    def test_verify_opensearch_connection_vcr(
        self,
        test_id,
        description,
        host,
        port,
        protocol,
        username,
        password,
        ignore_ssl,
        expected_success,
        expected_message,
    ):
        """
        Test the verify_opensearch_connection method for different scenarios using VCR.

        This test uses a dynamic cassette name based on the test parameters.
        """

        print(f"\n=== Test #{test_id}: {description} ===")

        cassette_name = f"opensearch_connection_{protocol}_{host}_{port}_{test_id}.yaml"

        # Use VCR with the specific cassette for this test case
        with my_vcr.use_cassette(cassette_name):
            # Store the input username to compare with the returned username
            input_username = username

            success, message, version, url, returned_username = (
                VerifyCluster.verify_opensearch_connection(
                    host, port, protocol, username, password, ignore_ssl
                )
            )

            # Verify the results
            assert success == expected_success
            assert expected_message in message

            if expected_success:
                assert version is not None
                assert url == f"{protocol}://{host}:{port}"
                assert returned_username == input_username

            print(f"Result: {'Success' if success else 'Failure'}, Message: {message}")

    @pytest.mark.parametrize(
        "test_id, "
        "description, "
        "host, "
        "mock_credentials, "
        "mock_region, "
        "expected_success, "
        "expected_message",
        [
            # AWS Tests
            (
                1,
                "AWS success",
                "search-cli-test-r2qtaiqbhsnh5dgwvzkcnd5l2y.us-east-2.es.amazonaws.com",
                True,
                "us-east-2",
                True,
                "success",
            ),
            (
                2,
                "AWS fail with 403",
                "search-cli-test-r2qtaiqbhsnh5dgwvzkcnd5l2y.us-east-2.es.amazonaws.com",
                True,
                "us-west-2",
                False,
                "Forbidden 403 please verify your permissions/tokens/keys.",
            ),
        ],
    )
    def test_verify_aws_opensearch_connection_vcr(
        self,
        test_id,
        description,
        host,
        mock_credentials,
        mock_region,
        expected_success,
        expected_message,
    ):
        """
        Test the verify_aws_opensearch_connection method for different scenarios.

        This test uses a hybrid approach:
        - For success cases, it uses VCR to record/replay real HTTP interactions with real AWS credentials
        - For failure cases, it uses mocks to simulate error conditions
        """

        print(f"\n=== Test #{test_id}: {description} ===")

        cassette_name = f"aws_connection_{test_id}.yaml"

        # Use VCR for all test cases
        with my_vcr.use_cassette(cassette_name):
            success, message, version, url, region = (
                VerifyCluster.verify_aws_opensearch_connection(host)
            )
            print(
                f"Success: {success}, Message: {message}, Version: {version}, URL: {url}, Region: {region}"
            )

        # Verify the results
        assert success == expected_success
        assert expected_message in message

        if expected_success:
            assert version is not None
            assert url == f"https://{host}"
            assert region == mock_region

        print(f"Result: {'Success' if success else 'Failure'}, Message: {message}")
