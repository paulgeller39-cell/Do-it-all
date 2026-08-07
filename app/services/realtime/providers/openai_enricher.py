"""
OpenAI enrichment scaffold.
Calls the OpenAI HTTP API to produce a short enrichment string for a given event.
This is optional and only used if OPENAI_API_KEY is set.
"""
import os
import aiohttp
import asyncio
import logging
import json

LOG = logging.getLogger("realtime.openai")

OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")


async def enrich(event, api_key=None, model="gpt-4o-mini"):
    """
    Given a JSON-like event, ask OpenAI for a short label/summary.
    Returns a string or None on failure.
    """
    if not api_key:
        return None

    prompt = (
        "Summarize the following market event in one short sentence (symbol, signal, or notable data):\n\n"
        + json.dumps(event)
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0.2,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_API_URL, json=body, headers=headers, timeout=20) as resp:
                if resp.status != 200:
                    LOG.debug("OpenAI responded %s", await resp.text())
                    return None
                data = await resp.json()
                # Response parsing is approximate — adapt to API surface used
                choices = data.get("choices") or []
                if not choices:
                    return None
                text = choices[0].get("message", {}).get("content") or choices[0].get("text")
                return text.strip() if text else None
    except Exception:
        LOG.exception("OpenAI enrichment request failed")
        return None
