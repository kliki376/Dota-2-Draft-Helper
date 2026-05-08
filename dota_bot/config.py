import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
CACHE_FILE = "dota_bot/cache.json"

DOTABUFF_BASE = "https://www.dotabuff.com/heroes"
OPENDOTA_API = "https://api.opendota.com/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

OPENDOTA_API_KEY = os.environ.get("OPENDOTA_API_KEY", "")

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "counter": 0.40,
    "synergy": 0.25,
    "meta": 0.20,
    "pro": 0.15,
}
