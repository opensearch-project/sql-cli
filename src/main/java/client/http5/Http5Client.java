/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client.http5;

import client.http5.aws.AwsRequestSigningApacheV5Interceptor;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import org.apache.hc.client5.http.auth.AuthScope;
import org.apache.hc.client5.http.auth.UsernamePasswordCredentials;
import org.apache.hc.client5.http.impl.async.HttpAsyncClientBuilder;
import org.apache.hc.client5.http.impl.auth.BasicCredentialsProvider;
import org.apache.hc.client5.http.impl.nio.PoolingAsyncClientConnectionManager;
import org.apache.hc.client5.http.impl.nio.PoolingAsyncClientConnectionManagerBuilder;
import org.apache.hc.client5.http.ssl.ClientTlsStrategyBuilder;
import org.apache.hc.core5.function.Factory;
import org.apache.hc.core5.http.EntityDetails;
import org.apache.hc.core5.http.HttpHost;
import org.apache.hc.core5.http.HttpRequest;
import org.apache.hc.core5.http.HttpRequestInterceptor;
import org.apache.hc.core5.http.nio.ssl.TlsStrategy;
import org.apache.hc.core5.http.protocol.HttpContext;
import org.apache.hc.core5.reactor.ssl.TlsDetails;
import org.apache.hc.core5.ssl.SSLContextBuilder;
import org.opensearch.client.RestClient;
import org.opensearch.client.RestClientBuilder;
import org.opensearch.client.RestHighLevelClient;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.auth.credentials.AwsCredentials;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.http.auth.aws.signer.AwsV4HttpSigner;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;

/**
 * Client class for creating OpenSearch clients with different authentication methods using HTTP5
 * for OpenSearch SQL plug-in version 3
 */
public class Http5Client {
  private static final Logger logger = LoggerFactory.getLogger("Http5Client");

  private static final String SERVERLESS = "aos";
  private static final String SERVICE = "es";
  private static final String SERVERLESS_NAME = "aoss";
  private static final String SERVICE_NAME = "es";

  private static final String PROBLEMATIC_SHOW_URI =
      "/?ignore_throttled=false&ignore_unavailable=false&expand_wildcards=open%2Cclosed&allow_no_indices=false&cluster_manager_timeout=30s";
  private static final String CORRECTED_SHOW_URI = "/*?";

  /**
   * Creates an OpenSearch client with AWS authentication (SigV4).
   *
   * @param awsEndpoint The AWS OpenSearch endpoint URL
   * @return Configured OpenSearchClient with AWS authentication
   * @throws RuntimeException if client creation fails
   */
  public static OpenSearchClient createAwsClient(String awsEndpoint) {
    try {
      String serviceName = determineServiceName(awsEndpoint);
      AwsCredentialsProvider credentialsProvider = createAwsCredentialsProvider();
      Region region = getAwsRegion();

      HttpHost host = new HttpHost("https", awsEndpoint, 443);
      HttpRequestInterceptor awsInterceptor =
          createAwsSigningInterceptor(serviceName, credentialsProvider, region);

      RestClientBuilder restClientBuilder =
          RestClient.builder(host)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> configureAwsHttpClient(httpClientBuilder, awsInterceptor));

      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create AWS OpenSearchClient", e);
    }
  }

  /**
   * Creates an OpenSearch client with HTTP or HTTPS and optional basic authentication.
   *
   * @param host The hostname
   * @param port The port number
   * @param protocol The protocol ("http" or "https")
   * @param username The username for basic auth (can be null)
   * @param password The password for basic auth (can be null)
   * @param ignoreSSL Whether to ignore SSL certificate validation (only applies to HTTPS)
   * @return Configured OpenSearchClient
   * @throws RuntimeException if client creation fails
   */
  public static OpenSearchClient createClient(
      String host, int port, String protocol, String username, String password, boolean ignoreSSL) {
    try {
      boolean useHttps = "https".equalsIgnoreCase(protocol);
      HttpHost httpHost = new HttpHost(useHttps ? "https" : "http", host, port);

      RestClientBuilder restClientBuilder = RestClient.builder(httpHost);

      if (useHttps) {
        // HTTPS configuration
        BasicCredentialsProvider credentialsProvider =
            createBasicCredentialsProvider(httpHost, username, password);
        SSLContext sslContext = createSSLContext(ignoreSSL);
        PoolingAsyncClientConnectionManager connectionManager = createConnectionManager(sslContext);

        restClientBuilder.setHttpClientConfigCallback(
            httpClientBuilder ->
                configureHttpsClient(httpClientBuilder, credentialsProvider, connectionManager));
      } else {
        // HTTP configuration
        restClientBuilder.setHttpClientConfigCallback(
            httpClientBuilder -> configureHttpClient(httpClientBuilder));
      }

      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create OpenSearchClient", e);
    }
  }

  /** Determines the AWS service name based on the endpoint URL. */
  private static String determineServiceName(String awsEndpoint) {
    if (awsEndpoint.contains(SERVERLESS)) {
      logger.info("Using service name '{}' for OpenSearch Serverless", SERVERLESS_NAME);
      return SERVERLESS_NAME;
    } else if (awsEndpoint.contains(SERVICE)) {
      logger.info("Using service name '{}' for OpenSearch Service", SERVICE_NAME);
      return SERVICE_NAME;
    } else {
      logger.error("Cannot determine service type from endpoint: {}", awsEndpoint);
      throw new RuntimeException("Cannot determine service type");
    }
  }

  /** Creates AWS credentials provider and logs access key ID. */
  private static AwsCredentialsProvider createAwsCredentialsProvider() {
    AwsCredentialsProvider credentialsProvider = DefaultCredentialsProvider.builder().build();
    AwsCredentials credentials = credentialsProvider.resolveCredentials();
    logger.info("Access Key ID: {}", credentials.accessKeyId());
    return credentialsProvider;
  }

  /** Gets AWS region from default provider chain. */
  private static Region getAwsRegion() {
    Region region = new DefaultAwsRegionProviderChain().getRegion();
    logger.info("Using AWS region: {}", region);
    return region;
  }

  /** Creates AWS signing interceptor. */
  private static HttpRequestInterceptor createAwsSigningInterceptor(
      String serviceName, AwsCredentialsProvider credentialsProvider, Region region) {
    return new AwsRequestSigningApacheV5Interceptor(
        serviceName, AwsV4HttpSigner.create(), credentialsProvider, region);
  }

  /** Creates basic credentials provider for HTTPS authentication. */
  private static BasicCredentialsProvider createBasicCredentialsProvider(
      HttpHost httpHost, String username, String password) {
    BasicCredentialsProvider credentialsProvider = new BasicCredentialsProvider();
    if (username != null && password != null) {
      credentialsProvider.setCredentials(
          new AuthScope(httpHost),
          new UsernamePasswordCredentials(username, password.toCharArray()));
    }
    return credentialsProvider;
  }

  /** Creates SSL context with optional certificate validation bypass. */
  private static SSLContext createSSLContext(boolean ignoreSSL) throws Exception {
    return SSLContextBuilder.create()
        .loadTrustMaterial(null, (chains, authType) -> ignoreSSL)
        .build();
  }

  /** Creates connection manager with TLS strategy. */
  private static PoolingAsyncClientConnectionManager createConnectionManager(
      SSLContext sslContext) {
    Factory<SSLEngine, TlsDetails> tlsDetailsFactory =
        sslEngine -> new TlsDetails(sslEngine.getSession(), sslEngine.getApplicationProtocol());

    TlsStrategy tlsStrategy =
        ClientTlsStrategyBuilder.create()
            .setSslContext(sslContext)
            .setTlsDetailsFactory(tlsDetailsFactory)
            .build();

    return PoolingAsyncClientConnectionManagerBuilder.create().setTlsStrategy(tlsStrategy).build();
  }

  /** Configures HTTP client for AWS authentication. */
  private static HttpAsyncClientBuilder configureAwsHttpClient(
      HttpAsyncClientBuilder httpClientBuilder, HttpRequestInterceptor awsInterceptor) {
    return httpClientBuilder
        .addRequestInterceptorFirst(createUriModificationInterceptor())
        .addRequestInterceptorLast(awsInterceptor)
        .addRequestInterceptorLast(createLoggingInterceptor(true));
  }

  /** Configures HTTP client for HTTPS with basic authentication. */
  private static HttpAsyncClientBuilder configureHttpsClient(
      HttpAsyncClientBuilder httpClientBuilder,
      BasicCredentialsProvider credentialsProvider,
      PoolingAsyncClientConnectionManager connectionManager) {
    return httpClientBuilder
        .setDefaultCredentialsProvider(credentialsProvider)
        .setConnectionManager(connectionManager)
        .addRequestInterceptorFirst(createUriModificationInterceptor())
        .addRequestInterceptorLast(createLoggingInterceptor(true));
  }

  /** Configures HTTP client for plain HTTP. */
  private static HttpAsyncClientBuilder configureHttpClient(
      HttpAsyncClientBuilder httpClientBuilder) {
    return httpClientBuilder
        .addRequestInterceptorFirst(createUriModificationInterceptor())
        .addRequestInterceptorLast(createLoggingInterceptor(false));
  }

  /**
   * Creates a URI modification interceptor for SHOW command.
   *
   * <p>Fixes the issue where certain query parameters are not recognized by OpenSearch. Original
   * problematic URI contains parameters like allow_no_indices, cluster_manager_timeout, etc. These
   * are replaced with a simplified URI pattern.
   */
  private static HttpRequestInterceptor createUriModificationInterceptor() {
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context) {
        try {
          String originalUri = request.getRequestUri();
          logger.info("Original URI: {}", originalUri);

          if (PROBLEMATIC_SHOW_URI.equals(originalUri)) {
            request.setPath(CORRECTED_SHOW_URI);
            logger.info("Modified Show URI: {}", request.getRequestUri());
          }
        } catch (Exception e) {
          logger.error("Error modifying URI: {}", e.getMessage());
        }
      }
    };
  }

  /**
   * Creates a logging interceptor for HTTP requests.
   *
   * @param isHttps Whether this is for HTTPS requests
   * @return Configured logging interceptor
   */
  private static HttpRequestInterceptor createLoggingInterceptor(boolean isHttps) {
    final String protocol = isHttps ? "HTTPS" : "HTTP";
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context) {
        logger.info("===== {} REQUEST =====", protocol);
        logger.info("Method: {}", request.getMethod());
        logger.info("URI: {}", request.getRequestUri());
        logger.info("Request Type: {}", request.getClass().getSimpleName());

        // Log headers
        logger.info("Headers:");
        request
            .headerIterator()
            .forEachRemaining(header -> logger.info("{}: {}", header.getName(), header.getValue()));
      }
    };
  }
}
