/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

package query.execution;

/** Interface for executing different types of queries. */
public interface Execution {

  /**
   * Execute a query and return the result as a formatted string.
   *
   * @param query The query to execute
   * @param isExplain Whether this is an explain query
   * @param format The output format
   * @return The formatted query result
   */
  String execute(String query, boolean isExplain, String format);
}
