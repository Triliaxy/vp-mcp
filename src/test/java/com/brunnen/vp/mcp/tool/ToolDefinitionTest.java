package com.brunnen.vp.mcp.tool;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

public class ToolDefinitionTest {
  public static class FailingTool {
    public String fail() {
      throw new IllegalStateException("The diagram element still exists");
    }
  }

  @Test
  public void exposesTheUnderlyingToolErrorToMcp() throws Exception {
    ToolDefinition tool =
        new ToolDefinition(
            "fail",
            "",
            new ObjectMapper().createObjectNode(),
            new FailingTool(),
            FailingTool.class.getMethod("fail"));
    IllegalStateException error =
        assertThrows(IllegalStateException.class, () -> tool.execute(null));
    assertEquals("The diagram element still exists", error.getMessage());
  }
}
