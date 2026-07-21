// bdshare Node.js demo — plain ES modules, no bundler.

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

async function getJSON(url) {
  const res = await fetch(url);
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || `Request failed: ${res.status}`);
  return body;
}

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || `Request failed: ${res.status}`);
  return body;
}

function renderTable(container, rows) {
  if (!rows || rows.length === 0) {
    container.innerHTML = '<p class="muted">No data.</p>';
    return;
  }
  const cols = Object.keys(rows[0]);
  const thead = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${cols
          .map((c) => `<td>${row[c] === null || row[c] === undefined ? "" : row[c]}</td>`)
          .join("")}</tr>`
    )
    .join("")}</tbody>`;
  container.innerHTML = `<table>${thead}${tbody}</table>`;
}

function renderError(container, err) {
  container.innerHTML = `<p class="error">${err.message}</p>`;
}

function populateSelect(select, symbols, { placeholder } = {}) {
  select.innerHTML = "";
  if (placeholder !== undefined) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    select.appendChild(opt);
  }
  for (const s of symbols) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    select.appendChild(opt);
  }
}

function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------------------------------------------------------------------------
// Shared state: symbol list, loaded once
// ---------------------------------------------------------------------------

let ALL_SYMBOLS = [];

async function loadSymbols() {
  try {
    const codes = await getJSON("/api/trading/codes");
    ALL_SYMBOLS = codes.map((r) => r.symbol).sort();
  } catch {
    ALL_SYMBOLS = ["GP", "ACI", "SQURPHARMA", "BEXIMCO"];
  }
  populateSelect(document.getElementById("live-symbol"), ALL_SYMBOLS, { placeholder: "All" });
  populateSelect(document.getElementById("hist-symbol"), ALL_SYMBOLS);
  populateSelect(document.getElementById("depth-symbol"), ALL_SYMBOLS);
  populateSelect(document.getElementById("news-symbol"), ALL_SYMBOLS, { placeholder: "All" });
  populateSelect(document.getElementById("pf-symbol"), ALL_SYMBOLS);
  populateSelect(document.getElementById("mcp-symbol"), ALL_SYMBOLS);
  if (ALL_SYMBOLS.includes("GP")) {
    document.getElementById("hist-symbol").value = "GP";
    document.getElementById("depth-symbol").value = "GP";
    document.getElementById("pf-symbol").value = "GP";
    document.getElementById("mcp-symbol").value = "GP";
  }
}

async function loadMarketStatus() {
  const el = document.getElementById("market-status");
  try {
    const { status } = await getJSON("/api/market/status");
    el.textContent = status;
  } catch (err) {
    el.textContent = "unavailable";
  }
}

// ---------------------------------------------------------------------------
// Tab: Live Trading
// ---------------------------------------------------------------------------

async function loadLiveTrading() {
  const symbol = document.getElementById("live-symbol").value;
  const container = document.getElementById("live-table");
  try {
    const rows = await getJSON(`/api/trading/current${symbol ? `?symbol=${symbol}` : ""}`);
    renderTable(container, rows);
  } catch (err) {
    renderError(container, err);
  }

  const dsexContainer = document.getElementById("dsex-table");
  try {
    renderTable(dsexContainer, await getJSON("/api/trading/dsex"));
  } catch (err) {
    renderError(dsexContainer, err);
  }
}

document.getElementById("live-refresh").addEventListener("click", loadLiveTrading);
document.getElementById("live-symbol").addEventListener("change", loadLiveTrading);

// ---------------------------------------------------------------------------
// Tab: Historical & Indicators
// ---------------------------------------------------------------------------

let histChart, histSeries, smaSeries, rsiChart, rsiSeries;

function ensureCharts() {
  if (histChart) return;
  histChart = LightweightCharts.createChart(document.getElementById("hist-chart"), {
    layout: { background: { color: "transparent" }, textColor: "#888" },
    grid: { vertLines: { color: "#8883" }, horzLines: { color: "#8883" } },
    autoSize: true,
  });
  histSeries = histChart.addCandlestickSeries({ upColor: "#16a34a", downColor: "#dc2626", borderVisible: false });
  smaSeries = histChart.addLineSeries({ color: "#f59e0b", lineWidth: 1 });

  rsiChart = LightweightCharts.createChart(document.getElementById("rsi-chart"), {
    layout: { background: { color: "transparent" }, textColor: "#888" },
    grid: { vertLines: { color: "#8883" }, horzLines: { color: "#8883" } },
    autoSize: true,
  });
  rsiSeries = rsiChart.addLineSeries({ color: "#2563eb", lineWidth: 1 });
}

async function loadHistorical() {
  ensureCharts();
  const symbol = document.getElementById("hist-symbol").value;
  const start = document.getElementById("hist-start").value;
  const end = document.getElementById("hist-end").value;
  const wantSma = document.getElementById("hist-sma").checked;
  const wantRsi = document.getElementById("hist-rsi").checked;
  const indicators = [wantSma && "sma", wantRsi && "rsi"].filter(Boolean).join(",");

  const qs = new URLSearchParams({ start, end, symbol, ...(indicators ? { indicators } : {}) });
  try {
    const rows = await getJSON(`/api/trading/historical?${qs}`);
    histSeries.setData(
      rows.map((r) => ({ time: r.date, open: r.open, high: r.high, low: r.low, close: r.close }))
    );
    smaSeries.setData(
      wantSma
        ? rows.filter((r) => r.sma_20 !== null).map((r) => ({ time: r.date, value: r.sma_20 }))
        : []
    );
    rsiSeries.setData(
      wantRsi
        ? rows.filter((r) => r.rsi_14 !== null).map((r) => ({ time: r.date, value: r.rsi_14 }))
        : []
    );
    histChart.timeScale().fitContent();
    rsiChart.timeScale().fitContent();
  } catch (err) {
    document.getElementById("hist-chart").innerHTML = `<p class="error">${err.message}</p>`;
  }
}

document.getElementById("hist-load").addEventListener("click", loadHistorical);
document.getElementById("hist-start").value = todayISO(-180);
document.getElementById("hist-end").value = todayISO();

// ---------------------------------------------------------------------------
// Tab: Market Movers
// ---------------------------------------------------------------------------

async function loadMovers() {
  const infoEl = document.getElementById("market-info");
  try {
    const rows = await getJSON("/api/market/info");
    renderTable(infoEl, rows.slice(-10));
  } catch (err) {
    renderError(infoEl, err);
  }

  const topTenEl = document.getElementById("top-ten");
  try {
    renderTable(topTenEl, await getJSON("/api/market/movers/top-ten?limit=10"));
  } catch (err) {
    renderError(topTenEl, err);
  }

  const topTwentyEl = document.getElementById("top-twenty");
  try {
    renderTable(topTwentyEl, await getJSON("/api/market/movers/top-twenty?limit=20"));
  } catch (err) {
    renderError(topTwentyEl, err);
  }

  const peEl = document.getElementById("pe-table");
  try {
    const rows = await getJSON("/api/market/pe");
    renderTable(peEl, rows.slice(0, 15));
  } catch (err) {
    renderError(peEl, err);
  }

  await loadDepthAndCompany();
}

async function loadDepthAndCompany() {
  const symbol = document.getElementById("depth-symbol").value;
  if (!symbol) return;

  const depthEl = document.getElementById("depth-table");
  try {
    renderTable(depthEl, await getJSON(`/api/market/depth/${symbol}`));
  } catch (err) {
    renderError(depthEl, err);
  }

  const companyEl = document.getElementById("company-table");
  try {
    const tables = await getJSON(`/api/company/${symbol}`);
    renderTable(companyEl, tables[0]);
  } catch (err) {
    renderError(companyEl, err);
  }
}

document.getElementById("depth-symbol").addEventListener("change", loadDepthAndCompany);

// ---------------------------------------------------------------------------
// Tab: News
// ---------------------------------------------------------------------------

async function loadNews() {
  const type = document.getElementById("news-type").value;
  const symbol = document.getElementById("news-symbol").value;
  const container = document.getElementById("news-table");
  const qs = new URLSearchParams({ news_type: type, ...(symbol ? { code: symbol } : {}) });
  try {
    renderTable(container, await getJSON(`/api/news?${qs}`));
  } catch (err) {
    renderError(container, err);
  }
}

document.getElementById("news-load").addEventListener("click", loadNews);

// ---------------------------------------------------------------------------
// Tab: Portfolio (client-held positions, server-computed valuation)
// ---------------------------------------------------------------------------

const portfolio = []; // [{symbol, quantity, avg_cost}]
let pfChart;

async function refreshPortfolio() {
  const tableEl = document.getElementById("pf-table");
  const summaryEl = document.getElementById("pf-summary");
  const chartEl = document.getElementById("pf-chart");

  if (portfolio.length === 0) {
    tableEl.innerHTML = '<p class="muted">Add a position above to see live valuation and P&amp;L.</p>';
    summaryEl.innerHTML = "";
    chartEl.innerHTML = "";
    return;
  }

  try {
    const { valuation, summary } = await postJSON("/api/portfolio/valuation", portfolio);
    renderTable(tableEl, valuation);

    const pnlClass = summary.total_pnl >= 0 ? "up" : "down";
    summaryEl.innerHTML = `
      <div class="metric"><div class="label">Total cost</div><div class="value">${summary.total_cost.toFixed(2)}</div></div>
      <div class="metric"><div class="label">Total value</div><div class="value">${summary.total_value.toFixed(2)}</div></div>
      <div class="metric"><div class="label">Total P&amp;L</div><div class="value ${pnlClass}">${summary.total_pnl.toFixed(2)} (${summary.total_pnl_pct.toFixed(2)}%)</div></div>
    `;

    const valued = valuation.filter((v) => v.market_value !== null);
    if (!pfChart) {
      pfChart = new Chart(chartEl.appendChild(document.createElement("canvas")), {
        type: "pie",
        data: { labels: [], datasets: [{ data: [] }] },
      });
    }
    pfChart.data.labels = valued.map((v) => v.symbol);
    pfChart.data.datasets[0].data = valued.map((v) => v.market_value);
    pfChart.update();
  } catch (err) {
    renderError(tableEl, err);
  }
}

document.getElementById("pf-add").addEventListener("click", () => {
  const symbol = document.getElementById("pf-symbol").value;
  const quantity = Number(document.getElementById("pf-qty").value);
  const avg_cost = Number(document.getElementById("pf-cost").value);
  if (!symbol || !quantity) return;

  const existing = portfolio.find((p) => p.symbol === symbol);
  if (existing) {
    const totalQty = existing.quantity + quantity;
    existing.avg_cost = (existing.quantity * existing.avg_cost + quantity * avg_cost) / totalQty;
    existing.quantity = totalQty;
  } else {
    portfolio.push({ symbol, quantity, avg_cost });
  }
  refreshPortfolio();
});

// ---------------------------------------------------------------------------
// Tab: Live Ticks (WebSocket, relayed by Express from bdshare-stream)
// ---------------------------------------------------------------------------

function connectTicks() {
  const statusEl = document.getElementById("ticks-status");
  const tableEl = document.getElementById("ticks-table");
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${location.host}/ws/ticks`);
  let previous = {};

  ws.addEventListener("open", () => {
    statusEl.textContent = "connected";
  });
  ws.addEventListener("close", () => {
    statusEl.textContent = "disconnected — retrying…";
    setTimeout(connectTicks, 3000);
  });
  ws.addEventListener("error", () => ws.close());
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    const rows = msg.data || [];
    const changedSymbols = new Set(
      rows.filter((r) => JSON.stringify(previous[r.symbol]) !== JSON.stringify(r)).map((r) => r.symbol)
    );
    for (const r of rows) previous[r.symbol] = r;

    if (rows.length === 0) return;
    const cols = Object.keys(rows[0]);
    tableEl.innerHTML = `<table><thead><tr>${cols
      .map((c) => `<th>${c}</th>`)
      .join("")}</tr></thead><tbody>${rows
      .map(
        (row) =>
          `<tr class="${changedSymbols.has(row.symbol) ? "changed" : ""}">${cols
            .map((c) => `<td>${row[c] ?? ""}</td>`)
            .join("")}</tr>`
      )
      .join("")}</tbody></table>`;
    statusEl.textContent = `${msg.type} — last update ${new Date().toLocaleTimeString()}`;
  });
}

// ---------------------------------------------------------------------------
// Tab: AI Agents (MCP)
// ---------------------------------------------------------------------------

async function loadMcpTools() {
  const select = document.getElementById("mcp-tool");
  try {
    const tools = await getJSON("/mcp/tools");
    select.innerHTML = "";
    for (const t of tools) {
      const opt = document.createElement("option");
      opt.value = t.name;
      opt.textContent = t.name;
      select.appendChild(opt);
    }
  } catch (err) {
    select.innerHTML = `<option>unavailable</option>`;
  }
}

document.getElementById("mcp-call").addEventListener("click", async () => {
  const name = document.getElementById("mcp-tool").value;
  const symbol = document.getElementById("mcp-symbol").value;
  const resultEl = document.getElementById("mcp-result");
  resultEl.textContent = "Calling…";

  // Tools that need a symbol argument; others are called with no args.
  const symbolArgTools = new Set(["market_depth", "company_info", "current_trades", "dsex_index", "historical_data", "basic_historical_data"]);
  const args = symbolArgTools.has(name) ? { symbol } : {};

  try {
    const result = await postJSON("/mcp/call", { name, arguments: args });
    resultEl.textContent = JSON.stringify(result, null, 2);
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

(async function init() {
  await loadSymbols();
  await loadMarketStatus();
  await loadLiveTrading();
  await loadHistorical();
  await loadMovers();
  await loadNews();
  await loadMcpTools();
  connectTicks();
  setInterval(loadMarketStatus, 60_000);
})();
