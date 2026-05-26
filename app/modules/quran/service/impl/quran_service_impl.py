from __future__ import annotations

from app.modules.quran.configuration.quran_module_configuration import QuranModuleConfiguration
from app.modules.quran.facade.quran_module_facade import QuranModuleFacade
from app.modules.quran.service.quran_service import QuranService


class QuranServiceImpl(QuranService):
    def __init__(self, moduleConfiguration: QuranModuleConfiguration) -> None:
        self.moduleConfiguration = moduleConfiguration

    def createFacade(self) -> QuranModuleFacade:
        return self.moduleConfiguration.createFacade()
