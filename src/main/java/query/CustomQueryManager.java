/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.opensearch.sql.executor.QueryId;
import org.opensearch.sql.executor.QueryManager;
import org.opensearch.sql.executor.execution.AbstractPlan;
import org.opensearch.sql.opensearch.client.OpenSearchClient;

// require QueryPlan, QueryID
public class CustomQueryManager implements QueryManager {
  private final OpenSearchClient openSearchClient;
  private final ExecutorService executor = Executors.newSingleThreadExecutor();

  public CustomQueryManager(OpenSearchClient openSearchClient) {
    this.openSearchClient = openSearchClient;
  }

  @Override
  public QueryId submit(AbstractPlan queryPlan) {
    QueryId queryId = queryPlan.getQueryId();
    executor.submit(
        () -> {
          try {
            queryPlan.execute();
          } catch (Exception e) {
            e.printStackTrace();
          }
        });
    return queryPlan.getQueryId();
  }

  @Override
  public boolean cancel(QueryId queryId) {
    return false;
  }
}
