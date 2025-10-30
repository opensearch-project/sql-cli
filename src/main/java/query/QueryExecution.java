/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query;

import com.google.inject.Inject;
import org.opensearch.sql.ppl.PPLService;
import org.opensearch.sql.sql.SQLService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import query.execution.Execution;
import query.execution.PplExecution;
import query.execution.SqlExecution;

import java.util.Arrays;

/** Main class for executing queries using the factory and strategy patterns. */
public class QueryExecution {
  private static final Logger logger = LoggerFactory.getLogger(QueryExecution.class);

  private final PPLService pplService;
  private final SQLService sqlService;

  @Inject
  public QueryExecution(PPLService pplService, SQLService sqlService) {
    this.pplService = pplService;
    this.sqlService = sqlService;
  }

  /**
   * Execute a query using the appropriate execution implementation based on the query type.
   *
   * @param query The query to execute
   * @param isPPL Whether the query is a PPL query
   * @param isExplain Whether this is an explain query
   * @param format The output format
   * @return The formatted query result
   */
  public String execute(String query, boolean isPPL, boolean isExplain, String format) {
    logger.info("Received query: " + query);
    logger.info("Query type: " + (isPPL ? "PPL" : "SQL"));

    try {

      Execution execution;
      if (isPPL) {
        execution = new PplExecution(pplService);
      } else {
        execution = new SqlExecution(sqlService);
      }

      return execution.execute(query, isExplain, format);
    } catch (Exception e) {
      logger.error("Execution Error: {}", Arrays.stream(e.getStackTrace()).toList());
      return e.toString();
    }
  }
}
