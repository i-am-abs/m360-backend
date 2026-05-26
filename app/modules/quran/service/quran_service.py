from __future__ import annotations

from typing import Protocol

from app.modules.quran.facade.quran_module_facade import QuranModuleFacade


class QuranService(Protocol):
    def createFacade(self) -> QuranModuleFacade:
        ...
