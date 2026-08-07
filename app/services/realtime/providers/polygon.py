"""
Polygon WebSocket connector scaffold.
Sends auth (if api_key provided) then subscribes to trade channels for symbols.
Publishes incoming trade events to Redis stream: realtime:{symbol}:trades

This is a minimal example — adapt subscribe/auth messages for your Polygon plan.
"""
import os
import json
import asyncio
import logging
import websockets

LOG = logging.getLogger("realtime.polygon")

async def _safe_xadd(r, stream, data):
    try:
        await r.xadd(stream, data)
    except Exception:
        LOG.exception("Failed to xadd to %s", stream)


async def run(redis_client, symbols, api_key=None, ws_url=None, enrich_fn=None):
    if not ws_url:
        ws_url = os.getenv("POLYGON_WS_URL", "wss://socket.polygon.io/stocks")

    if not symbols:
        LOG.info("No symbols configured for Polygon connector — exiting")
        return

    while True:
        try:
            LOG.info("Connecting to Polygon WS %s", ws_url)
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                # Authenticate if key provided (Polygon uses an "auth" action in many examples)
                if api_key:
                    auth_msg = {"action": "auth", "params": api_key}
                    await ws.send(json.dumps(auth_msg))
                    LOG.info("Sent Polygon auth message")

                # Subscribe to trade channels. Adjust channel names per your provider plan.
                sub_channels = [f"T.{s}" for s in symbols]
                sub_msg = {"action": "subscribe", "params": ",".join(sub_channels)}
                await ws.send(json.dumps(sub_msg))
                LOG.info("Subscribed to channels: %s", sub_channels)

                async for raw in ws:
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        LOG.debug("Non-JSON from Polygon: %s", raw)
                        continue

                    # Polygon sends various message types; here we try to map trade-like events
                    for ev in payload if isinstance(payload, list) else [payload]:
                        # Basic mapping — adapt fields as needed
                        symbol = ev.get("sym") or ev.get("S") or ev.get("ticker")
                        trade = {
                            "raw": json.dumps(ev),
                            "ts": str(int(ev.get("t", ev.get("timestamp", 0)))),
                        }
                        if symbol:
                            stream = f"realtime:{symbol}:trades"
                        else:
                            stream = "realtime:unknown:trades"

                        # Optional enrichment
                        if enrich_fn:
                            try:
                                enriched = await enrich_fn(ev)
                                if enriched:
                                    trade.update({"enriched": enriched})
                            except Exception:
                                LOG.exception("OpenAI enrichment failed")

                        await _safe_xadd(redis_client, stream, trade)
        except asyncio.CancelledError:
            LOG.info("Polygon connector task cancelled")
            break
        except Exception:
            LOG.exception("Polygon connector error — reconnecting in 5s")
            await asyncio.sleep(5)
