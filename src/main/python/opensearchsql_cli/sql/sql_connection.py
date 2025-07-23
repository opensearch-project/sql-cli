"""
SQL Library Connection Management

Handles connection to SQL library and OpenSearch Cluster configuration.
"""

from py4j.java_gateway import JavaGateway, GatewayParameters
import sys
from rich.console import Console
from .sql_library_manager import sql_library_manager
from .verify_cluster import VerifyCluster
from ..config.config import config_manager

# Create a console instance for rich formatting
console = Console()


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
                success, message, cluster_version, url, region = (
                    VerifyCluster.verify_aws_opensearch_connection(host_port)
                )
                if not success:
                    self.error_message = message
                    return False

                # Store connection information
                self.cluster_version = cluster_version
                self.url = url
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
                success, message, cluster_version, url, username = (
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
                result = self.sql_lib.entry_point.initializeAwsConnection(self.host)
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
            if result:
                self.opensearch_connected = True
                return True
            else:
                self.error_message = "Failed to initialize SQL library"
                self.opensearch_connected = False
                return False

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
                    console.print("[bold red]Failed to connect SQL Library[/bold red]")
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

    def query_executor(self, query: str, is_ppl: bool = True, format: str = "json"):
        """
        Execute a query through the SQL Library service

        Args:
            query: The SQL or PPL query string
            is_ppl: True if the query is PPL, False if SQL (default: True)
            format: Output format (json, table, csv) (default: json)

        Returns:
            Query result string formatted according to the specified format
        """
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
        result = query_service.queryExecution(query, is_ppl, format)
        return result


# Create a global connection instance
sql_connection = SqlConnection()
