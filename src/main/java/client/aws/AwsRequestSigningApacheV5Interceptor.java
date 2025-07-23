/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client.aws;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Collectors;
import org.apache.hc.core5.http.ClassicHttpRequest;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.EntityDetails;
import org.apache.hc.core5.http.Header;
import org.apache.hc.core5.http.HttpException;
import org.apache.hc.core5.http.HttpHeaders;
import org.apache.hc.core5.http.HttpRequest;
import org.apache.hc.core5.http.HttpRequestInterceptor;
import org.apache.hc.core5.http.io.entity.BasicHttpEntity;
import org.apache.hc.core5.http.io.entity.BufferedHttpEntity;
import org.apache.hc.core5.http.message.BasicHeader;
import org.apache.hc.core5.http.message.BasicHttpRequest;
import org.apache.hc.core5.http.protocol.HttpContext;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.http.SdkHttpFullRequest;
import software.amazon.awssdk.http.SdkHttpMethod;
import software.amazon.awssdk.http.auth.spi.signer.HttpSigner;
import software.amazon.awssdk.http.auth.spi.signer.SignedRequest;
import software.amazon.awssdk.identity.spi.AwsCredentialsIdentity;
import software.amazon.awssdk.regions.Region;

// AWS Request Signing Interceptor by acm19

/**
 * An {@link HttpRequestInterceptor} that signs requests for any AWS service running in a specific
 * region using an AWS {@link HttpSigner} and {@link AwsCredentialsProvider}.
 */
public final class AwsRequestSigningApacheV5Interceptor implements HttpRequestInterceptor {
  private final RequestSigner signer;

  /**
   * Creates an {@code AwsRequestSigningApacheInterceptor} with the ability to sign request for a
   * specific service in a region and defined credentials.
   *
   * @param service service the client is connecting to
   * @param signer signer implementation.
   * @param awsCredentialsProvider source of AWS credentials for signing
   * @param region signing region
   */
  public AwsRequestSigningApacheV5Interceptor(
      String service,
      HttpSigner<AwsCredentialsIdentity> signer,
      AwsCredentialsProvider awsCredentialsProvider,
      Region region) {
    this.signer = new RequestSigner(service, signer, awsCredentialsProvider, region);
  }

  /** {@inheritDoc} */
  @Override
  public void process(HttpRequest request, EntityDetails entityDetails, HttpContext context)
      throws HttpException, IOException {
    // copy Apache HttpRequest to AWS request
    SdkHttpFullRequest.Builder requestBuilder =
        SdkHttpFullRequest.builder()
            .method(SdkHttpMethod.fromValue(request.getMethod()))
            .uri(buildUri(request));

    // Print the request type
    System.out.println("AwsRequestSigningApacheV5Interceptor.process()");
    System.out.println("Request type: " + request.getClass().getName());
    System.out.println("Request method: " + request.getMethod());
    System.out.println("Request URI: " + request.getRequestUri());

    // Print entity details
    System.out.println(
        "Entity details: "
            + (entityDetails != null
                ? "Content type: "
                    + entityDetails.getContentType()
                    + ", Content length: "
                    + entityDetails.getContentLength()
                : "null"));

    if (request instanceof ClassicHttpRequest) {
      ClassicHttpRequest classicHttpRequest = (ClassicHttpRequest) request;

      if (classicHttpRequest.getEntity() != null) {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        classicHttpRequest.getEntity().writeTo(outputStream);
        if (!classicHttpRequest.getEntity().isRepeatable()) {
          // copy back the entity, so it can be read again
          BasicHttpEntity entity =
              new BasicHttpEntity(
                  new ByteArrayInputStream(outputStream.toByteArray()),
                  ContentType.parse(entityDetails.getContentType()));
          // wrap into repeatable entity to support retries
          classicHttpRequest.setEntity(new BufferedHttpEntity(entity));
        }
        requestBuilder.contentStreamProvider(
            () -> new ByteArrayInputStream(outputStream.toByteArray()));
      }
      // RestClient is always BasicHttpRequest?
    } else if (request instanceof BasicHttpRequest) {
      System.out.println("BasicHttpRequest");
      // If it's POST/DELETE request, then manually adding body content to the body
      // Because BasicHttpRequest does not have its body content attach to it
      // Only its metadata
      Set<String> methods = Set.of("POST", "DELETE");
      if (methods.contains(request.getMethod().toUpperCase())) {
        Path path = Paths.get("src/main/java/client/aws/aws_body.json");
        String bodyContent = "";

        if (Files.exists(path)) {
          try (BufferedReader reader = Files.newBufferedReader(path)) {
            bodyContent = reader.lines().collect(Collectors.joining("\n"));
          } catch (IOException e) {
            System.err.println("Failed to read: " + e.getMessage());
            e.printStackTrace();
          }
        } else {
          System.out.println("File does not exist at: " + path.toAbsolutePath());
        }

        // Only proceed if dslQuery is not empty
        if (!bodyContent.isEmpty()) {
          byte[] bodyBytes = bodyContent.getBytes(StandardCharsets.UTF_8);
          System.out.println("Byte added: " + bodyBytes.length);
          System.out.println("Body content signing: " + bodyContent);
          requestBuilder.contentStreamProvider(() -> new ByteArrayInputStream(bodyBytes));
        }
      }
    }

    Map<String, List<String>> headers = headerArrayToMap(request.getHeaders());
    // adds a hash of the request payload when signing
    headers.put("x-amz-content-sha256", Collections.singletonList("required"));
    requestBuilder.headers(headers);
    SignedRequest signedRequest = signer.signRequest(requestBuilder.build());

    // copy everything back
    request.setHeaders(mapToHeaderArray(signedRequest.request().headers()));
  }

  private static URI buildUri(HttpRequest request) throws IOException {
    try {
      return request.getUri();
    } catch (URISyntaxException ex) {
      throw new IOException("Invalid URI", ex);
    }
  }

  private static Map<String, List<String>> headerArrayToMap(Header[] headers) {
    Map<String, List<String>> headersMap = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
    for (Header header : headers) {
      if (!skipHeader(header)) {
        headersMap.put(
            header.getName(),
            headersMap.getOrDefault(
                header.getName(), new LinkedList<>(Collections.singletonList(header.getValue()))));
      }
    }
    return headersMap;
  }

  private static boolean skipHeader(Header header) {
    return (HttpHeaders.CONTENT_LENGTH.equalsIgnoreCase(header.getName())
            && "0".equals(header.getValue())) // Strip Content-Length: 0
        || HttpHeaders.HOST.equalsIgnoreCase(header.getName()); // Host comes from endpoint
  }

  private static Header[] mapToHeaderArray(Map<String, List<String>> mapHeaders) {
    Header[] headers = new Header[mapHeaders.size()];
    int i = 0;
    for (Map.Entry<String, List<String>> headerEntry : mapHeaders.entrySet()) {
      for (String value : headerEntry.getValue()) {
        headers[i++] = new BasicHeader(headerEntry.getKey(), value);
      }
    }
    return headers;
  }
}
