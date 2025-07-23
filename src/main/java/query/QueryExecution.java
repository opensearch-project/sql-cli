/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query;

import com.google.inject.Inject;
import java.nio.file.*;
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

public class QueryExecution {

  private final PPLService pplService;
  private final SQLService sqlService;

  @Inject
  public QueryExecution(PPLService pplService, SQLService sqlService) {
    this.pplService = pplService;
    this.sqlService = sqlService;
  }

  public String execute(String query, boolean isPPL) {
    return execute(query, isPPL, "json");
  }

  public String execute(String query, boolean isPPL, String format) {
    System.out.println("Received query: " + query);
    System.out.println("Query type: " + (isPPL ? "PPL" : "SQL"));

    try {
      CountDownLatch latch = new CountDownLatch(1);
      AtomicReference<QueryResponse> executeRef = new AtomicReference<>();
      AtomicReference<Exception> errorRef = new AtomicReference<>();
      AtomicReference<ExplainResponse> explainRef = new AtomicReference<>();
      ResponseListener<QueryResponse> queryListener =
          new ResponseListener<>() {
            @Override
            public void onResponse(QueryResponse response) {
              System.out.println("Execute Result: " + response);
              executeRef.set(response);
              latch.countDown();
            }

            @Override
            public void onFailure(Exception e) {
              System.out.println("queryExecution Execution Error: " + e);
              errorRef.set(e);
              latch.countDown();
            }
          };

      ResponseListener<ExplainResponse> explainListener =
          new ResponseListener<>() {
            @Override
            public void onResponse(ExplainResponse response) {
              System.out.println("Explain response: " + response);
              explainRef.set(response);
              latch.countDown();
            }

            @Override
            public void onFailure(Exception e) {
              System.out.println("queryExecution Explain Error: " + e);
              errorRef.set(e);
              latch.countDown();
            }
          };

      // Check if this is an explain query
      boolean isExplainQuery = query.trim().toLowerCase().startsWith("explain");

      if (isPPL) {
        System.out.println("Executing PPL query...");
        // For explain queries, set the path to "/_explain"
        String path = isExplainQuery ? "/_explain" : "/_plugins/_ppl";
        PPLQueryRequest pplRequest = new PPLQueryRequest(query, new JSONObject(), path, "");

        if (isExplainQuery) {
          System.out.println("Calling pplService.explain()");
          pplService.explain(pplRequest, explainListener);
        } else {
          System.out.println("Calling pplService.execute()");
          pplService.execute(pplRequest, queryListener, explainListener);
        }
      } else {
        System.out.println("Executing SQL query...");

        if (isExplainQuery) {
          // Remove "explain" prefix
          String actualQuery = query.substring(7).trim();
          System.out.println("SQL explain query for: " + actualQuery);

          String path = "/_explain";
          SQLQueryRequest sqlRequest = new SQLQueryRequest(new JSONObject(), actualQuery, path, "");

          System.out.println("Calling sqlService.execute() with explain path");
          sqlService.execute(sqlRequest, queryListener, explainListener);
        } else {
          // Regular SQL query
          String path = "/_plugins/_sql";
          SQLQueryRequest sqlRequest = new SQLQueryRequest(new JSONObject(), query, path, "");

          System.out.println("Calling sqlService.execute()");
          sqlService.execute(sqlRequest, queryListener, explainListener);
        }
      }

      latch.await();

      Files.deleteIfExists(Paths.get("src/main/java/client/aws/aws_body.json"));

      if (errorRef.get() != null) {
        errorRef.get().printStackTrace();
        return "queryExecution Error: " + errorRef.get();
      }

      // Handle the response based on the query type
      if (isExplainQuery && explainRef.get() != null) {
        System.out.println("Explain raw: \n" + explainRef.get().toString());
        return formatExplainResponse(explainRef.get(), format);
        // return explainRef.get().toString();
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
            case "csv":
              formatter = new CsvResponseFormatter();
              break;
            case "json":
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            case "compact_json":
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.COMPACT);
              break;
            case "jdbc":
              formatter = new JdbcResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            case "raw":
              formatter = new RawResponseFormatter();
              break;
            case "table":
              formatter = new JdbcResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
            default:
              formatter = new SimpleJsonResponseFormatter(JsonResponseFormatter.Style.PRETTY);
              break;
          }

          return formatter.format(queryResult);
        } catch (Exception e) {
          e.printStackTrace();
          return "Error formatting results: " + e.getMessage() + "\nRaw response: " + response;
        }
      } else {
        return "No results";
      }
    } catch (Exception e) {
      e.printStackTrace();
      return "queryExecution Error: " + e;
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

      System.out.println("After explain format: \n" + formatOutput);

      return formatOutput;

    } catch (Exception e) {
      e.printStackTrace();
      return "Error formatting explain results: " + e.getMessage() + "\nRaw response: " + response;
    }
  }
}
