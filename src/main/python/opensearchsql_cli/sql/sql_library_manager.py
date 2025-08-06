"""
SQL Library Management

Handles initialization and cleanup of the SQL Library.
"""

import os
import sys
import atexit
import logging
import subprocess
import time
import threading
import socket
from datetime import datetime
from .sql_version import sql_version
from ..config.config import config_manager

# sql-cli/src/main/python/opensearchsql_cli/sql
current_dir = os.path.dirname(os.path.abspath(__file__))
# sql-cli/
PROJECT_ROOT = os.path.normpath(os.path.join(current_dir, "../../../../../"))
JAVA_DIR = os.path.join(PROJECT_ROOT, "src", "main", "java")
AWS_DIR = os.path.join(JAVA_DIR, "client", "http5", "aws")
LOGBACK_CONFIG = os.path.abspath(
    os.path.join(PROJECT_ROOT, "src", "main", "resources", "logback.xml")
)


class SqlLibraryManager:
    """
    Manages the SQL Library initialization and cleanup
    """

    def __init__(self, port=25333):
        """
        Initialize the SQL Library manager

        Args:
            port: Port (default 25333)
        """
        self.gateway_port = port
        self.started = False
        self.process = None
        self.output_thread = None
        self.thread_running = False

        # Register cleanup function
        atexit.register(self.stop)

    def _check_port_in_use(self):
        """
        Check if the port is already in use

        Returns:
            bool: True if port is in use, False otherwise
        """
        try:
            # Try to create a socket and bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", self.gateway_port))
                return result == 0  # If result is 0, port is in use
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error checking port {self.gateway_port}: {e}")
            return False

    def _kill_process_on_port(self):
        """
        Kill any process using the specified port

        Returns:
            bool: True if process was killed or no process found, False on error
        """
        try:
            if sys.platform.startswith("win"):
                # Windows approach
                cmd = f"for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :{self.gateway_port}') do taskkill /F /PID %a"
                subprocess.run(cmd, shell=True)
            else:
                # Unix/Mac approach
                cmd = f"lsof -i :{self.gateway_port} | grep LISTEN | awk '{{print $2}}' | xargs -r kill -9"
                subprocess.run(cmd, shell=True)

            if hasattr(self, "logger"):
                self.logger.info(f"Killed any process using port {self.gateway_port}")
            return True
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(
                    f"Error killing process on port {self.gateway_port}: {e}"
                )
            return False

    def start(self):
        """
        Initialize the SQL Library

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self.started:
            return True

        self.process = None

        try:
            # Always attempt to kill any process using the port
            if self._check_port_in_use():
                if not self._kill_process_on_port():
                    return False

            # Get log file path from config or use default
            config_log_file = config_manager.get("File", "sql_log", "")
            if config_log_file and config_log_file.strip():
                log_file = config_log_file
            else:
                # Use default log file path
                log_file = os.path.join(PROJECT_ROOT, "logs", "sql_library.log")

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            self.logger = logging.getLogger("sql_library")
            self.logger.setLevel(logging.INFO)

            # Create file handler
            file_handler = logging.FileHandler(log_file, mode="a")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
            )
            self.logger.addHandler(file_handler)

            # Log startup information
            self.logger.info("=" * 80)
            self.logger.info(f"Initializing SQL Library on {time.strftime('%Y-%m-%d')}")

            jar_path = sql_version.get_jar_path()

            # Add logback configuration
            self.logger.info(f"Using logback config: {LOGBACK_CONFIG}")

            cmd = [
                "java",
                "-Dlogback.configurationFile=" + LOGBACK_CONFIG,
                "-jar",
                jar_path,
                "Gateway",
            ]
            self.logger.info(f"Using JAR file: {jar_path}")

            self.logger.info(f"Command: {' '.join(cmd)}")

            # Start the process
            self.process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Wait for the server to start
            started = False
            for _ in range(30):
                line = self.process.stdout.readline()
                self.logger.info(line.strip())
                if "Gateway Server Started" in line:
                    started = True
                    break

            if not started:
                error_msg = "Failed to start Gateway server within timeout"
                self.logger.error(error_msg)
                self.stop()
                return False

            # Start a thread to read and log output from the Java process
            self.thread_running = True

            def read_output():
                try:
                    while (
                        self.thread_running
                        and self.process
                        and self.process.poll() is None
                    ):
                        line = self.process.stdout.readline()
                        if line:
                            self.logger.info(line.strip())
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.error(f"Error in output thread: {e}")

            self.output_thread = threading.Thread(target=read_output, daemon=True)
            self.output_thread.start()

            self.started = True
            self.logger.info("SQL Library initialized successfully")

            return True

        except Exception as e:
            error_msg = f"Failed to initialize SQL Library: {e}"
            if hasattr(self, "logger"):
                self.logger.error(error_msg)
            return False

    def stop(self):
        """
        Clean up SQL Library resources

        Returns:
            bool: True if cleanup successful, False otherwise
        """
        if not self.started:
            return True

        try:
            # Signal the output thread to stop
            self.thread_running = False

            if hasattr(self, "process") and self.process:
                if sys.platform.startswith("win"):
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)]
                    )
                else:
                    self.process.kill()

                # Wait for the process to terminate
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass

                self.process = None

            # Wait for the output thread to finish
            if (
                hasattr(self, "output_thread")
                and self.output_thread
                and self.output_thread.is_alive()
            ):
                try:
                    self.output_thread.join(timeout=1)
                except Exception:
                    pass
                self.output_thread = None

            self.started = False

            aws_body_path = os.path.join(AWS_DIR, "aws_body.json")
            if os.path.exists(aws_body_path):
                os.remove(aws_body_path)
                self.logger.info("Delete " + aws_body_path)

            if hasattr(self, "logger"):
                self.logger.info("SQL Library resources cleaned up")
            return True

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error stopping SQL Library: {e}")
            return False


# Create a global instance
sql_library_manager = SqlLibraryManager()
