"""
Tests for Configuration Management.

This module contains tests for the Configuration Management functionality.
"""

import os
import yaml
import pytest
from unittest.mock import patch, mock_open, MagicMock
from opensearchsql_cli.config.config import Config


class TestConfig:
    """
    Test class for Config.
    """

    @pytest.mark.parametrize("file_exists", [True, False])
    def test_load_config(self, file_exists, mock_config_data, mock_config_file):
        """
        Test case 1: Test loading configuration from file.
        Tests both when file exists and when it doesn't.
        """
        print(f"\n=== Testing config loading (file_exists={file_exists}) ===")

        with patch("os.path.exists", return_value=file_exists):
            config = Config()

            if file_exists:
                # If file exists, config should be loaded
                assert config.config == mock_config_data
                print(f"Config loaded successfully with {len(config.config)} sections")
                for section in config.config:
                    print(f"Section '{section}' has {len(config.config[section])} keys")
            else:
                # If file doesn't exist, config should be empty
                assert config.config == {}
                print("Config is empty as expected when file doesn't exist")

    @pytest.mark.parametrize(
        "section, key, default, expected",
        [
            ("Connection", "endpoint", None, "localhost:9200"),
            ("Connection", "nonexistent", "default_value", "default_value"),
            ("NonexistentSection", "key", "default_value", "default_value"),
        ],
    )
    def test_get_config_value(self, section, key, default, expected, mock_config_data):
        """
        Test case 2: Test getting configuration values.
        """
        print(f"\n=== Testing get config value (section={section}, key={key}) ===")

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=yaml.dump(mock_config_data))
        ):
            config = Config()

            value = config.get(section, key, default)
            assert value == expected
            print(f"Got value '{value}' for {section}.{key} (expected: {expected})")

    @pytest.mark.parametrize(
        "section, key, default, expected",
        [
            ("Connection", "insecure", None, False),
            ("SqlSettings", "FIELD_TYPE_TOLERANCE", None, True),
            ("Query", "nonexistent", True, True),
            ("Connection", "nonexistent", False, False),
        ],
    )
    def test_get_boolean_config_value(
        self, section, key, default, expected, mock_config_data
    ):
        """
        Test case 3: Test getting boolean configuration values.
        """
        print(
            f"\n=== Testing get boolean config value (section={section}, key={key}) ==="
        )

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=yaml.dump(mock_config_data))
        ):
            config = Config()

            value = config.get_boolean(section, key, default)
            assert value is expected
            print(
                f"Got boolean value '{value}' for {section}.{key} (expected: {expected})"
            )

    def test_set_config_value(self, mock_config_data):
        """
        Test case 4: Test setting configuration values.
        """
        print("\n=== Testing set config value ===")

        # Create a mock for the open function for both reading and writing
        mock_file = mock_open(read_data=yaml.dump(mock_config_data))

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_file
        ):
            config = Config()

            # Test setting a value in an existing section
            result = config.set("Connection", "endpoint", "new-endpoint:9200")
            assert result is True
            assert config.config["Connection"]["endpoint"] == "new-endpoint:9200"
            print("Successfully set value in existing section")

            # Test setting a value in a new section
            result = config.set("NewSection", "new_key", "new_value")
            assert result is True
            assert config.config["NewSection"]["new_key"] == "new_value"
            print("Successfully set value in new section")

            # Verify the file was written to
            mock_file.assert_called_with(config.config_file, "w")
            print("Config file was written to")

    def test_display_config(self, mock_config_data):
        """
        Test case 5: Test displaying configuration.
        """
        print("\n=== Testing display config ===")

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=yaml.dump(mock_config_data))
        ), patch("opensearchsql_cli.config.config.console") as mock_console:
            config = Config()

            # Call display method
            config.display()

            # Verify console.print was called
            assert mock_console.print.call_count > 0
            print(f"Console.print was called {mock_console.print.call_count} times")

            # Check that password masking works
            config.config["Connection"]["password"] = "secret"
            config.display()

            # Find the call that would display the password
            password_masked = False
            for call in mock_console.print.call_args_list:
                if "********" in str(call):
                    password_masked = True
                    break

            assert password_masked
            print("Password was properly masked in display")
