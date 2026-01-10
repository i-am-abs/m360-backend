import uuid as uuid_module
from typing import Optional, Dict
from db.device_repository import DeviceRepository
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class LogDeviceRepository(DeviceRepository):

    def __init__(self):
        self.devices_by_uuid = {}
        logger.info("Using in-memory storage")

    def save_device(self, device_uuid: str) -> Optional[Dict]:
        try:
            if device_uuid in self.devices_by_uuid:
                _id = self.devices_by_uuid[device_uuid]
                return {"uuid": device_uuid, "_id": _id}

            _id = str(uuid_module.uuid4())
            self.devices_by_uuid[device_uuid] = _id
            logger.info(f"Device saved: uuid={device_uuid}")
            return {"uuid": device_uuid, "_id": _id}

        except Exception as e:
            logger.error(f"Error saving device: {e}")
            return None

    def get_device_by_uuid(self, device_uuid: str) -> Optional[Dict]:
        try:
            if device_uuid in self.devices_by_uuid:
                _id = self.devices_by_uuid[device_uuid]
                return {"uuid": device_uuid, "_id": _id}
            return None

        except Exception as e:
            logger.error(f"Error getting device by UUID: {e}")
            return None

    def get_all_devices(self) -> list:
        try:
            return [
                {"uuid": uuid_val, "_id": _id}
                for uuid_val, _id in self.devices_by_uuid.items()
            ]
        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return []

    def delete_device(self, device_uuid: str) -> bool:
        try:
            if device_uuid in self.devices_by_uuid:
                del self.devices_by_uuid[device_uuid]
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            return False

    def count_devices(self) -> int:
        return len(self.devices_by_uuid)
