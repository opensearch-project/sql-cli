/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import client.Client;
import com.google.inject.AbstractModule;
import com.google.inject.Provides;
import com.google.inject.name.Named;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.opensearch.sql.analysis.Analyzer;
import org.opensearch.sql.analysis.ExpressionAnalyzer;
import org.opensearch.sql.common.setting.Settings;
import org.opensearch.sql.datasource.DataSourceService;
import org.opensearch.sql.datasource.model.DataSourceMetadata;
import org.opensearch.sql.datasources.auth.DataSourceUserAuthorizationHelper;
import org.opensearch.sql.datasources.service.DataSourceMetadataStorage;
import org.opensearch.sql.datasources.service.DataSourceServiceImpl;
import org.opensearch.sql.executor.ExecutionEngine;
import org.opensearch.sql.executor.QueryManager;
import org.opensearch.sql.executor.QueryService;
import org.opensearch.sql.executor.execution.QueryPlanFactory;
import org.opensearch.sql.executor.pagination.PlanSerializer;
import org.opensearch.sql.expression.function.BuiltinFunctionRepository;
import org.opensearch.sql.monitor.AlwaysHealthyMonitor;
import org.opensearch.sql.monitor.ResourceMonitor;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.opensearch.sql.opensearch.executor.OpenSearchExecutionEngine;
import org.opensearch.sql.opensearch.executor.protector.ExecutionProtector;
import org.opensearch.sql.opensearch.executor.protector.OpenSearchExecutionProtector;
import org.opensearch.sql.opensearch.storage.OpenSearchDataSourceFactory;
import org.opensearch.sql.opensearch.storage.OpenSearchStorageEngine;
import org.opensearch.sql.planner.Planner;
import org.opensearch.sql.planner.optimizer.LogicalPlanOptimizer;
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.ppl.antlr.PPLSyntaxParser;
import org.opensearch.sql.protocol.response.QueryResult;
import org.opensearch.sql.protocol.response.format.CsvResponseFormatter;
import org.opensearch.sql.protocol.response.format.JdbcResponseFormatter;
import org.opensearch.sql.protocol.response.format.JsonResponseFormatter;
import org.opensearch.sql.protocol.response.format.RawResponseFormatter;
import org.opensearch.sql.protocol.response.format.ResponseFormatter;
import org.opensearch.sql.protocol.response.format.SimpleJsonResponseFormatter;
import org.opensearch.sql.sql.SQLService;
import org.opensearch.sql.sql.antlr.SQLSyntaxParser;
import org.opensearch.sql.storage.DataSourceFactory;
import org.opensearch.sql.storage.StorageEngine;
import query.CustomQueryManager;
import query.QueryExecution;

public class GatewayModule extends AbstractModule {
  private final String host;
  private final int port;
  private final String protocol;
  private final String username;
  private final String password;
  private final boolean ignoreSSL;
  private final boolean useAwsAuth;
  private final String awsEndpoint;
  private final String awsRegion;

  public GatewayModule(
      String host, int port, String protocol, String username, String password, boolean ignoreSSL) {
    this.host = host;
    this.port = port;
    this.protocol = protocol;
    this.username = username;
    this.password = password;
    this.ignoreSSL = ignoreSSL;
    this.useAwsAuth = false;
    this.awsEndpoint = null;
    this.awsRegion = null;
  }

  public GatewayModule(String awsEndpoint) {
    this.host = null;
    this.port = 0;
    this.protocol = null;
    this.username = null;
    this.password = null;
    this.ignoreSSL = false;
    this.useAwsAuth = true;
    this.awsEndpoint = awsEndpoint;
    this.awsRegion = null;
  }

  @Override
  protected void configure() {}

  @Provides
  public OpenSearchClient openSearchClient() {
    try {
      if (useAwsAuth) {
        // Use AWS authentication
        return Client.createAwsClient(awsEndpoint);
      } else if (protocol.equalsIgnoreCase("https")) {
        // Use HTTPS authentication
        return Client.createHttpsClient(host, port, username, password, ignoreSSL);
      } else {
        // Use HTTP authentication
        return Client.createHttpClient(host, port);
      }
    } catch (Exception e) {
      throw new RuntimeException("Failed to create OpenSearchClient", e);
    }
  }

  @Provides
  QueryManager queryManager(OpenSearchClient openSearchClient) {
    return new CustomQueryManager(openSearchClient);
  }

  @Provides
  BuiltinFunctionRepository functionRepository() {
    return BuiltinFunctionRepository.getInstance();
  }

  @Provides
  ExpressionAnalyzer expressionAnalyzer(BuiltinFunctionRepository functionRepository) {
    return new ExpressionAnalyzer(functionRepository);
  }

  @Provides
  Settings settings() {
    // Get settings from the configuration file: main/config/config_file
    return Config.getSettings();
  }

  @Provides
  OpenSearchDataSourceFactory openSearchDataSourceFactory(
      OpenSearchClient client, Settings settings) {
    return new OpenSearchDataSourceFactory(client, settings);
  }

  @Provides
  Set<DataSourceFactory> dataSourceFactories(OpenSearchDataSourceFactory factory) {
    return Set.of(factory);
  }

  @Provides
  public DataSourceMetadataStorage dataSourceMetadataStorage() {
    return new DataSourceMetadataStorage() {
      @Override
      public List<DataSourceMetadata> getDataSourceMetadata() {
        return Collections.emptyList();
      }

      @Override
      public Optional<DataSourceMetadata> getDataSourceMetadata(String datasourceName) {
        return Optional.empty();
      }

      @Override
      public void createDataSourceMetadata(DataSourceMetadata dataSourceMetadata) {}

      @Override
      public void updateDataSourceMetadata(DataSourceMetadata dataSourceMetadata) {}

      @Override
      public void deleteDataSourceMetadata(String datasourceName) {}
    };
  }

  @Provides
  public DataSourceUserAuthorizationHelper getDataSourceUserRoleHelper() {
    return new DataSourceUserAuthorizationHelper() {
      @Override
      public void authorizeDataSource(DataSourceMetadata dataSourceMetadata) {}
    };
  }

  @Provides
  DataSourceService dataSourceService(
      Set<DataSourceFactory> factories,
      DataSourceMetadataStorage metadataStorage,
      DataSourceUserAuthorizationHelper authorizationHelper) {
    return new DataSourceServiceImpl(factories, metadataStorage, authorizationHelper);
  }

  @Provides
  Analyzer analyzer(
      ExpressionAnalyzer expressionAnalyzer,
      DataSourceService dataSourceService,
      BuiltinFunctionRepository functionRepository) {
    return new Analyzer(expressionAnalyzer, dataSourceService, functionRepository);
  }

  @Provides
  ResourceMonitor resourceMonitor() {
    return new AlwaysHealthyMonitor();
  }

  @Provides
  ExecutionProtector executionProtector(ResourceMonitor resourceMonitor) {
    return new OpenSearchExecutionProtector(resourceMonitor);
  }

  @Provides
  StorageEngine storageEngine(OpenSearchClient client, Settings settings) {
    return new OpenSearchStorageEngine(client, settings);
  }

  @Provides
  PlanSerializer planSerializer(StorageEngine storageEngine) {
    return new PlanSerializer(storageEngine);
  }

  @Provides
  ExecutionEngine executionEngine(
      OpenSearchClient client, ExecutionProtector protector, PlanSerializer planSerializer) {
    return new OpenSearchExecutionEngine(client, protector, planSerializer);
  }

  @Provides
  Planner planner() {
    return new Planner(LogicalPlanOptimizer.create());
  }

  @Provides
  QueryService queryService(
      Analyzer analyzer,
      ExecutionEngine executionEngine,
      Planner planner,
      DataSourceService dataSourceService,
      Settings settings) {
    return new QueryService(analyzer, executionEngine, planner, dataSourceService, settings);
  }

  @Provides
  QueryPlanFactory queryPlanFactory(QueryService queryService) {
    return new QueryPlanFactory(queryService);
  }

  @Provides
  PPLService pplService(
      PPLSyntaxParser pplSyntaxParser,
      QueryManager queryManager,
      QueryPlanFactory queryPlanFactory,
      Settings settings) {
    return new PPLService(new PPLSyntaxParser(), queryManager, queryPlanFactory, settings);
  }

  @Provides
  SQLService sqlService(
      SQLSyntaxParser sqlSyntaxParser,
      QueryManager queryManager,
      QueryPlanFactory queryPlanFactory) {
    return new SQLService(new SQLSyntaxParser(), queryManager, queryPlanFactory);
  }

  @Provides
  QueryExecution queryExecution(PPLService pplService, SQLService sqlService) {
    return new QueryExecution(pplService, sqlService);
  }

  @Provides
  public CsvResponseFormatter csvResponseFormatter() {
    return new CsvResponseFormatter();
  }

  @Provides
  @Named("pretty")
  public SimpleJsonResponseFormatter jsonResponseFormatter() {
    return new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.PRETTY);
  }

  @Provides
  @Named("compact")
  public SimpleJsonResponseFormatter compactJsonResponseFormatter() {
    return new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.COMPACT);
  }

  @Provides
  public JdbcResponseFormatter jdbcResponseFormatter() {
    return new JdbcResponseFormatter(JsonResponseFormatter.Style.PRETTY);
  }

  @Provides
  public RawResponseFormatter rawResponseFormatter() {
    return new RawResponseFormatter();
  }

  @Provides
  public ResponseFormatter<QueryResult> getFormatter(
      String formatName,
      @Named("pretty") SimpleJsonResponseFormatter prettyFormatter,
      @Named("compact") SimpleJsonResponseFormatter compactFormatter,
      CsvResponseFormatter csvFormatter,
      JdbcResponseFormatter jdbcFormatter,
      RawResponseFormatter rawFormatter) {
    if (formatName == null || formatName.isEmpty()) {
      // Default to JSON
      return prettyFormatter;
    }

    switch (formatName.toLowerCase()) {
      case "csv":
        return csvFormatter;
      case "json":
        return prettyFormatter;
      case "compact_json":
        return compactFormatter;
      case "jdbc":
        return jdbcFormatter;
      case "raw":
        return rawFormatter;
      case "table":
        return jdbcFormatter;
      default:
        return prettyFormatter;
    }
  }
}
