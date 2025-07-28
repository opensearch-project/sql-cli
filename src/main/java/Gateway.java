/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import com.google.inject.Guice;
import com.google.inject.Injector;
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.sql.SQLService;
import py4j.GatewayServer;
import query.QueryExecution;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;

public class Gateway {

  private PPLService pplService;
  private SQLService sqlService;
  private QueryExecution queryExecution;

  public Gateway() {
    // Empty constructor - services will be initialized when OpenSearch CLI connects
  }

  public synchronized boolean initializeAwsConnection(String hostPort, boolean useHttp5) {
    // hostPort is the AWS OpenSearch endpoint (without https://)
    Region region = new DefaultAwsRegionProviderChain().getRegion();

    try {

      Injector injector = Guice.createInjector(new GatewayModule(hostPort, useHttp5));

      // Initialize services
      this.pplService = injector.getInstance(PPLService.class);
      this.sqlService = injector.getInstance(SQLService.class);
      this.queryExecution = injector.getInstance(QueryExecution.class);

      System.out.println(
          "Initialized AWS connection to OpenSearch at " + hostPort + " in region " + region + ".");
      System.out.println("Using HTTP" + (useHttp5 ? "5" : "4") + " for the connection.");

      return true;

    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  public synchronized boolean initializeConnection(
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

      System.out.println(
          "Initialized connection to OpenSearch at " + protocol + "://" + host + ":" + port + ".");
      System.out.println("Using HTTP" + (useHttp5 ? "5" : "4") + " for the connection.");

      return true;

    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  public String queryExecution(String query, boolean isPPL, String format) {
    // Use the QueryExecution class to execute the query
    return queryExecution.execute(query, isPPL, format);
  }

  public static void main(String[] args) {
    try {
      System.out.println("Starting Gateway Server...");

      Gateway app = new Gateway();

      // default port 25333
      int gatewayPort = 25333;
      GatewayServer server = new GatewayServer(app, gatewayPort);

      server.start();
      System.out.println("Gateway Server Started on port " + gatewayPort);
    } catch (Exception e) {
      e.printStackTrace();
    }
  }
}
