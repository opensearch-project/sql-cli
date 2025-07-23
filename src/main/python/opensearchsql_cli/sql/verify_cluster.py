"""
OpenSearch Connection Verification

Handles verification of connections to OpenSearch clusters.
"""

import ssl
import urllib3
import requests
import boto3
from rich.console import Console
from requests_aws4auth import AWS4Auth
from urllib.parse import urlparse
import sys

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a console instance for rich formatting
console = Console()


class VerifyCluster:
    """
    Class for verifying connections to OpenSearch clusters.
    """

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
            tuple: (success, message, version, url, username) where:
                - success: boolean indicating if the connection was successful
                - message: string message about the connection status
                - version: string version of OpenSearch if available, None otherwise
                - url: string URL of the OpenSearch endpoint
                - username: string username used for authentication if provided, None otherwise
        """
        try:
            # Build the URL
            url = f"{protocol}://{host}:{port}"

            # Set up request headers
            headers = {"Content-Type": "application/json"}

            # Set up authentication if provided
            auth = None
            if username and password:
                auth = (username, password)

            # Set up SSL verification
            verify = True
            if ignore_ssl and protocol.lower() == "https":
                verify = False

            # Make the request
            response = requests.get(
                url, headers=headers, auth=auth, verify=verify, timeout=10
            )

            # Check the response
            if response.status_code == 200:

                # Try to parse the response to get version information
                version = None
                try:
                    data = response.json()
                    if "version" in data and "number" in data["version"]:
                        version = data["version"]["number"]
                except Exception:
                    pass

                return True, "success", version, url, username
            if response.status_code == 401:
                error_msg = f"Unautorized 401 please verify your username/password."
                return False, error_msg, None, url, username
            elif response.status_code == 403:
                error_msg = f"Forbidden 403 please verify your username/password."
            elif response.status_code == 503:
                error_msg = f"Service Unavailable 503 please verify {url}."
            else:
                error_msg = f"{response.status_code}"
                return False, error_msg, None, url, username

        except Exception as e:
            err_str = str(e)
            # print(err_str)
            if any(
                e in err_str
                for e in (
                    "NewConnectionError",
                    "RemoteDisconnected",
                    "NameResolutionError",
                )
            ):
                error_msg = f"Unable to connect {url}"
            elif "ConnectTimeoutError" in err_str:
                error_msg = f"Connection timeout at {url}"
            elif "SSL: WRONG_VERSION_NUMBER" in err_str:
                error_msg = "Please check the correct protocol: HTTP/HTTPS"
            elif "SSLCertVerificationError" in err_str:
                error_msg = "Unable to verify SSL Certificate. Try adding -k flag"
            else:
                error_msg = f"Connection Verification ERROR: {err_str}"
            return False, error_msg, None, url if "url" in locals() else None, username

    @staticmethod
    def verify_aws_opensearch_connection(host):
        """
        Verify connection to an AWS OpenSearch Service or OpenSearch Serverless domain.

        Args:
            host: AWS OpenSearch host (without protocol)

        Returns:
            tuple: (success, message, version, url, region) where:
                - success: boolean indicating if the connection was successful
                - message: string message about the connection status
                - version: string version of OpenSearch if available, None otherwise
                - url: string URL of the AWS OpenSearch endpoint
                - region: string AWS region of the OpenSearch domain
        """

        url = None

        try:
            # Determine if this is OpenSearch Service or OpenSearch Serverless
            service_name = "aoss" if ".aoss." in host else "es"
            # print(f"Using service name '{service_name}' for AWS authentication")

            # Get AWS credentials and region
            session = boto3.Session()
            credentials = session.get_credentials()
            region = session.region_name

            if not credentials:
                error_msg = "Unable to retrieve AWS credentials."
                return False, error_msg, None, None, None

            if not region:
                error_msg = "Unable to retrieve AWS region."
                return False, error_msg, None, None, None

            # Create AWS authentication
            auth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                service_name,
                session_token=credentials.token,
            )

            # Build the URL
            url = f"https://{host}"

            # Make the request
            response = requests.get(url, auth=auth, timeout=10)

            # Check the response
            if response.status_code == 200:

                # Try to parse the response to get version information
                version = None
                try:
                    data = response.json()
                    if "version" in data and "number" in data["version"]:
                        version = data["version"]["number"]
                except Exception:
                    pass

                return True, "success", version, url, region
            if response.status_code == 403:
                error_msg = f"Forbidden 403 please verify your permissions/tokens/keys."
                return False, error_msg, None, url, region
            else:
                error_msg = f"{response.status_code}"
                return False, error_msg, None, url, region

        except Exception as e:
            err_str = str(e)
            # print(err_str)
            if "AWS_SECRET_ACCESS_KEY" in err_str:
                error_msg = "missing AWS_SECRET_ACCESS_KEY"
            else:
                error_msg = f"Unable to connect AWS server - {url}.\nPlease check your AWS Credentials/Configurations"
            return False, error_msg, None, url, None
