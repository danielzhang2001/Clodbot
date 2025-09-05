"""
Fetches and displays server stats of Clodbot.
"""

import os, json, asyncio, aiohttp, random

GIST_ID = os.getenv("GIST_ID")
GH_TOKEN = os.getenv("GH_TOKEN")

async def publish_stats(bot, every_seconds: int = 86400):
    # Publishes the number of servers and approx users to a public gist.
    if not GIST_ID or not GH_TOKEN:
        print("[stats] Missing GIST_ID or GH_TOKEN env var")
        return
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    async def push(session: aiohttp.ClientSession):
        payload = {
            "numServers": len(bot.guilds),
            "numUsers": sum((g.member_count or 0) for g in bot.guilds),
        }
        body = {"files": {"clodbot-stats.json": {"content": json.dumps(payload)}}}
        try:
            async with session.patch(url, json=body) as resp:
                if resp.status == 200:
                    print(f"[stats] Updated gist with {payload}")
                else:
                    text = await resp.text()
                    print(f"[stats] Failed ({resp.status}): {text}")
        except Exception as e:
            print(f"[stats] Exception: {e}")
    async with aiohttp.ClientSession(headers=headers) as session:
        await push(session)
        while True:
            jitter = random.randint(-600, 600)
            sleep_for = max(0, every_seconds + jitter)
            await asyncio.sleep(sleep_for)
            await push(session)