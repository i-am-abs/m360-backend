from abc import ABC, abstractmethod
from typing import Optional, Dict


class DeviceRepository(ABC):
    @abstractmethod
    def save_device(self, device_uuid: str) -> Optional[Dict]:
        """Save a device with UUID. Returns dict with uuid and _id if successful."""
        pass

    @abstractmethod
    def get_device_by_uuid(self, device_uuid: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_all_devices(self) -> list:
        pass

    @abstractmethod
    def delete_device(self, device_uuid: str) -> bool:
        pass
