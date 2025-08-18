/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query.execution;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;
import org.opensearch.sql.common.response.ResponseListener;
import org.opensearch.sql.executor.ExecutionEngine.ExplainResponse;
import org.opensearch.sql.executor.ExecutionEngine.QueryResponse;
import org.opensearch.sql.sql.SQLService;
import org.opensearch.sql.sql.domain.SQLQueryRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import query.execution.formatter.ExecuteFormatter;
import query.execution.formatter.ExplainFormatter;

/** Implementation for executing SQL queries. */
public class SqlExecution implements Execution {
  private static final Logger logger = LoggerFactory.getLogger(SqlExecution.class);

  private static final String EXPLAIN_PATH = "/_explain";
  private static final String SQL_PATH = "/_plugins/_sql";

  private final SQLService sqlService;

  public SqlExecution(SQLService sqlService) {
    this.sqlService = sqlService;
  }

  @Override
  public String execute(String query, boolean isExplain, String format) {
    logger.info("Executing SQL query: " + query);

    try {
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<QueryResponse> executeRef = new AtomicReference<>();
      AtomicReference<Exception> errorRef = new AtomicReference<>();
      AtomicReference<ExplainResponse> explainRef = new AtomicReference<>();

      ResponseListener<QueryResponse> queryListener =
          createQueryResponseListener(executeRef, errorRef, latch);
      ResponseListener<ExplainResponse> explainListener =
          createExplainResponseListener(explainRef, errorRef, latch);

      if (isExplain) {
        // Remove "explain" prefix
        String actualQuery = query.substring(7).trim();

        String path = EXPLAIN_PATH;
        SQLQueryRequest sqlRequest = new SQLQueryRequest(new JSONObject(), actualQuery, path, "");
        sqlService.execute(sqlRequest, queryListener, explainListener);
      } else {
        // Regular SQL query
        String path = SQL_PATH;
        SQLQueryRequest sqlRequest = new SQLQueryRequest(new JSONObject(), query, path, "");
        sqlService.execute(sqlRequest, queryListener, explainListener);
      }

      latch.await();

      if (errorRef.get() != null) {
        return errorRef.get().toString();
      }

      // Handle the response based on the query type
      if (isExplain && explainRef.get() != null) {
        return ExplainFormatter.format(explainRef.get(), format);
      } else if (executeRef.get() != null) {
        // For regular queries, use the query response
        return ExecuteFormatter.format(executeRef.get(), format);
      } else {
        return "No results";
      }
    } catch (Exception e) {
      logger.error("SQL Execution Error: ", e);
      return e.toString();
    }
  }

  private ResponseListener<QueryResponse> createQueryResponseListener(
      AtomicReference<QueryResponse> executeRef,
      AtomicReference<Exception> errorRef,
      CountDownLatch latch) {

    return new ResponseListener<>() {
      @Override
      public void onResponse(QueryResponse response) {
        logger.info("Execute Result: " + response);
        executeRef.set(response);
        latch.countDown();
      }

      @Override
      public void onFailure(Exception e) {
        logger.error("Execution Error: " + e);
        errorRef.set(e);
        latch.countDown();
      }
    };
  }

  private ResponseListener<ExplainResponse> createExplainResponseListener(
      AtomicReference<ExplainResponse> explainRef,
      AtomicReference<Exception> errorRef,
      CountDownLatch latch) {

    return new ResponseListener<>() {
      @Override
      public void onResponse(ExplainResponse response) {
        logger.info("Explain Result: " + response);
        explainRef.set(response);
        latch.countDown();
      }

      @Override
      public void onFailure(Exception e) {
        logger.error("Explain Error: " + e);
        errorRef.set(e);
        latch.countDown();
      }
    };
  }
}
