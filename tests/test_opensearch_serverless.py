import os
import pytest
from opensearch_sql_cli.opensearch_connection import OpenSearchConnection
import vcr


sql_cli_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",
    record_mode="once",
    match_on=["method", "path", "query", "body"],
)

class TestServerless:
    @pytest.fixture(scope="function")
    def aws_serverless_credentials(self):
        os.environ["TEST_ENDPOINT_URL"] = "https://example_endpoint.beta-us-east-1.aoss.amazonaws.com:443"
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"


    def test_show_tables(self, aws_serverless_credentials):
        with sql_cli_vcr.use_cassette("serverless_show_tables.yaml"):
            aes_test_executor = OpenSearchConnection(endpoint=os.environ["TEST_ENDPOINT_URL"], use_aws_authentication=True)
            aes_test_executor.set_connection()

            response = aes_test_executor.client.transport.perform_request(
                method="POST",
                url="/_plugins/_sql",
                body={"query": "SHOW TABLES LIKE %"},
                headers={"Content-Type": "application/json", "Accept-Charset": "UTF-8"},
            )

            assert response["status"] == 200
            assert response["total"] == 4
            assert response["datarows"][0][2] == ".opensearch_dashboards_1"
