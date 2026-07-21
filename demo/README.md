# bdshare Demos

Three demo apps live here:

- **[`streamlit/`](streamlit/)** (recommended for a quick tour) — a full-feature
  showcase of the library in pure Python: live trading data, historical
  charts with technical indicators, market movers, news, portfolio
  tracking, live tick polling, and the tool surface exposed to AI agents
  via MCP.
- **[`node/`](node/)** — the same feature set, but architected as four
  independent services to show bdshare being consumed from **outside
  Python**: an Express UI, a FastAPI backend, `bdshare-mcp` reached over
  HTTP, and `bdshare-stream`'s WebSocket ticks — the Node/Express layer
  never imports bdshare itself.
- **[`flask/`](flask/)** — a small Flask + Plotly.js app focused on one
  thing: interactive candlestick/line/OHLC charts from
  `get_basic_historical_data()`.

All three are built with `demo/docker-compose.yml`, whose Python-service
build **context is the repo root** (`..` from `demo/`) — that's what lets
those images install `bdshare` from local source instead of PyPI, so
unreleased features (`bdshare.indicators`, `bdshare.portfolio`,
`bdshare.stream`, the MCP server) all work.

```sh
cd demo
docker compose up --build          # all three demos at once
# or just one:
docker compose up --build streamlit
docker compose up --build node node-api mcp stream
docker compose up --build app
```

## Streamlit demo (full feature showcase, pure Python)

**http://localhost:8501/** after `docker compose up --build streamlit`.

### Run locally (without Docker)

From the **repo root**:

```sh
pip install -e ".[ta,stream]"
pip install -r demo/streamlit/requirements.txt
streamlit run demo/streamlit/streamlit_app.py
```

### What it showcases

| Tab | bdshare features |
|---|---|
| Live Trading | `get_current_trade_data()`, `get_dsex_data()` |
| Historical & Indicators | `get_basic_historical_data()` + `bdshare.indicators` (SMA/EMA/RSI/MACD/Bollinger) |
| Market Movers | `get_market_info()`, `get_top_ten_gainers_losers()`, `get_top_twenty_shares()`, `get_latest_pe()`, `get_market_depth_data()`, `get_company_info()` |
| News | `get_news()` unified dispatcher (all/agm/corporate/psn) |
| Portfolio | `bdshare.portfolio.Portfolio` — cost basis, live valuation, P&L |
| Live Ticks | poll-and-diff live prices, plus instructions for running the real `bdshare-stream` WebSocket server |
| AI Agents (MCP) | interactive tool calls + how to connect Claude Desktop/Code via `bdshare-mcp` |

## Node.js demo (cross-language integration showcase)

Four services, run together:

| Service | What it is | Reachable at |
|---|---|---|
| `node` | Express UI — the only thing the browser talks to | http://localhost:3000/ |
| `node-api` | FastAPI backend wrapping bdshare as JSON REST (Node can't `import bdshare`) | http://localhost:8000/ (optional, for direct API testing) |
| `mcp` | `bdshare-mcp --transport streamable-http` — Node speaks MCP to it via `@modelcontextprotocol/sdk`, the same way an AI agent would | internal only |
| `stream` | `bdshare-stream` — Node relays its WebSocket ticks to the browser at `/ws/ticks` | internal only |

```sh
docker compose up --build node node-api mcp stream
```

Then open **http://localhost:3000/**.

### Run locally (without Docker)

Three processes, from the **repo root**:

```sh
# 1. FastAPI backend
pip install -e ".[ta,mcp,stream]"
uvicorn main:app --app-dir demo/node/api --port 8000

# 2. MCP server over HTTP (separate terminal)
bdshare-mcp --transport streamable-http --host 0.0.0.0 --port 8001

# 3. Tick stream (separate terminal)
bdshare-stream --host 0.0.0.0 --port 8765 --symbols GP,ACI

# 4. Node server (separate terminal)
cd demo/node/server
npm install
API_BASE_URL=http://localhost:8000 MCP_URL=http://localhost:8001/mcp STREAM_WS_URL=ws://localhost:8765 npm start
```

### What it showcases

Same tabs as the Streamlit demo (Live Trading, Historical & Indicators,
Market Movers, News, Portfolio, Live Ticks, AI Agents), but built to
demonstrate three distinct ways a **non-Python program** can consume
bdshare:

1. **REST** — `node-api` (`demo/node/api/main.py`) turns bdshare functions
   into JSON endpoints; Express proxies to it under `/api/*`.
2. **MCP over HTTP** — `bdshare/mcp_server.py` gained a
   `--transport streamable-http` mode for exactly this: a network-reachable
   MCP server for programs that aren't a stdio-spawning desktop agent.
   Express's `lib/mcpClient.js` calls it with the official
   `@modelcontextprotocol/sdk` — the "AI Agents (MCP)" tab is a real MCP
   client, not a REST wrapper pretending to be one.
3. **WebSocket** — `lib/tickRelay.js` connects to `bdshare-stream` once,
   server-side, and re-broadcasts to any number of browser clients on
   `/ws/ticks`, so the browser only ever talks to one origin.

Charting uses [lightweight-charts](https://tradingview.github.io/lightweight-charts/)
(candlesticks + indicator overlays) and [Chart.js](https://www.chartjs.org/)
(portfolio allocation pie), both via CDN — no frontend build step.

## Flask demo (candlestick charts)

**http://localhost:9999/** after `docker compose up --build app`.

### Run locally (without Docker)

```sh
cd demo/flask
pip install -r requirements.txt
python app.py
```

## Notes

- `demo/flask/requirements.txt` installs `bdshare` from PyPI, so that demo
  runs against the latest *released* version, not your local working copy —
  swap that line for `-e ../..` if you need unreleased changes there too.
  The Streamlit and Node demos always build from local source (see above),
  so this only matters for the Flask app.
- All data is scraped live from `dsebd.org` on each request. The demos
  cache short-TTL where it makes sense, but repeated interaction still hits
  the network — please respect DSE's terms of service.
- The Node demo's charting libraries load from CDN (unpkg, jsDelivr) — it
  needs outbound internet access beyond just reaching dsebd.org.
