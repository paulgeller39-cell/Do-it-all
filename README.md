# Do-it-all
AI bot scaffold for realtime market ingestion and enrichment.

## Realtime connectors (feature/ai-platform-scaffold)
This branch adds a realtime connector scaffold for market data ingestion and enrichment.

Included connectors
- Polygon (WebSocket primary, requires POLYGON_API_KEY)
- Coinbase (public WebSocket, minimal support may already exist)
- AlphaVantage (REST poller for backfill, requires ALPHAVANTAGE_API_KEY)
- NewsAPI (REST headlines if NEWSAPI_KEY present)
- OpenAI (optional enrichment when OPENAI_API_KEY present)

Environment keys
- POLYGON_API_KEY: Polygon WebSocket auth key (do NOT commit)
- POLYGON_WS_URL: Polygon WS URL (default: wss://socket.polygon.io/stocks)
- ALPHAVANTAGE_API_KEY: AlphaVantage REST API key
- ALPHAVANTAGE_POLL_INTERVAL: Poll interval seconds (default: 60)
- OPENAI_API_KEY: OpenAI API key for optional enrichment
- OPENAI_API_URL: OpenAI API base URL
- OPENAI_MODEL: OpenAI model to use for enrichment
- REDIS_URL: Redis connection for publishing streams

How it publishes
- Redis Streams: realtime:{symbol}:trades and realtime:{symbol}:kline
- Optional Postgres persistence of 1m candles (DATABASE_URL required)

Quick start (on host)
1. Copy env example and set secrets (do NOT commit):
   cp env.example .env
   # edit .env: POLYGON_API_KEY, ALPHAVANTAGE_API_KEY, REDIS_URL, DATABASE_URL, OPENAI_API_KEY
2. Start with docker-compose:
   docker compose -f docker-compose.yml -f docker-compose.realtime.yml up -d --build
3. Check logs:
   docker compose logs -f realtime-connector
4. Verify messages in Redis:
   redis-cli XREAD BLOCK 0 STREAMS realtime:BTCUSD:trades 0

Notes
- No secrets are committed. Connectors auto-fallback to available providers.
- The Polygon connector uses websockets and will reconnect on failures.
- AlphaVantage is rate-limited — keep ALPHAVANTAGE_POLL_INTERVAL high for many symbols.
- See docs/realtime-deploy.md for full deployment & systemd example.
