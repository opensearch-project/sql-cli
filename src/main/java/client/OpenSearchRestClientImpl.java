/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package client;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import lombok.RequiredArgsConstructor;
import org.opensearch.action.admin.cluster.settings.ClusterGetSettingsRequest;
import org.opensearch.action.admin.indices.settings.get.GetSettingsRequest;
import org.opensearch.action.admin.indices.settings.get.GetSettingsResponse;
import org.opensearch.action.search.*;
import org.opensearch.client.RequestOptions;
import org.opensearch.client.RestHighLevelClient;
import org.opensearch.client.indices.CreateIndexRequest;
import org.opensearch.client.indices.GetIndexRequest;
import org.opensearch.client.indices.GetIndexResponse;
import org.opensearch.client.indices.GetMappingsRequest;
import org.opensearch.client.indices.GetMappingsResponse;
import org.opensearch.cluster.metadata.AliasMetadata;
import org.opensearch.common.settings.Settings;
import org.opensearch.common.xcontent.XContentFactory;
import org.opensearch.core.xcontent.ToXContent;
import org.opensearch.core.xcontent.XContentBuilder;
import org.opensearch.search.builder.PointInTimeBuilder;
import org.opensearch.search.builder.SearchSourceBuilder;
import org.opensearch.search.sort.SortOrder;
import org.opensearch.sql.opensearch.client.OpenSearchClient;
import org.opensearch.sql.opensearch.mapping.IndexMapping;
import org.opensearch.sql.opensearch.request.OpenSearchQueryRequest;
import org.opensearch.sql.opensearch.request.OpenSearchRequest;
import org.opensearch.sql.opensearch.request.OpenSearchScrollRequest;
import org.opensearch.sql.opensearch.response.OpenSearchResponse;
import org.opensearch.transport.client.node.NodeClient;

/**
 * OpenSearch REST client to support standalone mode that runs entire engine from remote.
 *
 * <p>TODO: Support for authN and authZ with AWS Sigv4 or security plugin.
 */
@RequiredArgsConstructor
public class OpenSearchRestClientImpl implements OpenSearchClient {

  /** OpenSearch high level REST client. */
  private final RestHighLevelClient client;

  @Override
  public boolean exists(String indexName) {
    System.out.println("OpenSearchRestClientImpl.exists()");
    try {
      return client.indices().exists(new GetIndexRequest(indexName), RequestOptions.DEFAULT);
    } catch (IOException e) {
      throw new IllegalStateException("Failed to check if index [" + indexName + "] exist", e);
    }
  }

  @Override
  public void createIndex(String indexName, Map<String, Object> mappings) {
    System.out.println("OpenSearchRestClientImpl.createIndex()");
    try {
      client
          .indices()
          .create(new CreateIndexRequest(indexName).mapping(mappings), RequestOptions.DEFAULT);
    } catch (IOException e) {
      throw new IllegalStateException("Failed to create index [" + indexName + "]", e);
    }
  }

  @Override
  public Map<String, IndexMapping> getIndexMappings(String... indexExpression) {
    System.out.println("OpenSearchRestClientImpl.getIndexMappings()");
    GetMappingsRequest request = new GetMappingsRequest().indices(indexExpression);
    try {
      GetMappingsResponse response = client.indices().getMapping(request, RequestOptions.DEFAULT);
      return response.mappings().entrySet().stream()
          .collect(Collectors.toMap(Map.Entry::getKey, e -> new IndexMapping(e.getValue())));
    } catch (IOException e) {
      throw new IllegalStateException("Failed to get index mappings for " + indexExpression, e);
    }
  }

  @Override
  public Map<String, Integer> getIndexMaxResultWindows(String... indexExpression) {
    System.out.println("OpenSearchRestClientImpl.getIndexMaxResultWindows()");
    GetSettingsRequest request =
        new GetSettingsRequest().indices(indexExpression).includeDefaults(true);
    try {
      GetSettingsResponse response = client.indices().getSettings(request, RequestOptions.DEFAULT);
      Map<String, Settings> settings = response.getIndexToSettings();
      Map<String, Settings> defaultSettings = response.getIndexToDefaultSettings();
      Map<String, Integer> result = new HashMap<>();

      defaultSettings.forEach(
          (key, value) -> {
            Integer maxResultWindow = value.getAsInt("index.max_result_window", null);
            if (maxResultWindow != null) {
              result.put(key, maxResultWindow);
            }
          });

      settings.forEach(
          (key, value) -> {
            Integer maxResultWindow = value.getAsInt("index.max_result_window", null);
            if (maxResultWindow != null) {
              result.put(key, maxResultWindow);
            }
          });

      return result;
    } catch (IOException e) {
      throw new IllegalStateException("Failed to get max result window for " + indexExpression, e);
    }
  }

  @Override
  public OpenSearchResponse search(OpenSearchRequest request) {
    System.out.println(
        "OpenSearchRestClientImpl.search() - request type: " + request.getClass().getSimpleName());

    if (request instanceof OpenSearchScrollRequest) {
      OpenSearchScrollRequest scrollRequest = (OpenSearchScrollRequest) request;
      System.out.println(
          "Scroll request - Index names: "
              + Arrays.toString(scrollRequest.getIndexName().getIndexNames()));
      System.out.println("Scroll request - Scroll ID: " + scrollRequest.getScrollId());
      System.out.println("Scroll request - Scroll timeout: " + scrollRequest.getScrollTimeout());
      System.out.println("Scroll request - Is scroll: " + scrollRequest.isScroll());
    } else if (request instanceof OpenSearchQueryRequest) {
      OpenSearchQueryRequest queryRequest = (OpenSearchQueryRequest) request;
      System.out.println(
          "Query request - Index names: "
              + Arrays.toString(queryRequest.getIndexName().getIndexNames()));

      // Get the source builder and save it to a file for the AWS interceptor to use
      // Set up similar to OpenSearchQueryRequest.java
      SearchSourceBuilder sourceBuilder = queryRequest.getSourceBuilder();
      if (sourceBuilder != null) {
        String pitId = queryRequest.getPitId();
        String dslQuery;

        if (pitId != null) {
          System.out.println("Query request - PIT ID: " + pitId);
          // Configure PIT search request using the existing pitId
          sourceBuilder.pointInTimeBuilder(new PointInTimeBuilder(pitId));
          sourceBuilder.timeout(queryRequest.getCursorKeepAlive());

          // Check for search after
          Object[] searchAfter = queryRequest.getSearchAfter();
          if (searchAfter != null) {
            sourceBuilder.searchAfter(searchAfter);
          }

          // Set sort field for search_after
          if (sourceBuilder.sorts() == null) {
            System.out.println("Adding default sort fields for PIT");
            sourceBuilder.sort("_doc", SortOrder.ASC);
            // Workaround to preserve sort location more exactly
            // see https://github.com/opensearch-project/sql/pull/3061
            sourceBuilder.sort("_id", SortOrder.ASC);
          }
        }

        // Convert the final source builder to a string
        dslQuery = sourceBuilder.toString();
        System.out.println("Query request - Source builder: " + dslQuery);

        // Write the DSL query to a file for the AWS interceptor to use
        writeForAwsBody(dslQuery);
      } else {
        System.out.println("Query request - Source builder: null");
      }
    }
    return request.search(
        req -> {
          try {
            return client.search(req, RequestOptions.DEFAULT);
          } catch (IOException e) {
            throw new IllegalStateException(
                "Failed to perform search operation with request " + req, e);
          }
        },
        req -> {
          try {
            return client.scroll(req, RequestOptions.DEFAULT);
          } catch (IOException e) {
            throw new IllegalStateException(
                "Failed to perform scroll operation with request " + req, e);
          }
        });
  }

  /**
   * Get the combination of the indices and the alias.
   *
   * @return the combination of the indices and the alias
   */
  @Override
  public List<String> indices() {
    System.out.println("OpenSearchRestClientImpl.indices()");
    try {
      GetIndexResponse indexResponse =
          client.indices().get(new GetIndexRequest(), RequestOptions.DEFAULT);
      final Stream<String> aliasStream =
          ImmutableList.copyOf(indexResponse.getAliases().values()).stream()
              .flatMap(Collection::stream)
              .map(AliasMetadata::alias);
      return Stream.concat(Arrays.stream(indexResponse.getIndices()), aliasStream)
          .collect(Collectors.toList());
    } catch (IOException e) {
      throw new IllegalStateException("Failed to get indices", e);
    }
  }

  /**
   * Get meta info of the cluster.
   *
   * @return meta info of the cluster.
   */
  @Override
  public Map<String, String> meta() {
    System.out.println("OpenSearchRestClientImpl.meta()");
    try {
      final ImmutableMap.Builder<String, String> builder = new ImmutableMap.Builder<>();
      ClusterGetSettingsRequest request = new ClusterGetSettingsRequest();
      request.includeDefaults(true);
      request.local(true);
      final Settings defaultSettings =
          client.cluster().getSettings(request, RequestOptions.DEFAULT).getDefaultSettings();
      builder.put(META_CLUSTER_NAME, defaultSettings.get("cluster.name", "opensearch"));
      builder.put(
          "plugins.sql.pagination.api", defaultSettings.get("plugins.sql.pagination.api", "true"));
      return builder.build();
    } catch (IOException e) {
      throw new IllegalStateException("Failed to get cluster meta info", e);
    }
  }

  @Override
  public void cleanup(OpenSearchRequest request) {
    System.out.println("OpenSearchRestClientImpl.cleanup()");
    if (request instanceof OpenSearchScrollRequest) {
      request.clean(
          scrollId -> {
            try {
              ClearScrollRequest clearRequest = new ClearScrollRequest();
              clearRequest.addScrollId(scrollId);
              client.clearScroll(clearRequest, RequestOptions.DEFAULT);
            } catch (IOException e) {
              throw new IllegalStateException(
                  "Failed to clean up resources for search request " + request, e);
            }
          });
    } else {
      request.clean(
          pitId -> {
            DeletePitRequest deletePitRequest = new DeletePitRequest(pitId);
            deletePit(deletePitRequest);
          });
    }
  }

  @Override
  public void schedule(Runnable task) {
    System.out.println("OpenSearchRestClientImpl.schedule()");
    task.run();
  }

  @Override
  public NodeClient getNodeClient() {
    throw new UnsupportedOperationException("Unsupported method.");
  }

  @Override
  public String createPit(CreatePitRequest createPitRequest) {
    System.out.println("OpenSearchRestClientImpl.createPit()");

    try {
      // For the AWS interceptor to use
      String bodyContent = getBodyContent(createPitRequest);
      writeForAwsBody(bodyContent);

      CreatePitResponse createPitResponse =
          client.createPit(createPitRequest, RequestOptions.DEFAULT);
      String pitId = createPitResponse.getId();
      System.out.println("PIT created successfully with ID: " + pitId);
      return pitId;
    } catch (IOException e) {
      throw new RuntimeException("Error occurred while creating PIT for new engine SQL query", e);
    }
  }

  @Override
  public void deletePit(DeletePitRequest deletePitRequest) {
    System.out.println("OpenSearchRestClientImpl.deletePit()");

    try {
      // For the AWS interceptor to use
      String bodyContent = getBodyContent(deletePitRequest);
      writeForAwsBody(bodyContent);

      DeletePitResponse deletePitResponse =
          client.deletePit(deletePitRequest, RequestOptions.DEFAULT);
    } catch (IOException e) {
      throw new RuntimeException("Error occurred while creating PIT for new engine SQL query", e);
    }
  }

  // Helper methods for AWS interceptor to sign its body
  private String getBodyContent(ToXContent request) throws IOException {
    XContentBuilder builder = XContentFactory.jsonBuilder();
    if (request instanceof DeletePitRequest) {
      request.toXContent(builder, ToXContent.EMPTY_PARAMS);
    } else if (request instanceof CreatePitRequest) {
      builder.startObject();
      request.toXContent(builder, ToXContent.EMPTY_PARAMS);
      builder.endObject();
    }

    String jsonBody = builder.toString();
    System.out.println("===== " + request.getClass().getSimpleName() + " Body Content =====");
    System.out.println(jsonBody);
    return jsonBody;
  }

  private void writeForAwsBody(String content) {
    File dslFile = new File("src/main/java/client/aws/aws_body.json");
    try (FileWriter writer = new FileWriter(dslFile)) {
      writer.write(content);
      System.out.println("Wrote DSL query to file: " + dslFile.getAbsolutePath());
    } catch (IOException e) {
      System.err.println("Failed to write DSL query to file: " + e.getMessage());
      e.printStackTrace();
    }
  }
}
