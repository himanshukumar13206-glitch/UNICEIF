from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.queues_col = None

    async def connect(self):
        if MONGO_URI:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            self.queues_col = self.db["queues"]

    async def save_queue(self, chat_id: int, tracks: list):
        if self.queues_col is not None:
            await self.queues_col.update_one(
                {"chat_id": chat_id},
                {"$set": {"tracks": tracks}},
                upsert=True
            )

    async def load_queue(self, chat_id: int) -> list:
        if self.queues_col is not None:
            doc = await self.queues_col.find_one({"chat_id": chat_id})
            if doc:
                return doc.get("tracks", [])
        return []

db = Database()
