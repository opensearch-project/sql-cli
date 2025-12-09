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
import org.opensearch.common.settings.Setting;
import org.opensearch.common.unit.TimeValue;
import org.opensearch.sql.common.setting.Settings;
import org.opensearch.sql.opensearch.setting.OpenSearchSettings;
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
        if (!configSettings.containsKey(key)) {
          throw new IllegalArgumentException("Key " + key + " not found");
        }
        return (T) configSettings.get(key);
      }

      @Override
      public List<Map.Entry<Settings.Key, Object>> getSettings() {
        return List.copyOf(configSettings.entrySet());
      }
    };
  }

  /**
   * Get default settings from OpenSearchSettings plugin
   *
   * @return Map of default settings extracted from OpenSearchSettings
   */
  private static Map<Settings.Key, Object> getDefaultSettingsFromPlugin() {
    Map<Settings.Key, Object> defaults = new HashMap<>();
    org.opensearch.common.settings.Settings emptySettings =
        org.opensearch.common.settings.Settings.EMPTY;

    for (Setting<?> setting : OpenSearchSettings.pluginSettings()) {
      String keyString = setting.getKey();
      Settings.Key key = Settings.Key.of(keyString).orElse(null);

      if (key != null) {
        Object defaultValue = setting.getDefault(emptySettings);
        defaults.put(key, defaultValue);
      }
    }

    return defaults;
  }

  /**
   * Read settings from the OpenSearch SQL CLI configuration file
   *
   * @return Map of settings
   */
  private static Map<Settings.Key, Object> readSettingsFromConfig() {
    // Get default settings by extracting them from OpenSearchSettings constants
    Map<Settings.Key, Object> defaultSettings = getDefaultSettingsFromPlugin();

    try {
      loadCliYamlConfig();
      Map<Settings.Key, Object> settings = new HashMap<>(defaultSettings);

      try {
        // Dynamically read all settings from YAML config
        for (Map.Entry<Settings.Key, Object> entry : defaultSettings.entrySet()) {
          Settings.Key key = entry.getKey();
          Object defaultValue = entry.getValue();
          String yamlKey = "SqlSettings." + key.name();

          if (yamlConfig.containsKey(yamlKey)) {
            Object value = parseYamlValue(yamlKey, defaultValue);
            if (value != null) {
              settings.put(key, value);
            }
          }
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

  /**
   * Parse a value from YAML config based on the type of the default value
   *
   * @param yamlKey The key in the YAML config
   * @param defaultValue The default value to determine the type
   * @return The parsed value, or null if parsing fails
   */
  private static Object parseYamlValue(String yamlKey, Object defaultValue) {
    try {
      if (defaultValue instanceof Integer) {
        return yamlConfig.getInt(yamlKey);
      } else if (defaultValue instanceof Boolean) {
        return yamlConfig.getBoolean(yamlKey);
      } else if (defaultValue instanceof Double) {
        return yamlConfig.getDouble(yamlKey);
      } else if (defaultValue instanceof Long) {
        return yamlConfig.getLong(yamlKey);
      } else if (defaultValue instanceof String) {
        return yamlConfig.getString(yamlKey);
      } else if (defaultValue instanceof TimeValue) {
        // Special handling for TimeValue - assume YAML stores minutes as int
        int minutes = yamlConfig.getInt(yamlKey);
        return TimeValue.timeValueMinutes(minutes);
      } else if (defaultValue instanceof List) {
        // Handle list types
        return yamlConfig.getList(yamlKey);
      } else {
        logger.warn("Unknown setting type for key {}: {}", yamlKey, defaultValue.getClass());
        return null;
      }
    } catch (Exception e) {
      logger.error("Error parsing value for key {}: {}", yamlKey, e.getMessage());
      return null;
    }
  }

  /** Load the YAML configuration from file */
  private static void loadCliYamlConfig() {
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
