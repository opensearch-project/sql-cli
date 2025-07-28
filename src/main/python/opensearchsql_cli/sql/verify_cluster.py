"""
OpenSearch Connection Verification

Handles verification of connections to OpenSearch clusters using opensearchpy.
"""

import ssl
import urllib3
import boto3
import sys
import warnings
from rich.console import Console
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import (
    ConnectionError,
    RequestError,
    AuthenticationException,
    AuthorizationException,
)
from opensearchpy.connection import create_ssl_context
from requests_aws4auth import AWS4Auth

# Disable SSL warnings from urllib3 and opensearchpy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings(
    "ignore", message="Connecting to .* using SSL with verify_certs=False is insecure"
)

# Create a console instance for rich formatting
console = Console()


class VerifyCluster:
    """
    Class for verifying connections to OpenSearch clusters.
    """

    @staticmethod
    def get_indices(client):
        """
        Get the list of indices from an OpenSearch cluster.

        Args:
            client: OpenSearch client
            print_list: Whether to print the list of indices

        Returns:
            list: List of indices
        """
        try:
            if client:
                res = client.indices.get_alias().keys()
                indices = list(res)
                return indices
            return []
        except Exception as e:
            console.print(f"[bold red]Error getting indices:[/bold red] {str(e)}")
            return []

    @staticmethod
    def verify_opensearch_connection(
        host, port, protocol="http", username=None, password=None, ignore_ssl=False
    ):
        """
        Verify connection to an OpenSearch cluster.

        Args:
            host: OpenSearch host
            port: OpenSearch port
            protocol: Protocol (http or https)
            username: Optional username for authentication
            password: Optional password for authentication
            ignore_ssl: Whether to ignore SSL certificate validation

        Returns:
            tuple: (success, message, version, url, username, client) where:
                - success: boolean indicating if the connection was successful
                - message: string message about the connection status
                - version: string version of OpenSearch if available, None otherwise
                - url: string URL of the OpenSearch endpoint
                - username: string username used for authentication if provided, None otherwise
                - client: OpenSearch client if successful, None otherwise
        """
        try:
            # Build the URL
            url = f"{protocol}://{host}:{port}"

            # Set up authentication if provided
            http_auth = None
            if username and password:
                http_auth = (username, password)

            # Set up SSL context if needed
            if protocol.lower() == "https":
                ssl_context = create_ssl_context()
                if ignore_ssl:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                # Create OpenSearch client
                client = OpenSearch(
                    [url],
                    http_auth=http_auth,
                    verify_certs=not ignore_ssl,
                    ssl_context=ssl_context,
                    connection_class=RequestsHttpConnection,
                )
            else:
                # Create OpenSearch client for HTTP
                client = OpenSearch(
                    [url],
                    http_auth=http_auth,
                    verify_certs=False,
                    connection_class=RequestsHttpConnection,
                )

            # Get cluster info
            info = client.info()

            # Extract version
            version = None
            if "version" in info and "number" in info["version"]:
                version = info["version"]["number"]

            return True, "success", version, url, username, client

        except (
            AuthenticationException,
            AuthorizationException,
            ConnectionError,
            Exception,
        ) as e:
            error_msg = f"Unable to connect {url}"
            return False, error_msg, None, url, username, None

    @staticmethod
    def verify_aws_opensearch_connection(host):
        """
        Verify connection to an AWS OpenSearch Service or OpenSearch Serverless domain using opensearchpy.

        Args:
            host: AWS OpenSearch host (without protocol)

        Returns:
            tuple: (success, message, version, url, region, client) where:
                - success: boolean indicating if the connection was successful
                - message: string message about the connection status
                - version: string version of OpenSearch if available, None otherwise
                - url: string URL of the AWS OpenSearch endpoint
                - region: string AWS region of the OpenSearch domain
                - client: OpenSearch client if successful, None otherwise
        """
        url = f"https://{host}"
        is_serverless = "aos" in host

        try:
            # Determine if this is OpenSearch Service or OpenSearch Serverless
            service = "aoss" if is_serverless else "es"

            # Get AWS credentials and region
            session = boto3.Session()
            credentials = session.get_credentials()
            region = session.region_name

            if not credentials:
                error_msg = "Unable to retrieve AWS credentials."
                return False, error_msg, None, url, None

            if not region:
                error_msg = "Unable to retrieve AWS region."
                return False, error_msg, None, url, None

            # Create AWS authentication
            aws_auth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                service,
                session_token=credentials.token,
            )

            # Create OpenSearch client
            client = OpenSearch(
                hosts=[url],
                http_auth=aws_auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
            )

            # Get cluster info
            info = client.info()

            # Extract version (serverless is versionless)
            version = "Serverless" if is_serverless else info["version"]["number"]

            return True, "success", version, url, region, client

        except (ConnectionError, Exception) as e:
            error_msg = f"Unable to connect {url}"
            return False, error_msg, None, url, None, None
        except Exception as e:
            error_msg = f"AWS Connection Verification ERROR: {str(e)}"
            return False, error_msg, None, url, None, None
