"""
Orchestrator for realtime connector providers.
- Starts Polygon websocket client (if POLYGON_API_KEY provided)
- Starts AlphaVantage poller for backfill/periodic data (if ALPHAVANTAGE_API_KEY provided)
- Optionally enriches messages using OpenAI if OPENAI_API_KEY is present

This is a scaffold for integration and not a production-ready implementation.
"""
import os
import asyncio
import logging
import signal

import redis.asyncio as aioredis

from providers import polygon, alphavantage, openai_enricher

LOG = logging.getLogger("realtime.connector")
logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTCUSD,ETHUSD").split(",") if s.strip()]

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_WS_URL = os.getenv("POLYGON_WS_URL", "wss://socket.polygon.io/stocks")

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
ALPHAVANTAGE_POLL_INTERVAL = int(os.getenv("ALPHAVANTAGE_POLL_INTERVAL", "60"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SHUTDOWN = False


def _on_signal():
    global SHUTDOWN
    SHUTDOWN = True


async def main():
    r = aioredis.from_url(REDIS_URL)

    enrich_fn = None
    if OPENAI_API_KEY:
        LOG.info("OpenAI key present — enabling enrichment")
        enrich_fn = lambda msg: openai_enricher.enrich(msg, api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    else:
        LOG.info("OpenAI key absent — enrichment disabled")

    tasks = []

    # Start Polygon websocket connector (ws-style)
    tasks.append(asyncio.create_task(
        polygon.run(redis_client=r, symbols=SYMBOLS, api_key=POLYGON_API_KEY, ws_url=POLYGON_WS_URL, enrich_fn=enrich_fn)
    ))

    # Start AlphaVantage poller
    tasks.append(asyncio.create_task(
        alphavantage.run(redis_client=r, symbols=SYMBOLS, api_key=ALPHAVANTAGE_API_KEY, poll_interval=ALPHAVANTAGE_POLL_INTERVAL, enrich_fn=enrich_fn)
    ))

    # Run until shutdown requested
    while not SHUTDOWN:
        await asyncio.sleep(0.5)

    LOG.info("Shutdown requested — cancelling providers")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await r.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _on_signal)
    try:
        loop.run_until_complete(main())
    except Exception:
        LOG.exception("Connector exited with exception")
    finally:
        loop.close()
