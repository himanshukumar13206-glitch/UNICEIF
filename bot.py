import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamAudioEnded   # ← original, works with 2.0.0
from config import BOT_TOKEN, API_ID, API_HASH, SUPPORT_GROUP, SUPPORT_CHANNEL, ENABLE_VPLAY
from services.extractor import extractor
from services.player import Track, ChatPlayer, player_manager
from utils.helpers import is_authorized, log_message
from utils.database import db

logging.basicConfig(level=logging.INFO)

bot = Client("UNICEIF", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(bot)

@pytgcalls.on_stream_end()
async def stream_end(_, update: Update):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        player = player_manager.players.get(chat_id)
        if player and player.is_playing:
            player._skip_event.set()

@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    text = "🎶 **UNICEIF Premium Music Bot** is alive!\n\n"
    if SUPPORT_GROUP:
        text += f"🆘 Support: {SUPPORT_GROUP}\n"
    if SUPPORT_CHANNEL:
        text += f"📢 Channel: {SUPPORT_CHANNEL}\n"
    text += "\nUse /play <song or link>"
    await msg.reply_text(text)

@bot.on_message(filters.command("play"))
async def play(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        return await msg.reply_text("⛔ Unauthorized.")
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: /play <query or YouTube URL>")
    query = msg.text.split(maxsplit=1)[1]
    status = await msg.reply_text("🔍 Searching...")
    info = await extractor.fetch(query)
    if not info:
        return await status.edit("❌ Could not fetch audio. Try another query.")
    track = Track(info, msg.from_user.id)
    player = player_manager.get(msg.chat.id, bot, pytgcalls)
    success = await player.add_track(track, status)
    if success is False:
        return
    await status.edit(f"✅ Added to queue: **{track.title}**")

@bot.on_message(filters.command("skip"))
async def skip(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        return await msg.reply_text("⛔ Unauthorized.")
    player = player_manager.players.get(msg.chat.id)
    if player and player.is_playing:
        await player.skip()
        await msg.reply_text("⏭ Skipped")
    else:
        await msg.reply_text("Nothing playing.")

@bot.on_message(filters.command("stop"))
async def stop(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        return await msg.reply_text("⛔ Unauthorized.")
    player = player_manager.players.get(msg.chat.id)
    if player:
        await player.stop()
        await msg.reply_text("⏹ Stopped & cleared.")
    else:
        await msg.reply_text("No active player.")

@bot.on_message(filters.command("pause"))
async def pause(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        return await msg.reply_text("⛔ Unauthorized.")
    player = player_manager.players.get(msg.chat.id)
    if player:
        await player.pause()
        await msg.reply_text("⏸ Paused")
    else:
        await msg.reply_text("Nothing to pause.")

@bot.on_message(filters.command("resume"))
async def resume(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        return await msg.reply_text("⛔ Unauthorized.")
    player = player_manager.players.get(msg.chat.id)
    if player:
        await player.resume()
        await msg.reply_text("▶️ Resumed")
    else:
        await msg.reply_text("Nothing to resume.")

@bot.on_message(filters.command("queue"))
async def queue_cmd(_, msg: Message):
    player = player_manager.players.get(msg.chat.id)
    if not player or (not player.current and not player.queue):
        return await msg.reply_text("Queue empty.")
    np = player.now_playing()
    qlist = player.queue_list()
    text = f"**Now Playing:** {np}\n\n**Queue:**\n" + "\n".join(qlist[:15])
    if len(qlist) > 15:
        text += f"\n... and {len(qlist)-15} more"
    await msg.reply_text(text)

@bot.on_message(filters.command("np"))
async def np_cmd(_, msg: Message):
    player = player_manager.players.get(msg.chat.id)
    if player:
        await msg.reply_text(player.now_playing())
    else:
        await msg.reply_text("Nothing playing.")

async def main():
    await db.connect()
    await bot.start()
    await pytgcalls.start()
    logging.info("UNICEIF Premium Music Bot started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
