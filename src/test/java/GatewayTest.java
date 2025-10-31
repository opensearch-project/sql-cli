/*
 * Copyright OpenSearch Contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import org.junit.jupiter.api.Test;
import org.opentest4j.AssertionFailedError;

public class GatewayTest {
  Gateway getGateway() {
    Gateway gateway = new Gateway();
    boolean connectionInitialized =
        gateway.initializeConnection("localhost", 9200, "http", null, null, false);
    if (!connectionInitialized) {
      throw new AssertionError("failed to initialize connection");
    }
    return gateway;
  }

  void assertSuccessfulPPL(Gateway gateway, String ppl) {
    String result = gateway.queryExecution(ppl, true, false, "table");
    System.out.println("Result is: " + result);

    if (result.contains("Exception")) {
      throw new AssertionFailedError(
          String.format("expected successful response string but got Exception:\n> %s", result));
    }
  }

  @Test
  void pplSelectAll() {
    Gateway gateway = getGateway();
    assertSuccessfulPPL(gateway, "source = accounts;");
  }

  @Test
  void pplSelectHead() {
    Gateway gateway = getGateway();
    assertSuccessfulPPL(gateway, "source = accounts | head 10;");
  }

  @Test
  void pplSelectOffsetHead() {
    Gateway gateway = getGateway();
    assertSuccessfulPPL(gateway, "source = accounts | head 200 from 9900;");
  }

  @Test
  void pplNumericStats() {
    Gateway gateway = getGateway();
    assertSuccessfulPPL(
        gateway,
        "source = accounts | stats max(balance) as max_balance, avg(balance) as avg_balance by"
            + " city");
  }

  @Test
  void pplValuesStats() {
    Gateway gateway = getGateway();
    assertSuccessfulPPL(gateway, "source = accounts | stats values(email) as emails");
  }
}
