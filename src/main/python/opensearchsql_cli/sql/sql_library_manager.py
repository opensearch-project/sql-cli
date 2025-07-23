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

            # sql-cli/src/main/python/opensearchsql_cli/sql
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # sql-cli/
            project_root = os.path.normpath(
                os.path.join(current_dir, "../../../../../")
            )

            # Use the Java directory for logging
            java_dir = os.path.join(project_root, "src", "main", "java")

            # Set up logging
            log_file = os.path.join(java_dir, "sql_library.log")
            self.logger = logging.getLogger("sql_library")
            self.logger.setLevel(logging.INFO)

            # Create file handler
            file_handler = logging.FileHandler(log_file, mode="a")
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(file_handler)

            # Log startup information
            self.logger.info("=" * 80)
            self.logger.info(
                f"Initializing SQL Library at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # if get version from -v or config
            if sql_version.version:
                # Use the JAR file according to Sql plugin version
                jar_path = sql_version.get_jar_path(project_root)
                cmd = ["java", "-jar", jar_path, "Gateway"]
                self.logger.info(f"Using JAR file: {jar_path}")
            else:
                # Use Gradle to run the Gateway class (for development)
                # this will be removed and use 3.1 as default
                cmd = ["./gradlew", "run", "--args=Gateway"]
                self.logger.info("Using ./gradlew run for development")

            self.logger.info(f"Command: {' '.join(cmd)}")

            # Start the process
            self.process = subprocess.Popen(
                cmd,
                cwd=project_root,
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
                self.logger.info("Terminating Gateway server process")

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

            if hasattr(self, "logger"):
                self.logger.info("SQL Library resources cleaned up")
                self.logger.info("=" * 80)
            return True

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error stopping SQL Library: {e}")
            return False


# Create a global instance
sql_library_manager = SqlLibraryManager()
