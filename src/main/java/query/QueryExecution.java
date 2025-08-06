/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query;

import com.google.inject.Inject;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;
import org.opensearch.sql.common.response.ResponseListener;
import org.opensearch.sql.data.model.ExprValue;
import org.opensearch.sql.executor.ExecutionEngine.ExplainResponse;
import org.opensearch.sql.executor.ExecutionEngine.QueryResponse;
import org.opensearch.sql.executor.ExecutionEngine.Schema;
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.ppl.domain.PPLQueryRequest;
import org.opensearch.sql.protocol.response.QueryResult;
import org.opensearch.sql.protocol.response.format.CsvResponseFormatter;
import org.opensearch.sql.protocol.response.format.JdbcResponseFormatter;
import org.opensearch.sql.protocol.response.format.JsonResponseFormatter;
import org.opensearch.sql.protocol.response.format.RawResponseFormatter;
import org.opensearch.sql.protocol.response.format.ResponseFormatter;
import org.opensearch.sql.protocol.response.format.SimpleJsonResponseFormatter;
import org.opensearch.sql.sql.SQLService;
import org.opensearch.sql.sql.domain.SQLQueryRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class QueryExecution {
  private static final Logger logger = LoggerFactory.getLogger("QueryExecution");

  // API paths
  private static final String EXPLAIN_PATH = "/_explain";
  private static final String PPL_PATH = "/_plugins/_ppl";
  private static final String SQL_PATH = "/_plugins/_sql";

  // Format constants
  private static final String FORMAT_CSV = "csv";
  private static final String FORMAT_JSON = "json";
  private static final String FORMAT_COMPACT_JSON = "compact_json";
  private static final String FORMAT_JDBC = "jdbc";
  private static final String FORMAT_RAW = "raw";
  private static final String FORMAT_TABLE = "table";

  // Query type indicators
  private static final String EXPLAIN_PREFIX = "explain";

  private final PPLService pplService;
  private final SQLService sqlService;

  @Inject
  public QueryExecution(PPLService pplService, SQLService sqlService) {
    this.pplService = pplService;
    this.sqlService = sqlService;
  }

  public String execute(String query, boolean isPPL) {
    return execute(query, isPPL, FORMAT_JSON);
  }

  public String execute(String query, boolean isPPL, String format) {
    logger.info("Received query: " + query);
    logger.info("Query type: " + (isPPL ? "PPL" : "SQL"));

    try {
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<QueryResponse> executeRef = new AtomicReference<>();
      AtomicReference<Exception> errorRef = new AtomicReference<>();
      AtomicReference<ExplainResponse> explainRef = new AtomicReference<>();
      ResponseListener<QueryResponse> queryListener =
          new ResponseListener<>() {
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

      ResponseListener<ExplainResponse> explainListener =
          new ResponseListener<>() {
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

      // Check if this is an explain query
      boolean isExplainQuery = query.trim().toLowerCase().startsWith(EXPLAIN_PREFIX);

      if (isPPL) {
        logger.info("Executing PPL query...");
        // For explain queries, set the appropriate path
        String path = isExplainQuery ? EXPLAIN_PATH : PPL_PATH;
        PPLQueryRequest pplRequest = new PPLQueryRequest(query, new JSONObject(), path, "");

        if (isExplainQuery) {
          pplService.explain(pplRequest, explainListener);
        } else {
          pplService.execute(pplRequest, queryListener, explainListener);
        }
      } else {
        logger.info("Executing SQL query...");

        if (isExplainQuery) {
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
      }

      latch.await();

      if (errorRef.get() != null) {
        return errorRef.get().toString();
      }

      // Handle the response based on the query type
      if (isExplainQuery && explainRef.get() != null) {
        return formatExplainResponse(explainRef.get(), format);
      } else if (executeRef.get() != null && executeRef.get().getResults() != null) {
        // For regular queries, use the query response
        QueryResponse response = executeRef.get();

        // Create a new QueryResult from the response
        Schema schema = response.getSchema();
        List<ExprValue> results = (List<ExprValue>) response.getResults();
        QueryResult queryResult = new QueryResult(schema, results);

        // Format the result based on the requested format
        try {
          ResponseFormatter<QueryResult> formatter = null;

          switch (format.toLowerCase()) {
            case FORMAT_CSV:
              formatter = new CsvResponseFormatter();
              break;
            case FORMAT_JSON:
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            case FORMAT_COMPACT_JSON:
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.COMPACT);
              break;
            case FORMAT_JDBC:
              formatter = new JdbcResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            case FORMAT_RAW:
              formatter = new RawResponseFormatter();
              break;
            case FORMAT_TABLE:
              formatter = new JdbcResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            default:
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
          }

          return formatter.format(queryResult);
        } catch (Exception e) {
          logger.error("Error formatting result: ", e);
          return e.toString();
        }
      } else {
        return "No results";
      }
    } catch (Exception e) {
      logger.error("Execution Error: ", e);
      return e.toString();
    }
  }

  // Format an ExplainResponse object as JSON
  // using the same approach as TransportPPLQueryAction.java/RestSQLQueryAction.java
  private String formatExplainResponse(ExplainResponse response, String format) {
    try {
      String formatOutput =
          new JsonResponseFormatter<ExplainResponse>(JsonResponseFormatter.Style.PRETTY) {
            @Override
            protected Object buildJsonObject(ExplainResponse response) {
              return response;
            }
          }.format(response);
      return formatOutput;

    } catch (Exception e) {
      logger.error("Error formatting explain result: ", e);
      return e.toString();
    }
  }
}
