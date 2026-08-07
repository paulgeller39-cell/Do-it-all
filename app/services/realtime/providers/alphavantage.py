"""
AlphaVantage poller scaffold.
Polls AlphaVantage for the latest 1min time series (or analogous endpoint) and publishes
new bars to Redis stream: realtime:{symbol}:kline

This is rate-limited by AlphaVantage — keep poll_interval high for many symbols.
"""
import os
import aiohttp
import asyncio
import logging
import time
import json

LOG = logging.getLogger("realtime.alphavantage")

BASE = "https://www.alphavantage.co/query"

async def _safe_xadd(r, stream, data):
    try:
        await r.xadd(stream, data)
    except Exception:
        LOG.exception("Failed to xadd to %s", stream)


async def fetch_intraday(session, symbol, api_key):
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": "1min",
        "outputsize": "compact",
        "apikey": api_key,
    }
    async with session.get(BASE, params=params, timeout=30) as resp:
        return await resp.json()


async def run(redis_client, symbols, api_key=None, poll_interval=60, enrich_fn=None):
    if not api_key:
        LOG.info("AlphaVantage API key not provided — AlphaVantage poller disabled")
        return

    if not symbols:
        LOG.info("No symbols configured for AlphaVantage poller — exiting")
        return

    last_seen = {s: None for s in symbols}

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for symbol in symbols:
                    try:
                        payload = await fetch_intraday(session, symbol, api_key)
                        # AlphaVantage response contains 'Time Series (1min)' key
                        ts_key = next((k for k in payload.keys() if "Time Series" in k), None)
                        if not ts_key:
                            LOG.debug("No time series for %s: %s", symbol, payload)
                            continue
                        series = payload.get(ts_key, {})
                        # series is a dict of timestamp -> data
                        for ts in sorted(series.keys()):
                            if last_seen[symbol] and ts <= last_seen[symbol]:
                                continue
                            bar = series[ts]
                            data = {
                                "symbol": symbol,
                                "ts": ts,
                                "open": bar.get("1. open"),
                                "high": bar.get("2. high"),
                                "low": bar.get("3. low"),
                                "close": bar.get("4. close"),
                                "volume": bar.get("5. volume"),
                            }

                            # Optional enrichment
                            if enrich_fn:
                                try:
                                    enriched = await enrich_fn(data)
                                    if enriched:
                                        data["enriched"] = enriched
                                except Exception:
                                    LOG.exception("OpenAI enrichment failed for alphavantage data")

                            stream = f"realtime:{symbol}:kline"
                            await _safe_xadd(redis_client, stream, {k: str(v) for k, v in data.items() if v is not None})
                            last_seen[symbol] = ts
                    except Exception:
                        LOG.exception("Error polling AlphaVantage for %s", symbol)
                    # Respect AlphaVantage rate limits — simple sleep between symbols
                    await asyncio.sleep(max(1, poll_interval / max(len(symbols), 1)))
                # After iterating symbols sleep a bit
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                LOG.info("AlphaVantage poller cancelled")
                break
            except Exception:
                LOG.exception("AlphaVantage poller error — sleeping 10s")
                await asyncio.sleep(10)
