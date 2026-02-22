Below is the **official, comprehensive API documentation** and reference material from Alpaca Markets that you should give to your coding agent. It covers both the **core API (Manual API)** and the **Model Context Protocol (MCP) / MCP Server** integration. This material will allow them to design an efficient architecture that stays within rate limits and avoids bans.

---

# 📘 Official Alpaca API Documentation Links

## 1) Alpaca Core API (Trading, Data, Orders, Accounts)

This is the **primary API documentation** for all aspects of trading, market data, orders, positions, accounts, etc.

**API Reference & Docs**
🔗 [https://docs.alpaca.markets/](https://docs.alpaca.markets/) — Main documentation portal for all Alpaca APIs. ([Alpaca API Docs][1])

Within these docs, your agent should focus on the following areas:

### a. **Trading API (REST / Orders / Accounts)**

* Submit orders (market, limit, stop, trailing)
* Cancel / update orders
* Manage positions
* Get account settings & balances

Includes full reference for endpoints like `/v2/orders`, `/v2/positions`, `/v2/account`, etc. ([Alpaca API Docs][1])

### b. **Market Data API**

* Real-time data via WebSocket
* Historical bar data
* Quote and trade streams

Documented under **Market Data API** docs — includes both REST and WebSocket feeds. ([Alpaca API Docs][2])

### c. **WebSocket & SSE Streaming**

For efficient live data feeds (quotes, trades, fills, order updates) — essential to reduce REST polling and avoid hitting rate limits. ([Alpaca API Docs][3])

### d. **SDKs and Sample Code**

SDKs are available in:

* Python (`alpaca-py`)
* JavaScript / Node (`@alpacahq/alpaca-trade-api`)
* Go, C#, etc.
  Your agent should use these native libraries where possible to avoid reinventing HTTP clients. ([npm][4])

---

## 2) MCP Server / MCP Interface

**Model Context Protocol (MCP)** is a structured way for external tools (like AI, coding agents, or CLI tools) to access the Alpaca API without writing custom integration logic. It can be seen as an abstraction layer on top of the core API.

**Alpaca MCP Server Docs**
🔗 [https://docs.alpaca.markets/docs/alpaca-mcp-server](https://docs.alpaca.markets/docs/alpaca-mcp-server) — Detailed documentation for Alpaca’s MCP Server. ([Alpaca API Docs][5])

### MCP Server Key Features

MCP Server exposes *pre-defined functions* that encapsulate trading, market data, and portfolio endpoints in a standardized protocol (Model Context Protocol) for AI or tool integrations. ([Alpaca API Docs][5])

Examples include:

* `get_account_info`
* `get_open_position`
* `get_stock_bars`
* `place_stock_order`
* `cancel_all_orders`
  (and ~40+ other functions) ([Alpaca API Docs][5])

### MCP Use Cases

* Natural language trading interfaces
* AI decision support
* Automated assistant pipelines

Your coding agent should use MCP as **an abstraction layer** *only if required* for connected tools (e.g., ChatGPT plugins, Claude, IDE integrations). For core bot logic, the raw REST + WebSocket architecture is still standard.

---

## 3) Additional Resources & Tools

### Official GitHub Specifications

OpenAPI / Swagger specs exist for the Alpaca APIs. These provide a **machine-readable API spec** useful for automatic client generation:

* Alpaca docs repository contains OAS specs for REST endpoints. ([Alpaca Community Forum][6])

### SDK Examples

* Python: [https://docs.alpaca.markets/docs/alpaca-py](https://docs.alpaca.markets/docs/alpaca-py)
  ("alpaca-py" is the recommended Python client) ([Alpaca API Docs][1])
* Node.js client: `@alpacahq/alpaca-trade-api` with implicit documentation links to the official REST docs. ([npm][4])

---

# 🛠 Architecture Guidance for Your Coding Agent

To **avoid rate limits and bans**, here are the architectural recommendations your coding agent should follow. They are consistent with typical professional designs:

---

## ✅ 1. Use WebSockets for Real-Time Feeds

Instead of REST polling:

* Market data
* Order updates
* Trade confirmations

Streaming reduces REST calls dramatically.

**Best practice:** Connect once at startup → maintain state locally → reconcile only on significant events.

---

## ✅ 2. Cache & Debounce REST Requests

For non-critical data (e.g., asset lists, portfolio lookups):

* Cache results
* Only refresh on expiration

---

## ✅ 3. Batch & Queue Orders

Instead of sending individual REST calls for every signal:

* Batch logic orders
* Use asynchronous queuing
* Reduce unnecessary calls

---

## ✅ 4. Respect and Monitor Rate Limits

Apica docs specify rate limits per endpoint — architect the client to:

* Detect HTTP 429s
* Back off intelligently
* Retry with exponential backoff

This prevents throttling and bans.

---

## ✅ 5. Use MCP Only for AI/Client Integration

If using AI tools like *Claude*, *ChatGPT*, *VS Code plugins*, use Alpaca’s MCP Server to *abstract authentication & function calls* without building multiple web clients yourself. ([Alpaca API Docs][5])

---

## ⚠️ 6. Avoid Multiple Free Accounts

if shard across multiple free API accounts to evade rate limits . This will:

* Violates terms
* Fragmented portfolio state
* Harder reconciliation

you have to manage multiple accounts carefully and use second account if first account is rate limited .
---

# 📎 Summary of Required URLs to Share With Your Agent

| Purpose                  | Link                                                                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| Main API Reference       | [https://docs.alpaca.markets/](https://docs.alpaca.markets/) ([Alpaca API Docs][1])                                                     |
| Market Data API          | [https://docs.alpaca.markets/docs/about-market-data-api](https://docs.alpaca.markets/docs/about-market-data-api) ([Alpaca API Docs][2]) |
| MCP Server Documentation | [https://docs.alpaca.markets/docs/alpaca-mcp-server](https://docs.alpaca.markets/docs/alpaca-mcp-server) ([Alpaca API Docs][5])         |
| SDK Resources            | Linked inside Alpaca docs (Python, Node, etc.) ([Alpaca API Docs][1])                                                                   |
| GitHub API Spec          | Available via Alpaca’s docs repo (OpenAPI/OAS) ([Alpaca Community Forum][6])                                                            |

---

If you want, I can also generate a **printable API reference sheet** (with example endpoints and authentication patterns) specifically tailored for an automated trading architecture.

[1]: https://docs.alpaca.markets/?utm_source=chatgpt.com "Alpaca API Docs"
[2]: https://docs.alpaca.markets/docs/about-market-data-api?utm_source=chatgpt.com "About Market Data API"
[3]: https://docs.alpaca.markets/docs/alpaca-api-platform?utm_source=chatgpt.com "Alpaca API Platform"
[4]: https://www.npmjs.com/package/%40alpacahq/alpaca-trade-api?utm_source=chatgpt.com "@alpacahq/alpaca-trade-api - npm"
[5]: https://docs.alpaca.markets/docs/alpaca-mcp-server?utm_source=chatgpt.com "Alpaca's MCP Server"
[6]: https://forum.alpaca.markets/t/alpaca-apis-swagger-file/5586?utm_source=chatgpt.com "Alpaca APIs Swagger File - Getting Started with Alpaca - Alpaca Community Forum"
