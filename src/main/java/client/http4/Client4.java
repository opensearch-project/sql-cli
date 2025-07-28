/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client.http4;

import io.github.acm19.aws.interceptor.http.AwsRequestSigningApacheInterceptor;
import javax.net.ssl.SSLContext;
import org.apache.http.Header;
import org.apache.http.HttpEntityEnclosingRequest;
import org.apache.http.HttpHost;
import org.apache.http.HttpRequest;
import org.apache.http.HttpRequestInterceptor;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.conn.ssl.TrustStrategy;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.protocol.HttpContext;
import org.apache.http.ssl.SSLContexts;
import org.opensearch.client.RestClient;
import org.opensearch.client.RestClientBuilder;
import org.opensearch.client.RestHighLevelClient;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.opensearch.sql.opensearch.client.OpenSearchRestClient;
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
public class Client4 {

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

      HttpHost host = new HttpHost(awsEndpoint, 443, "https");

      // Create a custom interceptor to handle request signing
      HttpRequestInterceptor interceptor =
          new HttpRequestInterceptor() {
            @Override
            public void process(HttpRequest request, HttpContext context) {
              // Create and apply the AWS SigV4 interceptor
              try {
                AwsRequestSigningApacheInterceptor awsInterceptor =
                    new AwsRequestSigningApacheInterceptor(
                        serviceName, AwsV4HttpSigner.create(), credentialsProvider, region);
                awsInterceptor.process(request, context);

              } catch (Exception e) {
                System.err.println("Error in AWS request signing: " + e.getMessage());
                e.printStackTrace();
              }
            }
          };

      // Add logging interceptor
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(host)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder
                        .addInterceptorLast(interceptor)
                        .addInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);
      return new OpenSearchRestClient(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create AWS OpenSearchClient", e);
    }
  }

  public static OpenSearchClient createHttpsClient(
      String host, int port, String username, String password, boolean ignoreSSL) {
    try {
      HttpHost httpHost = new HttpHost(host, port, "https");

      // Set up credentials
      final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
      if (username != null && password != null) {
        credentialsProvider.setCredentials(
            new AuthScope(httpHost), new UsernamePasswordCredentials(username, password));
      }

      // Set up SSL context
      final TrustStrategy trustStrategy = (chains, authType) -> ignoreSSL;
      final SSLContext sslContext =
          SSLContexts.custom().loadTrustMaterial(null, trustStrategy).build();

      // Create interceptors
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(true);

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(httpHost)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder
                        .setDefaultCredentialsProvider(credentialsProvider)
                        .setSSLContext(sslContext)
                        .addInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      final RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);

      return new OpenSearchRestClient(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create HTTPS OpenSearchClient", e);
    }
  }

  public static OpenSearchClient createHttpClient(String host, int port) {
    try {
      final HttpHost httpHost = new HttpHost(host, port, "http");

      // Create interceptors
      HttpRequestInterceptor loggingInterceptor = createLoggingInterceptor(false);

      // Create RestClientBuilder with configurations
      RestClientBuilder restClientBuilder =
          RestClient.builder(httpHost)
              .setHttpClientConfigCallback(
                  httpClientBuilder -> {
                    return httpClientBuilder.addInterceptorLast(loggingInterceptor);
                  });

      // Create RestHighLevelClient
      RestHighLevelClient restHighLevelClient = new RestHighLevelClient(restClientBuilder);

      return new OpenSearchRestClient(restHighLevelClient);
    } catch (Exception e) {
      throw new RuntimeException("Failed to create HTTP OpenSearchClient", e);
    }
  }

  private static HttpRequestInterceptor createLoggingInterceptor(boolean isHttps) {
    final String protocol = isHttps ? "HTTPS" : "HTTP";
    return new HttpRequestInterceptor() {
      @Override
      public void process(HttpRequest request, HttpContext context) {
        System.out.println("===== " + protocol + " REQUEST =====");
        System.out.println("Method: " + request.getRequestLine().getMethod());
        System.out.println("URI: " + request.getRequestLine().getUri());
        System.out.println("Request Type: " + request.getClass().getSimpleName());

        // Log headers
        System.out.println("Headers:");
        for (Header header : request.getAllHeaders()) {
          System.out.println("  " + header.getName() + ": " + header.getValue());
        }

        if (request instanceof HttpEntityEnclosingRequest) {
          HttpEntityEnclosingRequest entityRequest = (HttpEntityEnclosingRequest) request;
          if (entityRequest.getEntity() != null) {
            System.out.println("Content Type: " + entityRequest.getEntity().getContentType());
            System.out.println("Content Length: " + entityRequest.getEntity().getContentLength());
          }
        }
        System.out.println("=====================");
      }
    };
  }
}
