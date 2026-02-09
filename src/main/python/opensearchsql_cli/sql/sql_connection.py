"""
SQL Library Connection Management

Handles connection to SQL library and OpenSearch Cluster configuration.
"""

from py4j.java_gateway import JavaGateway, GatewayParameters
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from .sql_library_manager import sql_library_manager
from .verify_cluster import VerifyCluster
from .sql_version import sql_version
from ..config.config import config_manager

# Create a console instance for rich formatting
console = Console()


class DirectRestExecutor:
    """
    Executor that sends queries directly to the OpenSearch cluster REST API
    without using the local Java gateway
    """

    def __init__(self, url, username=None, password=None, verify_ssl=True):
        """
        Initialize the DirectRestExecutor

        Args:
            url: Base URL of the OpenSearch cluster (e.g., "https://localhost:9200")
            username: Optional username for authentication
            password: Optional password for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.auth = HTTPBasicAuth(username, password) if username and password else None

    def execute_query(self, query, is_ppl=True, is_explain=False, format="json"):
        """
        Execute a query directly against the cluster REST API

        Args:
            query: The SQL or PPL query string
            is_ppl: True if the query is PPL, False if SQL
            is_explain: True if query is explain
            format: Output format (json, table, csv)

        Returns:
            Query result string formatted according to the specified format
        """
        try:
            # Determine the endpoint
            endpoint = "/_plugins/_ppl" if is_ppl else "/_plugins/_sql"

            # Build the request body
            body = {"query": query}

            # Add format parameter for non-explain queries
            if not is_explain:
                if format.lower() == "csv":
                    body["format"] = "csv"
                elif format.lower() == "table" or format.lower() == "json":
                    body["format"] = "jdbc"

            # For explain queries, use the explain endpoint
            if is_explain:
                endpoint = f"{endpoint}/_explain"

            # Make the request
            response = requests.post(
                f"{self.url}{endpoint}",
                json=body,
                auth=self.auth,
                verify=self.verify_ssl,
                headers={"Content-Type": "application/json"}
            )

            # Check for HTTP errors
            response.raise_for_status()

            # For CSV format, return the raw text
            if format.lower() == "csv" and not is_explain:
                return response.text

            # For other formats, parse JSON and format appropriately
            result_json = response.json()

            # Handle explain responses
            if is_explain:
                return json.dumps(result_json, indent=2)

            # For regular queries, return formatted JSON
            return json.dumps(result_json, indent=2)

        except requests.exceptions.RequestException as e:
            # Handle connection errors
            error_msg = f"Request failed: {str(e)}"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_msg = json.dumps(error_json, indent=2)
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            return f"Exception: {error_msg}"
        except Exception as e:
            return f"Exception: {str(e)}"


class SqlConnection:
    """
    SqlConnection class for managing SQL library and OpenSearch connections
    """

    def __init__(self, port=25333):
        """
        Initialize a Connection instance

        Args:
            port: Gateway port (default 25333)
        """
        self.gateway_port = port
        self.sql_lib = None
        self.sql_connected = False
        self.opensearch_connected = False
        self.error_message = None

        # Connection parameters
        self.host = None
        self.port_num = None
        self.protocol = "http"
        self.username = None
        self.password = None

        # Store OpenSearch verification results
        self.cluster_version = None
        self.url = None
        self.client = None

        # Remote mode (direct REST API) support
        self.remote_mode = False
        self.direct_executor = None
        self.ignore_ssl = False

    def verify_opensearch_connection(
        self, host_port=None, username_password=None, ignore_ssl=False, aws_auth=False
    ):
        """
        Verify connection to an OpenSearch cluster

        Args:
            host_port: Optional host:port string for OpenSearch Cluster connection
            username_password: Optional username:password string for authentication
            ignore_ssl: Whether to ignore SSL certificate validation
            aws_auth: Whether to use AWS SigV4 authentication

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Store ignore_ssl for later use
            self.ignore_ssl = ignore_ssl

            # Parse username_password if provided
            if username_password and ":" in username_password:
                self.username, self.password = username_password.split(":", 1)

            if aws_auth:
                # AWS SigV4 authentication
                if not host_port:
                    console.print(
                        "[bold red]ERROR:[/bold red] [red]URL is required for AWS Authentication[/red]"
                    )
                    return False

                # Remove protocol prefix if present
                if "://" in host_port:
                    self.protocol, host_port = host_port.split("://", 1)

                # Store the AWS host
                self.host = host_port

                # Verify AWS connection
                success, message, cluster_version, url, region, client = (
                    VerifyCluster.verify_aws_opensearch_connection(host_port)
                )
                if not success:
                    self.error_message = message
                    return False

                # Store connection information
                self.cluster_version = cluster_version
                self.url = url
                self.client = client
                self.username = (
                    f"{region}"  # Use region as the "username" for AWS connections
                )
                return True
            elif host_port:
                # Handle URLs with protocol
                if "://" in host_port:
                    self.protocol, host_port = host_port.split("://", 1)

                # Parse host and port
                if ":" in host_port:
                    self.host, port_str = host_port.split(":", 1)

                    try:
                        self.port_num = int(port_str)
                    except ValueError:
                        console.print(
                            f"[bold red]ERROR:[/bold red] [red]Invalid port: {port_str}[/red]"
                        )
                        return False
                else:
                    self.host = host_port
                    # Set default port based on protocol
                    if self.protocol.lower() == "http":
                        self.port_num = 9200
                    elif self.protocol.lower() == "https":
                        self.port_num = 443

                # Verify connection using parsed values
                success, message, cluster_version, url, username, client = (
                    VerifyCluster.verify_opensearch_connection(
                        self.host,
                        self.port_num,
                        self.protocol,
                        self.username,
                        self.password,
                        ignore_ssl,
                    )
                )
                if not success:
                    self.error_message = message
                    return False

                # Store connection information
                self.cluster_version = cluster_version
                self.url = url
                self.client = client
                if username:
                    self.username = username

                return True

            return False

        except Exception as e:
            self.error_message = f"Unable to connect to {host_port}: {str(e)}"
            return False

    def initialize_sql_library(
        self, host_port=None, username_password=None, ignore_ssl=False, aws_auth=False
    ):
        """
        Initialize SQL Library with OpenSearch connection parameters.
        This is called after verify_opensearch_connection has succeeded.
        This will also connect to the SQL library if it's not already connected.

        Args:
            host_port: Optional host:port string for OpenSearch Cluster connection
            username_password: Optional username:password string for authentication
            ignore_ssl: Whether to ignore SSL certificate validation
            aws_auth: Whether to use AWS SigV4 authentication

        Returns:
            bool: True if successful, False otherwise
        """
        # Connect to the SQL library if not already connected
        if not self.sql_connected or not self.sql_lib:
            if not self.connect():
                return False

        try:
            # Initialize the connection in Java based on the verification results
            if aws_auth:
                result = self.sql_lib.entry_point.initializeAwsConnection(
                    self.host,
                )
            else:
                result = self.sql_lib.entry_point.initializeConnection(
                    self.host,
                    self.port_num,
                    self.protocol,
                    self.username,
                    self.password,
                    ignore_ssl,
                )

            # Check for successful initialization
            self.opensearch_connected = result
            self.error_message = (
                "Failed to initialize SQL library" if not result else None
            )
            return result

        except Exception as e:
            self.error_message = f"Unable to initialize SQL library: {str(e)}"
            self.opensearch_connected = False
            return False

    def connect(self):
        """
        Connect to the SQL library

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Start the SQL Library server if it's not already running
            if not sql_library_manager.started:
                if not sql_library_manager.start():
                    console.print("[bold red]Failed to connect to the SQL gateway. See logs/sql_library.log for details.[/bold red]")
                    return False

            # Connect to the SQL Library
            self.sql_lib = JavaGateway(
                gateway_parameters=GatewayParameters(port=self.gateway_port)
            )
            self.sql_connected = True
            return True
        except Exception as e:
            console.print(
                f"[bold red]Failed to connect to SQL on port {self.gateway_port}: {e}[/bold red]"
            )
            self.sql_connected = False
            return False

    def set_remote_mode(self, enabled=True):
        """
        Enable or disable remote mode (direct REST API connection)

        Args:
            enabled: Whether to enable remote mode

        Returns:
            bool: True if successful, False otherwise
        """
        self.remote_mode = enabled

        if enabled and self.url:
            # Initialize the direct executor
            self.direct_executor = DirectRestExecutor(
                url=self.url,
                username=self.username,
                password=self.password,
                verify_ssl=not self.ignore_ssl
            )
            # Mark as connected in remote mode
            self.opensearch_connected = True
            return True
        return False

    def query_executor(self, query, is_ppl=True, is_explain=False, format="json"):
        """
        Execute a query through the SQL Library service or direct REST API

        Args:
            query: The SQL or PPL query string
            is_ppl: True if the query is PPL, False if SQL (default: True)
            is_explain: True if query is explain (default: False)
            format: Output format (json, table, csv) (default: json)

        Returns:
            Query result string formatted according to the specified format
        """
        # Use direct REST API in remote mode
        if self.remote_mode and self.direct_executor:
            return self.direct_executor.execute_query(query, is_ppl, is_explain, format)

        # Otherwise use the Java gateway
        if not self.sql_connected or not self.sql_lib:
            console.print(
                "[bold red]ERROR:[/bold red] [red]Unable to connect to SQL library[/red]"
            )
            return "Error: Not connected to SQL library"

        if not self.opensearch_connected:
            console.print(
                "[bold red]ERROR:[/bold red] [red]Unable to connect to OpenSearch Cluster[/bold red]"
            )
            return "Error: Not connected to OpenSearch Cluster"

        query_service = self.sql_lib.entry_point
        # queryExecution inside of Gateway.java
        result = query_service.queryExecution(query, is_ppl, is_explain, format)
        return result


# Create a global connection instance
sql_connection = SqlConnection()
