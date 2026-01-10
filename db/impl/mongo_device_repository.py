import os
from typing import Optional, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from constants.system_config import SystemConfig
from db.device_repository import DeviceRepository
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class MongoDeviceRepository(DeviceRepository):
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        mongo_db = os.getenv("MONGO_DB", "quran_api")

        try:
            self.client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=int(
                    SystemConfig.MONGO_CONNECTION_TIMEOUT.value
                ),
                connectTimeoutMS=int(SystemConfig.MONGO_CONNECTION_TIMEOUT.value),
            )
            self.client.admin.command("ping")
            self.db = self.client[mongo_db]
            self.devices_collection = self.db["devices"]

            self.devices_collection.create_index("uuid", unique=True)
            logger.info(f"Connected to MongoDB: {mongo_db}")

        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB at {mongo_uri}")

    def save_device(self, device_uuid: str) -> Optional[Dict]:
        try:
            existing = self.devices_collection.find_one({"uuid": device_uuid})
            if existing:
                return {"uuid": existing["uuid"], "_id": str(existing["_id"])}

            document = {"uuid": device_uuid}
            result = self.devices_collection.insert_one(document)
            logger.info(f"Device saved: uuid={device_uuid}")
            return {"uuid": device_uuid, "_id": str(result.inserted_id)}

        except DuplicateKeyError:
            existing = self.devices_collection.find_one({"uuid": device_uuid})
            if existing:
                return {"uuid": existing["uuid"], "_id": str(existing["_id"])}
            return None

        except Exception as e:
            logger.error(f"Error saving device: {e}")
            return None

    def get_device_by_uuid(self, device_uuid: str) -> Optional[Dict]:
        try:
            device = self.devices_collection.find_one({"uuid": device_uuid})
            if device:
                return {"uuid": device["uuid"], "_id": str(device["_id"])}
            return None

        except Exception as e:
            logger.error(f"Error getting device by UUID: {e}")
            return None

    def get_all_devices(self) -> list:
        try:
            devices = []
            for doc in self.devices_collection.find({}):
                devices.append({"uuid": doc["uuid"], "_id": str(doc["_id"])})
            return devices

        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return []

    def delete_device(self, device_uuid: str) -> bool:
        try:
            result = self.devices_collection.delete_one({"uuid": device_uuid})
            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            return False

    def count_devices(self) -> int:
        try:
            return self.devices_collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting devices: {e}")
            return 0

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False
