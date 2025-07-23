/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client;

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
import software.amazon.awssdk.auth.credentials.AwsCredentials;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.http.auth.aws.signer.AwsV4HttpSigner;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;

/** Client class for creating OpenSearch clients with different authentication methods. */
public class Client {

  public static OpenSearchClient createAwsClient(String awsEndpoint) {
    try {
      // Determine the service name based on the endpoint URL
      String serviceName;
      if (awsEndpoint.contains("aos")) {
        serviceName = "aoss"; // Amazon OpenSearch Serverless
        System.out.println("Using service name 'aoss' for OpenSearch Serverless");
      } else if (awsEndpoint.contains("es")) {
        serviceName = "es"; // Amazon OpenSearch Service
        System.out.println("Using service name 'es' for OpenSearch Service");
      } else {
        System.err.println("ERROR - Cannot determine service type");
        throw new RuntimeException("ERROR - Cannot determine service type");
      }

      // Create the DefaultCredentialsProvider that will read from ~/.aws/credentials
      AwsCredentialsProvider credentialsProvider = DefaultCredentialsProvider.builder().build();
      AwsCredentials credentials = credentialsProvider.resolveCredentials();
      System.out.println("Access Key ID: " + credentials.accessKeyId());

      // read from ~/.aws/config
      Region region = new DefaultAwsRegionProviderChain().getRegion();
      System.out.println("Using AWS region: " + region);

      HttpHost host = new HttpHost("https", awsEndpoint, 443);

      // Create a custom interceptor to handle request signing
      HttpRequestInterceptor interceptor =
          new HttpRequestInterceptor() {
            @Override
            public void process(HttpRequest request, EntityDetails entity, HttpContext context) {
              // Create and apply the AWS SigV4 interceptor
              try {
                client.aws.AwsRequestSigningApacheV5Interceptor awsInterceptor =
                    new client.aws.AwsRequestSigningApacheV5Interceptor(
                        serviceName, AwsV4HttpSigner.create(), credentialsProvider, region);
                awsInterceptor.process(request, entity, context);

              } catch (Exception e) {
                System.err.println("Error in AWS request signing: " + e.getMessage());
                e.printStackTrace();
              }
            }
          };

      // Add our URI modification and logging interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Build RestClientBuilder with interceptors
      RestClientBuilder restClientBuilder =
          RestClient.builder(host)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    httpClientBuilder.addRequestInterceptorFirst(newShowURI);
                    httpClientBuilder.addRequestInterceptorLast(interceptor);
                    httpClientBuilder.addRequestInterceptorLast(loggingInterceptor);
                    return httpClientBuilder;
                  });

      // Use the builder for the high-level client
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

      // For HTTPS: Set up credentials and SSL
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

      // Create our interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Create RestHighLevelClient with SSL and authentication
      final RestHighLevelClient restHighLevelClient =
          new RestHighLevelClient(
              RestClient.builder(httpHost)
                  .setHttpClientConfigCallback(
                      httpClientBuilder -> {
                        // Set up TLS strategy
                        final TlsStrategy tlsStrategy =
                            ClientTlsStrategyBuilder.create()
                                .setSslContext(sslContext)
                                .setTlsDetailsFactory(
                                    new Factory<SSLEngine, TlsDetails>() {
                                      @Override
                                      public TlsDetails create(final SSLEngine sslEngine) {
                                        return new TlsDetails(
                                            sslEngine.getSession(),
                                            sslEngine.getApplicationProtocol());
                                      }
                                    })
                                .build();

                        // Set up connection manager
                        final PoolingAsyncClientConnectionManager connectionManager =
                            PoolingAsyncClientConnectionManagerBuilder.create()
                                .setTlsStrategy(tlsStrategy)
                                .build();

                        return httpClientBuilder
                            .setDefaultCredentialsProvider(credentialsProvider)
                            .setConnectionManager(connectionManager)
                            .addRequestInterceptorFirst(newShowURI)
                            .addRequestInterceptorLast(loggingInterceptor);
                      }));

      return new OpenSearchRestClientImpl(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create HTTPS OpenSearchClient", e);
    }
  }

  public static OpenSearchClient createHttpClient(String host, int port) {
    try {
      final HttpHost httpHost = new HttpHost("http", host, port);

      // Create our interceptors
      HttpRequestInterceptor newShowURI = createNewShowURI();
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(false);

      RestHighLevelClient restHighLevelClient =
          new RestHighLevelClient(
              RestClient.builder(httpHost)
                  .setHttpClientConfigCallback(
                      httpClientBuilder -> {
                        return httpClientBuilder
                            .addRequestInterceptorFirst(newShowURI)
                            .addRequestInterceptorLast(loggingInterceptor);
                      }));

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
          System.out.println("Original URI: " + originalUri);

          // Check if this is the exact URI
          String wrongShowUri =
              "/?ignore_throttled=false&ignore_unavailable=false&expand_wildcards=open%2Cclosed&allow_no_indices=false&cluster_manager_timeout=30s";
          if (originalUri.equals(wrongShowUri)) {
            // Replace URI to just /*?
            request.setPath("/*?");
            System.out.println("Modified Show URI: " + request.getRequestUri());
          }
        } catch (Exception e) {
          System.err.println("Error modifying URI: " + e.getMessage());
          e.printStackTrace();
        }
      }
    };
  }

  private static HttpRequestInterceptor createLoggingInterceptor(boolean isHttps) {
    final String protocol = isHttps ? "HTTPS" : "HTTP";
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context) {
        System.out.println("===== " + protocol + " REQUEST =====");
        System.out.println("Method: " + request.getMethod());
        System.out.println("URI: " + request.getRequestUri());
        System.out.println("Request Type: " + request.getClass().getSimpleName());

        // Log headers
        System.out.println("Headers:");
        request
            .headerIterator()
            .forEachRemaining(
                header -> System.out.println("  " + header.getName() + ": " + header.getValue()));

        if (entityDetails != null) {
          System.out.println("Content Type: " + entityDetails.getContentType());
          System.out.println("Content Length: " + entityDetails.getContentLength());
        }
        System.out.println("=====================");
      }
    };
  }
}
