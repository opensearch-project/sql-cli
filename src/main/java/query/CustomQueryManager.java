/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query;

import org.opensearch.sql.executor.QueryId;
import org.opensearch.sql.executor.QueryManager;
import org.opensearch.sql.executor.execution.AbstractPlan;
import org.opensearch.sql.opensearch.client.OpenSearchClient;

// require QueryPlan, QueryID
public class CustomQueryManager implements QueryManager {
  private final OpenSearchClient openSearchClient;

  public CustomQueryManager(OpenSearchClient openSearchClient) {
    this.openSearchClient = openSearchClient;
  }

  @Override
  public QueryId submit(AbstractPlan queryPlan) {
    QueryId queryId = queryPlan.getQueryId();
    queryPlan.execute();

    return queryPlan.getQueryId();
  }

  @Override
  public boolean cancel(QueryId queryId) {
    return false;
  }
}
