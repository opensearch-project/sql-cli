/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query.execution.formatter;

import org.opensearch.sql.executor.ExecutionEngine.ExplainResponse;
import org.opensearch.sql.protocol.response.format.JsonResponseFormatter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Formatter for ExplainResponse objects. same approach as in
 * TransportPPLQueryAction.java/RestSQLQueryAction.java
 */
public class ExplainFormatter {
  private static final Logger logger = LoggerFactory.getLogger(ExplainFormatter.class);

  /**
   * Format an ExplainResponse object as JSON.
   *
   * @param response The ExplainResponse to format
   * @param format The output format (currently only JSON is supported)
   * @return The formatted response as a string
   */
  public static String format(ExplainResponse response, String format) {
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
