import asyncio
import re
import random
import yt_dlp
import httpx
from typing import Optional, Dict
from config import API_URL, API_KEY, COOKIES_URL

INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://yewtu.be",
    "https://invidious.kavin.rocks",
    "https://vid.puffyan.us",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

class Extractor:
    def __init__(self):
        self._yt_dlp_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "geo_bypass": True,
            "user_agent": random.choice(USER_AGENTS),
            "extract_flat": False,
        }
        if COOKIES_URL:
            self._yt_dlp_opts["cookiefile"] = COOKIES_URL  # yt-dlp supports URLs for cookies

    async def fetch(self, query: str) -> Optional[Dict]:
        """Try custom API first, then yt‑dlp, then Invidious."""
        # 1. Custom API
        if API_URL and API_KEY:
            data = await self._from_api(query)
            if data:
                return data

        # 2. yt‑dlp (with optional cookies)
        data = await self._from_ytdlp(query)
        if data:
            return data

        # 3. Invidious fallback
        return await self._from_invidious(query)

    async def _from_api(self, query: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{API_URL}/api/audio",
                    params={"query": query},
                    headers={"X-API-Key": API_KEY}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def _from_ytdlp(self, query: str) -> Optional[Dict]:
        try:
            loop = asyncio.get_event_loop()
            with yt_dlp.YoutubeDL(self._yt_dlp_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if info is None:
                    return None
                if "entries" in info:
                    info = info["entries"][0]

                audio_url = info.get("url")
                if not audio_url:
                    for fmt in info.get("formats", []):
                        if fmt.get("acodec") != "none" and fmt.get("url"):
                            audio_url = fmt["url"]
                            break
                if not audio_url:
                    return None
                return {
                    "title": info.get("title", "Unknown"),
                    "url": audio_url,
                    "webpage_url": info.get("webpage_url", ""),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                }
        except Exception:
            return None

    async def _from_invidious(self, query: str) -> Optional[Dict]:
        """Search for video ID and then get stream via Invidious."""
        vid = None
        if re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})", query):
            vid = re.search(r"(?:v=|/|embed/)([A-Za-z0-9_-]{11})", query).group(1)
        else:
            # Search on Invidious
            for instance in INVIDIOUS_INSTANCES:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(f"{instance}/api/v1/search", params={"q": query})
                        if resp.status_code == 200:
                            data = resp.json()
                            for item in data:
                                if item.get("type") == "video":
                                    vid = item.get("videoId")
                                    break
                            if vid:
                                break
                except Exception:
                    continue
        if not vid:
            return None

        # Now get the audio stream
        for instance in INVIDIOUS_INSTANCES:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(f"{instance}/api/v1/videos/{vid}")
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    adaptive = data.get("adaptiveFormats", [])
                    best = None
                    for fmt in adaptive:
                        if fmt.get("type", "").startswith("audio"):
                            if not best or "opus" in fmt.get("type", ""):
                                best = fmt
                    if best and best.get("url"):
                        return {
                            "title": data.get("title", "Unknown"),
                            "url": best["url"],
                            "webpage_url": f"https://youtube.com/watch?v={vid}",
                            "duration": data.get("lengthSeconds", 0),
                            "thumbnail": data.get("videoThumbnails", [{}])[0].get("url", ""),
                        }
            except Exception:
                continue
        return None

extractor = Extractor()
