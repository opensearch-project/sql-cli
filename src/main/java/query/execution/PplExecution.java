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
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.ppl.domain.PPLQueryRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import query.execution.formatter.ExecuteFormatter;
import query.execution.formatter.ExplainFormatter;

/** Implementation for executing PPL queries. */
public class PplExecution implements Execution {
  private static final Logger logger = LoggerFactory.getLogger(PplExecution.class);

  private static final String EXPLAIN_PATH = "/_explain";
  private static final String PPL_PATH = "/_plugins/_ppl";

  private final PPLService pplService;

  public PplExecution(PPLService pplService) {
    this.pplService = pplService;
  }

  @Override
  public String execute(String query, boolean isExplain, String format) {
    logger.info("Executing PPL query: " + query);

    try {
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<QueryResponse> executeRef = new AtomicReference<>();
      AtomicReference<Exception> errorRef = new AtomicReference<>();
      AtomicReference<ExplainResponse> explainRef = new AtomicReference<>();

      ResponseListener<QueryResponse> queryListener =
          createQueryResponseListener(executeRef, errorRef, latch);
      ResponseListener<ExplainResponse> explainListener =
          createExplainResponseListener(explainRef, errorRef, latch);

      // For explain queries, set the appropriate path
      String path = isExplain ? EXPLAIN_PATH : PPL_PATH;
      PPLQueryRequest pplRequest = new PPLQueryRequest(query, new JSONObject(), path, "");

      if (isExplain) {
        pplService.explain(pplRequest, explainListener);
      } else {
        pplService.execute(pplRequest, queryListener, explainListener);
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
      logger.error("PPL Execution Error: ", e);
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
      public void onFailure(Exception ex) {
        logger.error("Execution Error: {}", ex.getMessage(), ex);
        errorRef.set(ex);
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
