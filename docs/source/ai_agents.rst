===================================
Using bdshare with AI Agents (MCP)
===================================

bdshare ships a `Model Context Protocol <https://modelcontextprotocol.io/>`_ (MCP)
server so AI agents running in **another program** — Claude Desktop, Claude Code, or
any other MCP-compatible client — can call live DSE data as tools, without you writing
any glue code.

.. contents:: On This Page
   :local:
   :depth: 2

----

Install
=======

.. code-block:: bash

    pip install "bdshare[mcp]"

Run
===

.. code-block:: bash

    bdshare-mcp
    # or
    python -m bdshare.mcp_server

By default it speaks MCP over stdio, which is what desktop/CLI agent clients expect.

Connect it to a client
=======================

Claude Code
-----------

.. code-block:: bash

    claude mcp add bdshare -- bdshare-mcp

Claude Desktop
--------------

Add to ``claude_desktop_config.json``:

.. code-block:: json

    {
      "mcpServers": {
        "bdshare": {
          "command": "bdshare-mcp"
        }
      }
    }

Any other MCP client is configured the same way — point it at the ``bdshare-mcp``
command (or ``python -m bdshare.mcp_server``), stdio transport.

What the agent gets
====================

The server exposes 15 tools covering the same data described in :doc:`usage`:

- ``market_status`` — wraps ``get_market_status()``
- ``market_summary`` — wraps ``get_market_info()``
- ``market_summary_range`` — wraps ``get_market_info_more_data(start, end, code?)``
- ``market_depth`` — wraps ``get_market_depth_data(symbol)``
- ``latest_pe_ratios`` — wraps ``get_latest_pe()``
- ``top_ten_gainers_losers`` — wraps ``get_top_ten_gainers_losers(limit?)``
- ``top_twenty_shares`` — wraps ``get_top_twenty_shares(limit?)``
- ``company_info`` — wraps ``get_company_info(symbol)``
- ``current_trades`` — wraps ``get_current_trade_data(symbol?)``
- ``dsex_index`` — wraps ``get_dsex_data(symbol?)``
- ``trading_codes`` — wraps ``get_current_trading_code()``
- ``historical_data`` — wraps ``get_historical_data(start, end, code?)``
- ``basic_historical_data`` — wraps ``get_basic_historical_data(start, end, code?)``
- ``news`` — wraps ``get_news(news_type?, code?)``
- ``agm_news`` — wraps ``get_agm_news()``

Each tool returns JSON — ``DataFrame`` results are converted to lists of row records
(``df.to_dict(orient="records")``) — and a ``BDShareError`` (bad symbol, DSE outage,
parse failure) surfaces as a clean tool error message instead of a raw traceback.

Notes for agent use
====================

.. warning::

   **No caching in the MCP server itself.** Every tool call scrapes dsebd.org live.
   If your agent calls the same tool repeatedly in one turn (e.g. checking a price
   several times), consider fronting it with the :class:`BDShare` client's caching in
   a custom wrapper — the bundled server intentionally stays stateless and simple.

.. warning::

   **Rate limits are the agent's responsibility.** The ``BDShare`` OOP client has a
   built-in 5 calls/second limiter; the MCP tools call the plain module-level
   functions, which don't. Avoid tight loops of tool calls.

Source: ``bdshare/mcp_server.py`` — a plain
`FastMCP <https://github.com/modelcontextprotocol/python-sdk>`_ server, easy to fork if
you want a different tool surface (e.g. fewer tools, added caching, or a subset scoped
to a specific agent).

Writing your own tool wrapper
==============================

If you'd rather integrate bdshare into an existing agent program without MCP — plain
OpenAI/Anthropic function-calling, LangChain tools, or a custom framework — the same
pattern the MCP server uses works anywhere: call the function, convert the
``DataFrame`` to records, and catch ``BDShareError``.

.. code-block:: python

    from bdshare import get_current_trade_data, BDShareError

    def get_current_trades_tool(symbol: str | None = None) -> list[dict]:
        """Tool function an agent framework can call directly."""
        try:
            df = get_current_trade_data(symbol)
        except BDShareError as e:
            return {"error": str(e)}
        return df.to_dict(orient="records")

Expose that as a tool with whatever schema your framework expects (OpenAI function
calling, Anthropic tool use, LangChain ``@tool``, etc.) — the docstring and type hints
above are enough to hand-write the JSON schema most frameworks require.
