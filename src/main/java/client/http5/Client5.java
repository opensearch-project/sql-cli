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
public class Client5 {
  private static final Logger logger = LoggerFactory.getLogger("Client5");

  public static OpenSearchClient createAwsClient(String awsEndpoint) {
    try {
      // Determine the service name based on the endpoint URL
      String serviceName;
      if (awsEndpoint.contains("aos")) {
        serviceName = "aoss"; // Amazon OpenSearch Serverless
        logger.info("Using service name 'aoss' for OpenSearch Serverless");
      } else if (awsEndpoint.contains("es")) {
        serviceName = "es"; // Amazon OpenSearch Service
        logger.info("Using service name 'es' for OpenSearch Service");
      } else {
        logger.error("Cannot determine service type");
        throw new RuntimeException("Cannot determine service type");
      }

      // Create the DefaultCredentialsProvider that will read from ~/.aws/credentials
      AwsCredentialsProvider credentialsProvider = DefaultCredentialsProvider.builder().build();
      AwsCredentials credentials = credentialsProvider.resolveCredentials();
      logger.info("Access Key ID: " + credentials.accessKeyId());

      // read from ~/.aws/config
      Region region = new DefaultAwsRegionProviderChain().getRegion();
      logger.info("Using AWS region: " + region);

      HttpHost host = new HttpHost("https", awsEndpoint, 443);

      // Create the AWS SigV4 interceptor
      HttpRequestInterceptor interceptor =
          new AwsRequestSigningApacheV5Interceptor(
              serviceName, AwsV4HttpSigner.create(), credentialsProvider, region);

      // Add URI modification and logging interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(host)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder
                        .addRequestInterceptorFirst(newShowURI)
                        .addRequestInterceptorLast(interceptor)
                        .addRequestInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create AWS OpenSearchClient", e);
    }
  }

  public static OpenSearchClient createHttpsClient(
      String host, int port, String username, String password, boolean ignoreSSL) {
    try {
      final HttpHost httpHost = new HttpHost("https", host, port);

      // Set up credentials
      final BasicCredentialsProvider credentialsProvider = new BasicCredentialsProvider();
      if (username != null && password != null) {
        credentialsProvider.setCredentials(
            new AuthScope(httpHost),
            new UsernamePasswordCredentials(username, password.toCharArray()));
      }

      // Set up SSL context
      final SSLContext sslContext =
          SSLContextBuilder.create()
              // Trust certificates based on ignoreSSL flag
              .loadTrustMaterial(null, (chains, authType) -> ignoreSSL)
              .build();

      // Create interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Create a factory for TLS details
      Factory<SSLEngine, TlsDetails> tlsDetailsFactory =
          new Factory<SSLEngine, TlsDetails>() {
            @Override
            public TlsDetails create(final SSLEngine sslEngine) {
              return new TlsDetails(sslEngine.getSession(), sslEngine.getApplicationProtocol());
            }
          };

      // Build the TLS strategy using SSL context and factory
      final TlsStrategy tlsStrategy =
          ClientTlsStrategyBuilder.create()
              .setSslContext(sslContext)
              .setTlsDetailsFactory(tlsDetailsFactory)
              .build();

      // Create a connection manager with TLS strategy
      final PoolingAsyncClientConnectionManager connectionManager =
          PoolingAsyncClientConnectionManagerBuilder.create().setTlsStrategy(tlsStrategy).build();

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(httpHost)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder
                        .setDefaultCredentialsProvider(credentialsProvider)
                        .setConnectionManager(connectionManager)
                        .addRequestInterceptorFirst(newShowURI)
                        .addRequestInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      final RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);

      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create HTTPS OpenSearchClient", e);
    }
  }

  public static OpenSearchClient createHttpClient(String host, int port) {
    try {
      final HttpHost httpHost = new HttpHost("http", host, port);

      // Create interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(false);

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(httpHost)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder
                        .addRequestInterceptorFirst(newShowURI)
                        .addRequestInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);

      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create HTTP OpenSearchClient", e);
    }
  }

  /**
   * Creates a URI modification interceptor for SHOW command Original URI:
   * /?ignore_throttled=false&ignore_unavailable=false&expand_wildcards=open%2Cclosed&allow_no_indices=false&cluster_manager_timeout=30s
   * Because Error: OpenSearchStatusException[OpenSearch exception [type=illegal_argument_exception,
   * reason=request [/] contains unrecognized parameters: [allow_no_indices],
   * [cluster_manager_timeout], [expand_wildcards], [ignore_throttled], [ignore_unavailable]]]
   * Modified URI:: /*?
   */
  private static HttpRequestInterceptor createNewShowURI() {
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context) {
        try {
          // Get the original URI
          String originalUri = request.getRequestUri();
          logger.info("Original URI: " + originalUri);

          // Check if this is the exact URI
          String wrongShowUri =
              "/?ignore_throttled=false&ignore_unavailable=false&expand_wildcards=open%2Cclosed&allow_no_indices=false&cluster_manager_timeout=30s";
          if (originalUri.equals(wrongShowUri)) {
            // Replace URI to just /*?
            request.setPath("/*?");
            logger.info("Modified Show URI: " + request.getRequestUri());
          }
        } catch (Exception e) {
          logger.error("Error modifying URI: " + e.getMessage());
        }
      }
    };
  }

  private static HttpRequestInterceptor createLoggingInterceptor(boolean isHttps) {
    final String protocol = isHttps ? "HTTPS" : "HTTP";
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context) {
        logger.info("===== " + protocol + " REQUEST =====");
        logger.info("Method: " + request.getMethod());
        logger.info("URI: " + request.getRequestUri());
        logger.info("Request Type: " + request.getClass().getSimpleName());

        // Log headers
        logger.info("Headers:");
        request
            .headerIterator()
            .forEachRemaining(header -> logger.info(header.getName() + ": " + header.getValue()));
      }
    };
  }
}
