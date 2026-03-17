from pymongo import MongoClient
from config import MONGO_URI
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri):
        try:
            self.client = MongoClient(uri)
            self.db = self.client.get_database()
            # Collections
            self.users = self.db.users
            self.watermarks = self.db.watermarks
            self.tasks = self.db.tasks
            self.bans = self.db.bans
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    # User methods
    def add_user(self, user_id, username, first_name, last_name):
        user = {
            "_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "joined_at": self.db.command("buildinfo")["version"],  # Just a placeholder for timestamp
            "is_banned": False
        }
        self.users.update_one({"_id": user_id}, {"$set": user}, upsert=True)

    def get_user(self, user_id):
        return self.users.find_one({"_id": user_id})

    def update_user(self, user_id, data):
        self.users.update_one({"_id": user_id}, {"$set": data})

    def ban_user(self, user_id):
        self.users.update_one({"_id": user_id}, {"$set": {"is_banned": True}})
        self.bans.insert_one({"user_id": user_id, "banned_at": self.db.command("buildinfo")["version"]})

    def unban_user(self, user_id):
        self.users.update_one({"_id": user_id}, {"$set": {"is_banned": False}})
        self.bans.delete_one({"user_id": user_id})

    def is_user_banned(self, user_id):
        user = self.get_user(user_id)
        return user.get("is_banned", False) if user else False

    # Watermark methods
    def add_watermark(self, user_id, watermark_data):
        watermark_data["user_id"] = user_id
        result = self.watermarks.insert_one(watermark_data)
        return result.inserted_id

    def get_watermarks(self, user_id):
        return list(self.watermarks.find({"user_id": user_id}))

    def get_watermark(self, watermark_id):
        return self.watermarks.find_one({"_id": watermark_id})

    def update_watermark(self, watermark_id, data):
        self.watermarks.update_one({"_id": watermark_id}, {"$set": data})

    def delete_watermark(self, watermark_id):
        self.watermarks.delete_one({"_id": watermark_id})

    # Task methods
    def add_task(self, task_data):
        result = self.tasks.insert_one(task_data)
        return result.inserted_id

    def update_task(self, task_id, data):
        self.tasks.update_one({"_id": task_id}, {"$set": data})

    def get_task(self, task_id):
        return self.tasks.find_one({"_id": task_id})

    def get_user_tasks(self, user_id):
        return list(self.tasks.find({"user_id": user_id}))

# Initialize database instance
db = Database(MONGO_URI)