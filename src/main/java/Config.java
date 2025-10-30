/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.commons.configuration2.YAMLConfiguration;
import org.apache.commons.configuration2.ex.ConfigurationException;
import org.opensearch.common.unit.TimeValue;
import org.opensearch.sql.common.setting.Settings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Configuration handler for OpenSearch CLI Reads settings from the configuration file using Apache
 * Commons Configuration
 */
public class Config {
  private static final Logger logger = LoggerFactory.getLogger("Config");

  // Config file path
  private static final String PROJECT_ROOT = System.getProperty("user.dir");
  private static final String CONFIG_FILE =
      PROJECT_ROOT + "/src/main/python/opensearchsql_cli/config/config.yaml";

  private static YAMLConfiguration yamlConfig = null;

  /**
   * Get settings for OpenSearch SQL Library
   *
   * @return Settings object with values from the config file
   */
  public static Settings getSettings() {
    // Read settings from config file
    Map<Settings.Key, Object> configSettings = readSettingsFromConfig();

    return new Settings() {
      @Override
      public <T> T getSettingValue(Settings.Key key) {
        return (T) configSettings.get(key);
      }

      @Override
      public List<Map.Entry<Settings.Key, Object>> getSettings() {
        return List.copyOf(configSettings.entrySet());
      }
    };
  }

  /**
   * Read settings from the OpenSearch SQL CLI configuration file
   *
   * @return Map of settings
   */
  private static Map<Settings.Key, Object> readSettingsFromConfig() {
    // Default settings to use if config file is not available
    Map<Settings.Key, Object> defaultSettings =
        Map.of(
            Settings.Key.QUERY_SIZE_LIMIT, 200,
            Settings.Key.FIELD_TYPE_TOLERANCE, true,
            Settings.Key.CALCITE_ENGINE_ENABLED, true,
            Settings.Key.CALCITE_FALLBACK_ALLOWED, true,
            Settings.Key.CALCITE_PUSHDOWN_ENABLED, true,
            Settings.Key.CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR, 1.0,
            Settings.Key.SQL_CURSOR_KEEP_ALIVE, TimeValue.timeValueMinutes(1));

    try {
      // Load the YAML configuration
      loadConfig();

      // Create a mutable map to store settings
      Map<Settings.Key, Object> settings = new HashMap<>(defaultSettings);

      // Parse settings from config file
      try {
        // QUERY_SIZE_LIMIT
        if (yamlConfig.containsKey("SqlSettings.QUERY_SIZE_LIMIT")) {
          int value = yamlConfig.getInt("SqlSettings.QUERY_SIZE_LIMIT");
          settings.put(Settings.Key.QUERY_SIZE_LIMIT, value);
        }

        // FIELD_TYPE_TOLERANCE
        if (yamlConfig.containsKey("SqlSettings.FIELD_TYPE_TOLERANCE")) {
          boolean value = yamlConfig.getBoolean("SqlSettings.FIELD_TYPE_TOLERANCE");
          settings.put(Settings.Key.FIELD_TYPE_TOLERANCE, value);
        }

        // CALCITE_ENGINE_ENABLED
        if (yamlConfig.containsKey("SqlSettings.CALCITE_ENGINE_ENABLED")) {
          boolean value = yamlConfig.getBoolean("SqlSettings.CALCITE_ENGINE_ENABLED");
          settings.put(Settings.Key.CALCITE_ENGINE_ENABLED, value);
        }

        // CALCITE_FALLBACK_ALLOWED
        if (yamlConfig.containsKey("SqlSettings.CALCITE_FALLBACK_ALLOWED")) {
          boolean value = yamlConfig.getBoolean("SqlSettings.CALCITE_FALLBACK_ALLOWED");
          settings.put(Settings.Key.CALCITE_FALLBACK_ALLOWED, value);
        }

        // CALCITE_PUSHDOWN_ENABLED
        if (yamlConfig.containsKey("SqlSettings.CALCITE_PUSHDOWN_ENABLED")) {
          boolean value = yamlConfig.getBoolean("SqlSettings.CALCITE_PUSHDOWN_ENABLED");
          settings.put(Settings.Key.CALCITE_PUSHDOWN_ENABLED, value);
        }

        // CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR
        if (yamlConfig.containsKey("SqlSettings.CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR")) {
          double value =
              yamlConfig.getDouble("SqlSettings.CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR");
          settings.put(Settings.Key.CALCITE_PUSHDOWN_ROWCOUNT_ESTIMATION_FACTOR, value);
        }

        // SQL_CURSOR_KEEP_ALIVE
        if (yamlConfig.containsKey("SqlSettings.SQL_CURSOR_KEEP_ALIVE")) {
          int minutes = yamlConfig.getInt("SqlSettings.SQL_CURSOR_KEEP_ALIVE");
          settings.put(Settings.Key.SQL_CURSOR_KEEP_ALIVE, TimeValue.timeValueMinutes(minutes));
        }

      } catch (Exception e) {
        logger.error("Error parsing settings from config file: " + e.getMessage(), e);
      }

      return settings;
    } catch (Exception e) {
      logger.error("Error reading config file: " + e.getMessage(), e);
      return defaultSettings;
    }
  }

  /** Load the YAML configuration from file */
  private static void loadConfig() {
    if (yamlConfig != null) {
      return;
    }

    try {
      // Check if config file exists
      File file = new File(CONFIG_FILE);
      if (!file.exists()) {
        logger.info("Config file not found: {}", CONFIG_FILE);
        yamlConfig = new YAMLConfiguration();
        return;
      }

      logger.info("Found config file at: " + CONFIG_FILE);
      yamlConfig = new YAMLConfiguration();
      try (FileReader reader = new FileReader(file)) {
        yamlConfig.read(reader);
      }
    } catch (IOException | ConfigurationException e) {
      logger.error("Error loading configuration: {}", e.getMessage(), e);
      yamlConfig = new YAMLConfiguration();
    }
  }
}
