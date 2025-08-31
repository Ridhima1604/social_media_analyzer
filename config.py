# config.py
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
DB_NAME = os.getenv("DB_NAME", "social_analyzer")
COLLECTION = os.getenv("COLLECTION", "users")   # ✅ match what main.py expects
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
