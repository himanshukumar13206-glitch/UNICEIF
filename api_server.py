import yt_dlp
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
import os

app = FastAPI(title="UNICEIF Music API")

# Read API key from environment (set in Render dashboard)
API_KEY = os.getenv("API_KEY", "supersecretkey")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

def extract_audio(query: str) -> dict:
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        audio_url = info.get("url")
        if not audio_url:
            for fmt in info.get("formats", []):
                if fmt.get("acodec") != "none" and fmt.get("url"):
                    audio_url = fmt["url"]
                    break
        if not audio_url:
            raise HTTPException(status_code=404, detail="No audio stream")
        return {
            "title": info.get("title", "Unknown"),
            "url": audio_url,
            "webpage_url": info.get("webpage_url", ""),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
        }

@app.get("/api/audio", dependencies=[Security(verify_key)])
async def get_audio(query: str):
    try:
        return extract_audio(query)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
