/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import com.google.inject.Guice;
import com.google.inject.Injector;
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.sql.SQLService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import py4j.GatewayServer;
import query.QueryExecution;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;

public class Gateway {
  private static final Logger logger = LoggerFactory.getLogger("Gateway");

  private PPLService pplService;
  private SQLService sqlService;
  private QueryExecution queryExecution;

  public boolean initializeAwsConnection(String hostPort, boolean useHttp5) {
    // hostPort is the AWS OpenSearch endpoint (without https://)
    Region region = new DefaultAwsRegionProviderChain().getRegion();

    try {

      Injector injector = Guice.createInjector(new GatewayModule(hostPort, useHttp5));

      // Initialize services
      this.pplService = injector.getInstance(PPLService.class);
      this.sqlService = injector.getInstance(SQLService.class);
      this.queryExecution = injector.getInstance(QueryExecution.class);

      logger.info("Initialized AWS connection to OpenSearch at {} in region {}.", hostPort, region);
      logger.info("Using HTTP{} for the connection.", (useHttp5 ? "5" : "4"));

      return true;

    } catch (Exception e) {
      logger.error("Failed to initialize AWS connection", e);
      return false;
    }
  }

  public boolean initializeConnection(
      String host,
      int port,
      String protocol,
      String username,
      String password,
      boolean ignoreSSL,
      boolean useHttp5) {

    try {

      Injector injector =
          Guice.createInjector(
              new GatewayModule(host, port, protocol, username, password, ignoreSSL, useHttp5));

      // Initialize services
      this.pplService = injector.getInstance(PPLService.class);
      this.sqlService = injector.getInstance(SQLService.class);
      this.queryExecution = injector.getInstance(QueryExecution.class);

      logger.info("Initialized connection to OpenSearch at {}://{}:{}.", protocol, host, port);
      logger.info("Using HTTP{} for the connection.", (useHttp5 ? "5" : "4"));

      return true;

    } catch (Exception e) {
      logger.error("Failed to initialize connection", e);
      return false;
    }
  }

  public String queryExecution(String query, boolean isPPL, String format) {
    // Use the QueryExecution class to execute the query
    return queryExecution.execute(query, isPPL, format);
  }

  public static void main(String[] args) {
    try {
      Gateway app = new Gateway();

      // default port 25333
      int gatewayPort = 25333;
      GatewayServer server = new GatewayServer(app, gatewayPort);

      server.start();
      logger.info("Gateway Server Started on port {}", gatewayPort);

    } catch (Exception e) {
      logger.error("Failed to start Gateway Server", e);
    }
  }
}
