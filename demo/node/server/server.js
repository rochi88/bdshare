import express from "express";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { apiGet, apiPost, ApiError } from "./lib/apiClient.js";
import { listTools, callTool } from "./lib/mcpClient.js";
import { attachTickRelay } from "./lib/tickRelay.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;

const app = express();
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  res.render("index");
});

// ---------------------------------------------------------------------------
// REST proxy to the Python API (demo/node/api) — Node can't import bdshare
// directly, so every data route here is a thin passthrough.
// ---------------------------------------------------------------------------

function proxy(pathOrFn) {
  return async (req, res) => {
    try {
      const target = typeof pathOrFn === "function" ? pathOrFn(req) : pathOrFn;
      res.json(await apiGet(target));
    } catch (err) {
      res.status(err instanceof ApiError ? err.status : 502).json({ error: err.message });
    }
  };
}

app.get("/api/market/status", proxy("/market/status"));
app.get("/api/market/info", proxy("/market/info"));
app.get("/api/market/movers/top-ten", proxy((req) => `/market/movers/top-ten?limit=${req.query.limit || 10}`));
app.get("/api/market/movers/top-twenty", proxy((req) => `/market/movers/top-twenty?limit=${req.query.limit || 20}`));
app.get("/api/market/pe", proxy("/market/pe"));
app.get("/api/market/depth/:symbol", proxy((req) => `/market/depth/${encodeURIComponent(req.params.symbol)}`));
app.get("/api/company/:symbol", proxy((req) => `/company/${encodeURIComponent(req.params.symbol)}`));
app.get(
  "/api/trading/current",
  proxy((req) => `/trading/current${req.query.symbol ? `?symbol=${encodeURIComponent(req.query.symbol)}` : ""}`)
);
app.get(
  "/api/trading/dsex",
  proxy((req) => `/trading/dsex${req.query.symbol ? `?symbol=${encodeURIComponent(req.query.symbol)}` : ""}`)
);
app.get("/api/trading/codes", proxy("/trading/codes"));
app.get("/api/trading/historical", proxy((req) => `/trading/historical?${new URLSearchParams(req.query)}`));
app.get("/api/news", proxy((req) => `/news?${new URLSearchParams(req.query)}`));

app.post("/api/portfolio/valuation", async (req, res) => {
  try {
    res.json(await apiPost("/portfolio/valuation", req.body));
  } catch (err) {
    res.status(err instanceof ApiError ? err.status : 502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// MCP tool explorer — Node speaks MCP directly to bdshare-mcp, the way an
// AI agent (or any other program) would.
// ---------------------------------------------------------------------------

app.get("/mcp/tools", async (req, res) => {
  try {
    res.json(await listTools());
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.post("/mcp/call", async (req, res) => {
  try {
    const { name, arguments: args } = req.body;
    res.json(await callTool(name, args));
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

const server = http.createServer(app);
attachTickRelay(server);

server.listen(PORT, () => {
  console.log(`bdshare Node demo listening on http://localhost:${PORT}`);
});
