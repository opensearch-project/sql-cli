/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query.execution.formatter;

import java.util.List;
import org.opensearch.sql.data.model.ExprValue;
import org.opensearch.sql.executor.ExecutionEngine.QueryResponse;
import org.opensearch.sql.executor.ExecutionEngine.Schema;
import org.opensearch.sql.protocol.response.QueryResult;
import org.opensearch.sql.protocol.response.format.CsvResponseFormatter;
import org.opensearch.sql.protocol.response.format.JdbcResponseFormatter;
import org.opensearch.sql.protocol.response.format.JsonResponseFormatter;
import org.opensearch.sql.protocol.response.format.RawResponseFormatter;
import org.opensearch.sql.protocol.response.format.ResponseFormatter;
import org.opensearch.sql.protocol.response.format.SimpleJsonResponseFormatter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Formatter for QueryResponse objects. */
public class ExecuteFormatter {
  private static final Logger logger = LoggerFactory.getLogger(ExecuteFormatter.class);

  private static final String FORMAT_CSV = "csv";
  private static final String FORMAT_JSON = "json";
  private static final String FORMAT_COMPACT_JSON = "compact_json";
  private static final String FORMAT_JDBC = "jdbc";
  private static final String FORMAT_RAW = "raw";
  private static final String FORMAT_TABLE = "table";

  /**
   * Format a QueryResponse object based on the specified format.
   *
   * @param response The QueryResponse to format
   * @param format The output format
   * @return The formatted response as a string
   */
  public static String format(QueryResponse response, String format) {
    try {
      if (response == null || response.getResults() == null) {
        return "No results";
      }

      Schema schema = response.getSchema();
      List<ExprValue> results = (List<ExprValue>) response.getResults();
      QueryResult queryResult = new QueryResult(schema, results);

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
  }
}
