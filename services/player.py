import asyncio
import logging
from collections import deque
from typing import Optional, List
from pyrogram import Client
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update, AudioPiped          # ✅ Fixed import
from pytgcalls.types import StreamEnded                # (Just in case, already used in bot.py)
from pytgcalls.exceptions import NoActiveGroupCall, GroupCallNotFound
from utils.database import db
from utils.helpers import log_message
from config import SONG_DURATION_LIMIT

logger = logging.getLogger(__name__)

class Track:
    def __init__(self, info: dict, requested_by: int):
        self.title = info["title"]
        self.url = info["url"]
        self.webpage = info["webpage_url"]
        self.duration = info.get("duration", 0)
        self.thumbnail = info.get("thumbnail", "")
        self.requester = requested_by

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "webpage": self.webpage,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "requester": self.requester,
        }

    @staticmethod
    def from_dict(data):
        track = Track.__new__(Track)
        track.title = data["title"]
        track.url = data["url"]
        track.webpage = data["webpage"]
        track.duration = data["duration"]
        track.thumbnail = data["thumbnail"]
        track.requester = data["requester"]
        return track

class ChatPlayer:
    def __init__(self, chat_id: int, client: Client, pytgcalls: PyTgCalls):
        self.chat_id = chat_id
        self.client = client
        self.pytgcalls = pytgcalls
        self.queue = deque()
        self.current: Optional[Track] = None
        self.is_playing = False
        self.is_paused = False
        self._skip_event = asyncio.Event()

    async def add_track(self, track: Track, status_msg: Message = None):
        if SONG_DURATION_LIMIT and track.duration > SONG_DURATION_LIMIT:
            if status_msg:
                await status_msg.edit(f"❌ Song too long. Max {SONG_DURATION_LIMIT} sec.")
            return False
        self.queue.append(track)
        await db.save_queue(self.chat_id, [t.to_dict() for t in self.queue])
        if not self.is_playing:
            await self._start_playing()
        return True

    async def _start_playing(self):
        if self.is_playing or not self.queue:
            return
        self.is_playing = True
        while self.queue:
            self.current = self.queue.popleft()
            await db.save_queue(self.chat_id, [t.to_dict() for t in self.queue])
            self.is_paused = False
            try:
                await self.pytgcalls.join_group_call(
                    self.chat_id,
                    AudioPiped(self.current.url),      # ✅ Works with new import
                )
                await log_message(self.client, f"▶️ Now playing: **{self.current.title}** in {self.chat_id}")
            except (NoActiveGroupCall, GroupCallNotFound):
                await self.client.send_message(self.chat_id, "❌ No active voice chat. Start one first.")
                self.is_playing = False
                self.queue.clear()
                await db.save_queue(self.chat_id, [])
                return
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await self.client.send_message(self.chat_id, f"❌ Stream error: {e}")
                continue

            self._skip_event.clear()
            try:
                await asyncio.wait_for(self._skip_event.wait(), timeout=self.current.duration + 10)
            except asyncio.TimeoutError:
                pass
            try:
                await self.pytgcalls.leave_group_call(self.chat_id)
            except:
                pass

        self.current = None
        self.is_playing = False
        await db.save_queue(self.chat_id, [])
        await self.client.send_message(self.chat_id, "🎵 Queue finished, left voice chat.")
        await log_message(self.client, f"🏁 Queue ended in {self.chat_id}")

    async def skip(self):
        if self.is_playing:
            self._skip_event.set()

    async def stop(self):
        self.queue.clear()
        await db.save_queue(self.chat_id, [])
        if self.is_playing:
            self._skip_event.set()
        try:
            await self.pytgcalls.leave_group_call(self.chat_id)
        except:
            pass

    async def pause(self):
        if self.is_playing and not self.is_paused:
            try:
                await self.pytgcalls.pause_stream(self.chat_id)
                self.is_paused = True
            except Exception as e:
                logger.error(f"Pause error: {e}")

    async def resume(self):
        if self.is_playing and self.is_paused:
            try:
                await self.pytgcalls.resume_stream(self.chat_id)
                self.is_paused = False
            except Exception as e:
                logger.error(f"Resume error: {e}")

    async def now_playing(self) -> str:
        if self.current:
            return f"🎵 {self.current.title}"
        return "🔇 Nothing playing"

    def queue_list(self) -> List[str]:
        return [f"{i+1}. {t.title}" for i, t in enumerate(self.queue)]

class PlayerManager:
    def __init__(self):
        self.players = {}

    def get(self, chat_id: int, client: Client, pytgcalls: PyTgCalls) -> ChatPlayer:
        if chat_id not in self.players:
            self.players[chat_id] = ChatPlayer(chat_id, client, pytgcalls)
        return self.players[chat_id]

player_manager = PlayerManager()
