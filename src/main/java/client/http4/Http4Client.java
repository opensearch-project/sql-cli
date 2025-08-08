/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client.http4;

import io.github.acm19.aws.interceptor.http.AwsRequestSigningApacheInterceptor;
import javax.net.ssl.SSLContext;
import org.apache.http.Header;
import org.apache.http.HttpHost;
import org.apache.http.HttpRequest;
import org.apache.http.HttpRequestInterceptor;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.conn.ssl.TrustStrategy;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.impl.nio.client.HttpAsyncClientBuilder;
import org.apache.http.protocol.HttpContext;
import org.apache.http.ssl.SSLContexts;
import org.opensearch.client.RestClient;
import org.opensearch.client.RestClientBuilder;
import org.opensearch.client.RestHighLevelClient;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.opensearch.sql.opensearch.client.OpenSearchRestClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.auth.credentials.AwsCredentials;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.http.auth.aws.signer.AwsV4HttpSigner;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;

/**
 * Client class for creating OpenSearch clients with different authentication methods using HTTP4
 * for OpenSearch SQL plug-in version 2
 */
public class Http4Client {
  private static final Logger logger = LoggerFactory.getLogger("Http4Client");

  private static final String SERVERLESS = "aos";
  private static final String SERVICE = "es";
  private static final String SERVERLESS_NAME = "aoss";
  private static final String SERVICE_NAME = "es";

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

      HttpHost host = new HttpHost(awsEndpoint, 443, "https");
      HttpRequestInterceptor awsInterceptor =
          createAwsSigningInterceptor(serviceName, credentialsProvider, region);

      RestClientBuilder restClientBuilder =
          RestClient.builder(host)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> configureAwsHttpClient(httpClientBuilder, awsInterceptor));

      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClient(restHighLevelClient);
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
      HttpHost httpHost = new HttpHost(host, port, useHttps ? "https" : "http");

      RestClientBuilder restClientBuilder = RestClient.builder(httpHost);

      if (useHttps) {
        // HTTPS configuration
        CredentialsProvider credentialsProvider =
            createBasicCredentialsProvider(httpHost, username, password);
        SSLContext sslContext = createSSLContext(ignoreSSL);

        restClientBuilder.setHttpClientConfigCallback(
            httpClientBuilder ->
                configureHttpsClient(httpClientBuilder, credentialsProvider, sslContext));
      } else {
        // HTTP configuration
        restClientBuilder.setHttpClientConfigCallback(
            httpClientBuilder -> configureHttpClient(httpClientBuilder));
      }

      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClient(restHighLevelClient);
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
    return new AwsRequestSigningApacheInterceptor(
        serviceName, AwsV4HttpSigner.create(), credentialsProvider, region);
  }

  /** Creates basic credentials provider for HTTPS authentication. */
  private static CredentialsProvider createBasicCredentialsProvider(
      HttpHost httpHost, String username, String password) {
    CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
    if (username != null && password != null) {
      credentialsProvider.setCredentials(
          new AuthScope(httpHost), new UsernamePasswordCredentials(username, password));
    }
    return credentialsProvider;
  }

  /** Creates SSL context with optional certificate validation bypass. */
  private static SSLContext createSSLContext(boolean ignoreSSL) throws Exception {
    TrustStrategy trustStrategy = (chains, authType) -> ignoreSSL;
    return SSLContexts.custom().loadTrustMaterial(null, trustStrategy).build();
  }

  /** Configures HTTP client for AWS authentication. */
  private static HttpAsyncClientBuilder configureAwsHttpClient(
      HttpAsyncClientBuilder httpClientBuilder, HttpRequestInterceptor awsInterceptor) {
    return httpClientBuilder
        .addInterceptorLast(awsInterceptor)
        .addInterceptorLast(createLoggingInterceptor(true));
  }

  /** Configures HTTP client for HTTPS with basic authentication. */
  private static HttpAsyncClientBuilder configureHttpsClient(
      HttpAsyncClientBuilder httpClientBuilder,
      CredentialsProvider credentialsProvider,
      SSLContext sslContext) {
    return httpClientBuilder
        .setDefaultCredentialsProvider(credentialsProvider)
        .setSSLContext(sslContext)
        .addInterceptorLast(createLoggingInterceptor(true));
  }

  /** Configures HTTP client for plain HTTP. */
  private static HttpAsyncClientBuilder configureHttpClient(
      HttpAsyncClientBuilder httpClientBuilder) {
    return httpClientBuilder.addInterceptorLast(createLoggingInterceptor(false));
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
      public void process(HttpRequest request, HttpContext context) {
        logger.info("===== {} REQUEST =====", protocol);
        logger.info("Method: {}", request.getRequestLine().getMethod());
        logger.info("URI: {}", request.getRequestLine().getUri());
        logger.info("Request Type: {}", request.getClass().getSimpleName());

        // Log headers
        logger.info("Headers:");
        for (Header header : request.getAllHeaders()) {
          logger.info("{}: {}", header.getName(), header.getValue());
        }
      }
    };
  }
}
