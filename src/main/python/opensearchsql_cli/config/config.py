"""
Configuration Management

This module provides functionality to manage configuration settings for OpenSearch CLI.
"""

import os
import yaml
from rich.console import Console

# Create a console instance for rich formatting
console = Console()


class Config:
    """
    Class for managing configuration settings
    """

    def __init__(self):
        """
        Initialize Config instance
        """
        # Set up config file path
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.config_dir, "config.yaml")

        # Initialize config as empty dictionary
        self.config = {}

        # Load config file
        self._load_config()

    def _load_config(self):
        """
        Load configuration from file
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = yaml.safe_load(f) or {}

            except Exception as e:
                console.print(
                    f"[bold yellow]WARNING:[/bold yellow] [yellow]Could not read config file: {e}[/yellow]"
                )

    def get(self, section, key, default=None):
        """
        Get a configuration value

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Value for the key or default if not found
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except (AttributeError, KeyError):
            return default

    def get_boolean(self, section, key, default=False):
        """
        Get a boolean configuration value

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Boolean value for the key or default if not found
        """
        try:
            value = self.config.get(section, {}).get(key, default)
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() == "true"
            else:
                return bool(value)
        except (AttributeError, KeyError, ValueError):
            return default

    def set(self, section, key, value):
        """
        Set a configuration value

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if section not in self.config:
                self.config[section] = {}

            self.config[section][key] = value

            with open(self.config_file, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

            return True
        except Exception as e:
            console.print(
                f"[bold red]ERROR:[/bold red] [red]Could not write to config file: {e}[/red]"
            )
            return False

    def display(self):
        """
        Display current configuration
        """
        console.print("[bold green]Current Configuration: \n[/bold green]")

        for section, items in self.config.items():
            console.print(f"[green][{section}][/green]")
            for key, value in items.items():
                # Mask password
                if section == "Connection" and key == "password" and value:
                    display_value = "********"
                else:
                    display_value = value

                console.print(f"  [green]{key}:[/green] {display_value}")

        console.print(f"[bold green]\nFile:[/bold green] {self.config_file}")


# Create a singleton instance
config_manager = Config()
