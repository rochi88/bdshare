import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const MCP_URL = process.env.MCP_URL || "http://localhost:8001/mcp";

let clientPromise = null;

function getClient() {
  if (clientPromise) return clientPromise;
  clientPromise = (async () => {
    const transport = new StreamableHTTPClientTransport(new URL(MCP_URL));
    const client = new Client({ name: "bdshare-node-demo", version: "1.0.0" });
    await client.connect(transport);
    return client;
  })();
  // Drop the cached promise on failure so the next call retries instead of
  // being stuck with a permanently-rejected connection (useful since the MCP
  // service may not be up yet when this container starts).
  clientPromise.catch(() => {
    clientPromise = null;
  });
  return clientPromise;
}

export async function listTools() {
  const client = await getClient();
  const { tools } = await client.listTools();
  return tools;
}

export async function callTool(name, args) {
  const client = await getClient();
  return client.callTool({ name, arguments: args || {} });
}
