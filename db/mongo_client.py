import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from logger.Logger import Logger

logger = Logger.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


_mongo_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _load_env()
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        logger.info("MongoDB client initialised (uri=%s)", uri.split("@")[-1])
    return _mongo_client


def get_database() -> Database:
    global _database
    if _database is None:
        _load_env()
        db_name = os.getenv("MONGO_DB_NAME", "m360")
        _database = get_mongo_client()[db_name]
        logger.info("Using MongoDB database: %s", db_name)
    return _database


def close_mongo_client() -> None:
    global _mongo_client, _database
    if _mongo_client is not None:
        _mongo_client.close()
        logger.info("MongoDB client closed")
        _mongo_client = None
        _database = None
