/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client;

import java.lang.reflect.Method;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Builder class for creating OpenSearchClient instances. Supports both HTTP4 and HTTP5 client
 * implementations.
 */
public class ClientBuilder {
  private static final Logger logger = LoggerFactory.getLogger(ClientBuilder.class);

  // Client configuration
  private String host;
  private int port;
  private String protocol;
  private String username;
  private String password;
  private boolean ignoreSSL;
  private boolean useAwsAuth;
  private String awsEndpoint;
  private boolean useHttp5;


  /**
   * Sets the host for the client.
   *
   * @param host the host name or IP address
   * @return this builder instance
   */
  public ClientBuilder withHost(String host) {
    this.host = host;
    return this;
  }

  /**
   * Sets the port for the client.
   *
   * @param port the port number
   * @return this builder instance
   */
  public ClientBuilder withPort(int port) {
    this.port = port;
    return this;
  }

  /**
   * Sets the protocol for the client (http or https).
   *
   * @param protocol the protocol
   * @return this builder instance
   */
  public ClientBuilder withProtocol(String protocol) {
    this.protocol = protocol;
    return this;
  }

  /**
   * Sets the username for basic authentication.
   *
   * @param username the username
   * @return this builder instance
   */
  public ClientBuilder withUsername(String username) {
    this.username = username;
    return this;
  }

  /**
   * Sets the password for basic authentication.
   *
   * @param password the password
   * @return this builder instance
   */
  public ClientBuilder withPassword(String password) {
    this.password = password;
    return this;
  }

  /**
   * Sets whether to ignore SSL certificate validation.
   *
   * @param ignoreSSL true to ignore SSL certificate validation
   * @return this builder instance
   */
  public ClientBuilder withIgnoreSSL(boolean ignoreSSL) {
    this.ignoreSSL = ignoreSSL;
    return this;
  }

  /**
   * Configures the client to use AWS authentication.
   *
   * @param awsEndpoint the AWS endpoint
   * @return this builder instance
   */
  public ClientBuilder withAwsAuth(String awsEndpoint) {
    this.useAwsAuth = true;
    this.awsEndpoint = awsEndpoint;
    return this;
  }

  /**
   * Sets whether to use HTTP5 client implementation.
   *
   * @param useHttp5 true to use HTTP5, false to use HTTP4
   * @return this builder instance
   */
  public ClientBuilder withHttp5(boolean useHttp5) {
    this.useHttp5 = useHttp5;
    return this;
  }

  /**
   * Builds and returns an OpenSearchClient instance based on the configured parameters. Uses
   * reflection to create the appropriate client (HTTP4 or HTTP5) based on configuration.
   *
   * @return an OpenSearchClient instance
   * @throws RuntimeException if client creation fails
   */
  public OpenSearchClient build() {
    try {
      // Determine which client class to use based on useHttp5 flag
      String clientClassName = useHttp5 ? "client.http5.Http5Client" : "client.http4.Http4Client";
      Class<?> clientClass = Class.forName(clientClassName);

      if (useAwsAuth) {
        // Call createAwsClient(awsEndpoint)
        logger.info("Building AWS client with endpoint: {}", awsEndpoint);
        Method method = clientClass.getMethod("createAwsClient", String.class);
        return (OpenSearchClient) method.invoke(null, awsEndpoint);
      } else {
        // Call createClient(host, port, protocol, username, password, ignoreSSL)
        logger.info("Building {} client for {}:{}", protocol.toUpperCase(), host, port);
        Method method =
            clientClass.getMethod(
                "createClient",
                String.class,
                int.class,
                String.class,
                String.class,
                String.class,
                boolean.class);
        return (OpenSearchClient) method.invoke(null, host, port, protocol, username, password, ignoreSSL);
      }
    } catch (Exception e) {
      throw new RuntimeException("Failed to create OpenSearchClient: " + e.getMessage(), e);
    }
  }
}
