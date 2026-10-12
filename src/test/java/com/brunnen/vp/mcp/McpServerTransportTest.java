package com.brunnen.vp.mcp;

import static org.junit.jupiter.api.Assertions.*;

import com.brunnen.vp.mcp.tool.Tool;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.ServerSocket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class McpServerTransportTest {
  private static final ObjectMapper JSON = new ObjectMapper();
  private final HttpClient client = HttpClient.newHttpClient();
  private McpServer server;
  private String baseUrl;

  public static class TestTools {
    @Tool(name = "echo", description = "Echo a test value")
    public String echo(String value) {
      return value;
    }

    @Tool(name = "fail", description = "Return a test error")
    public String fail() {
      throw new IllegalStateException("Verified tool error");
    }
  }

  @BeforeEach
  public void startServer() throws Exception {
    int port;
    try (ServerSocket socket = new ServerSocket(0)) {
      port = socket.getLocalPort();
    }
    server = new McpServer();
    server.setPort(port);
    server.registerTools(new TestTools());
    server.start();
    baseUrl = "http://127.0.0.1:" + port;
  }

  @AfterEach
  public void stopServer() {
    server.stop();
  }

  private HttpRequest request(String path, String body) {
    return HttpRequest.newBuilder(URI.create(baseUrl + path))
        .timeout(Duration.ofSeconds(10))
        .header("Content-Type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build();
  }

  @Test
  public void supportsInitializationToolsErrorsAndNotifications() throws Exception {
    HttpResponse<String> init =
        client.send(
            request(
                "/mcp", "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}"),
            HttpResponse.BodyHandlers.ofString());
    assertEquals(200, init.statusCode());
    assertEquals(
        "visual-paradigm-mcp-server",
        JSON.readTree(init.body()).path("result").path("serverInfo").path("name").asText());
    HttpResponse<String> list =
        client.send(
            request("/mcp", "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}"),
            HttpResponse.BodyHandlers.ofString());
    assertEquals(2, JSON.readTree(list.body()).path("result").path("tools").size());
    HttpResponse<String> failure =
        client.send(
            request(
                "/mcp",
                "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"fail\",\"arguments\":{}}}"),
            HttpResponse.BodyHandlers.ofString());
    JsonNode result = JSON.readTree(failure.body()).path("result");
    assertTrue(result.path("isError").asBoolean());
    assertTrue(result.path("content").get(0).path("text").asText().contains("Verified tool error"));
    HttpResponse<String> notification =
        client.send(
            request("/mcp", "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"),
            HttpResponse.BodyHandlers.ofString());
    assertEquals(202, notification.statusCode());
  }

  @Test
  public void supportsParallelRequestsAndProxyEndpoints() throws Exception {
    List<CompletableFuture<HttpResponse<String>>> responses = new ArrayList<>();
    for (int i = 0; i < 24; i++) {
      String body =
          "{\"jsonrpc\":\"2.0\",\"id\":"
              + i
              + ",\"method\":\"tools/call\",\"params\":{\"name\":\"echo\",\"arguments\":{\"value\":\"request-"
              + i
              + "\"}}}";
      responses.add(client.sendAsync(request("/mcp", body), HttpResponse.BodyHandlers.ofString()));
    }
    for (int i = 0; i < responses.size(); i++) {
      HttpResponse<String> response = responses.get(i).join();
      assertEquals(200, response.statusCode());
      assertEquals(
          "request-" + i,
          JSON.readTree(response.body())
              .path("result")
              .path("content")
              .get(0)
              .path("text")
              .asText());
    }
    HttpResponse<String> tools =
        client.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/api/tools"))
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build(),
            HttpResponse.BodyHandlers.ofString());
    assertEquals(200, tools.statusCode());
    assertEquals(2, JSON.readTree(tools.body()).size());
    HttpResponse<String> echo =
        client.send(
            request(
                "/api/execute", "{\"toolName\":\"echo\",\"arguments\":{\"value\":\"proxy-ok\"}}"),
            HttpResponse.BodyHandlers.ofString());
    assertEquals("proxy-ok", JSON.readTree(echo.body()).path("result").asText());
  }

  @Test
  public void keepsLegacySseResponsesWorking() throws Exception {
    HttpResponse<java.io.InputStream> stream =
        client.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/sse"))
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build(),
            HttpResponse.BodyHandlers.ofInputStream());
    assertEquals(200, stream.statusCode());
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream.body()))) {
      assertEquals("event: endpoint", reader.readLine());
      String path = reader.readLine().substring("data: ".length());
      assertEquals("", reader.readLine());
      HttpResponse<String> response =
          client.send(
              request(path, "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/list\"}"),
              HttpResponse.BodyHandlers.ofString());
      assertEquals(202, response.statusCode());
      assertEquals("event: message", reader.readLine());
      assertEquals(
          2,
          JSON.readTree(reader.readLine().substring("data: ".length()))
              .path("result")
              .path("tools")
              .size());
    }
  }
}
