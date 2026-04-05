from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_NAME = os.getenv("APP_NAME", "Zodex Server")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8008"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://infozodex_db_user:absolutions@data.yycywiw.mongodb.net")
MONGODB_DB = os.getenv("MONGODB_DB", "zodex_server")
USE_MOCK_DB = os.getenv("USE_MOCK_DB", "false").lower() == "true"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "Zodex Admin")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
