from __future__ import annotations

from http import HTTPStatus
from typing import Dict, List, Optional

from app.core.enums.error_code import ErrorCode
from app.exceptions.base import ApiException
from app.modules.feature_flag.application.dto.feature_flag_dto import (
    FeatureFlagCreateRequestDto,
    FeatureFlagEvaluationRequestDto,
    FeatureFlagEvaluationResponseDto,
    FeatureFlagListResponseDto,
    FeatureFlagResponseDto,
    FeatureFlagUpdateRequestDto,
)
from app.modules.feature_flag.application.ports.feature_flag_repository_port import FeatureFlagRepositoryPort
from app.modules.feature_flag.domain.entities.feature_flag_entity import FeatureFlagEntity
from app.modules.feature_flag.domain.value_objects.feature_flag_evaluation_context import (
    FeatureFlagEvaluationContext,
)
from app.modules.feature_flag.infrastructure.factories.feature_flag_evaluation_strategy_factory import (
    FeatureFlagEvaluationStrategyFactory,
)


class FeatureFlagManagementService:
    EVALUATION_REASON_FEATURE_NOT_FOUND = "FEATURE_NOT_FOUND"
    EVALUATION_REASON_FEATURE_INACTIVE = "FEATURE_INACTIVE"
    EVALUATION_REASON_GLOBALLY_DISABLED = "GLOBALLY_DISABLED"
    EVALUATION_REASON_CONDITION_MATCHED = "CONDITION_MATCHED"
    EVALUATION_REASON_DEFAULT_ENABLED = "DEFAULT_ENABLED"
    EVALUATION_REASON_CONDITION_NOT_MATCHED = "CONDITION_NOT_MATCHED"

    def __init__(
            self,
            featureFlagRepository: FeatureFlagRepositoryPort,
            evaluationStrategyFactory: FeatureFlagEvaluationStrategyFactory,
            runtimeEnvironmentName: str,
    ) -> None:
        self.featureFlagRepository = featureFlagRepository
        self.evaluationStrategyFactory = evaluationStrategyFactory
        self.runtimeEnvironmentName = runtimeEnvironmentName
        self.featureFlagCacheByName: Dict[str, FeatureFlagEntity] = {}

    def refreshFeatureFlagCache(self) -> None:
        self.featureFlagCacheByName = {
            featureFlag.featureName: featureFlag
            for featureFlag in self.featureFlagRepository.findAllFeatureFlags()
        }

    def createFeatureFlag(self, createRequest: FeatureFlagCreateRequestDto) -> FeatureFlagResponseDto:
        existingFeatureFlag = self.featureFlagRepository.findFeatureFlagByName(createRequest.feature_name)
        if existingFeatureFlag is not None:
            raise ApiException(
                f"Feature flag '{createRequest.feature_name}' already exists.",
                status_code=HTTPStatus.CONFLICT.value,
                code=ErrorCode.FEATURE_FLAG_ALREADY_EXISTS,
            )

        featureFlagEntity = FeatureFlagEntity(
            featureName=createRequest.feature_name,
            displayName=createRequest.display_name,
            description=createRequest.description,
            globallyEnabled=createRequest.globally_enabled,
            defaultEnabled=createRequest.default_enabled,
            conditionType=createRequest.condition_type,
            conditionConfiguration=createRequest.condition_configuration,
            featureFlagStatus=createRequest.feature_flag_status,
        )
        savedFeatureFlag = self.featureFlagRepository.saveFeatureFlag(featureFlagEntity)
        self.featureFlagCacheByName[savedFeatureFlag.featureName] = savedFeatureFlag
        return self.toResponseDto(savedFeatureFlag)

    def updateFeatureFlag(
            self,
            featureName: str,
            updateRequest: FeatureFlagUpdateRequestDto,
    ) -> FeatureFlagResponseDto:
        normalizedFeatureName = featureName.strip().upper()
        existingFeatureFlag = self.findFeatureFlagEntityByName(normalizedFeatureName)
        if existingFeatureFlag is None:
            raise ApiException(
                f"Feature flag '{normalizedFeatureName}' was not found.",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.FEATURE_FLAG_NOT_FOUND,
            )

        if updateRequest.display_name is not None:
            existingFeatureFlag.displayName = updateRequest.display_name
        if updateRequest.description is not None:
            existingFeatureFlag.description = updateRequest.description
        if updateRequest.globally_enabled is not None:
            existingFeatureFlag.globallyEnabled = updateRequest.globally_enabled
        if updateRequest.default_enabled is not None:
            existingFeatureFlag.defaultEnabled = updateRequest.default_enabled
        if updateRequest.condition_type is not None:
            existingFeatureFlag.conditionType = updateRequest.condition_type
        if updateRequest.condition_configuration is not None:
            existingFeatureFlag.conditionConfiguration = updateRequest.condition_configuration
        if updateRequest.feature_flag_status is not None:
            existingFeatureFlag.featureFlagStatus = updateRequest.feature_flag_status

        existingFeatureFlag.touchUpdatedAt()
        savedFeatureFlag = self.featureFlagRepository.saveFeatureFlag(existingFeatureFlag)
        self.featureFlagCacheByName[savedFeatureFlag.featureName] = savedFeatureFlag
        return self.toResponseDto(savedFeatureFlag)

    def deleteFeatureFlag(self, featureName: str) -> None:
        normalizedFeatureName = featureName.strip().upper()
        deleted = self.featureFlagRepository.deleteFeatureFlagByName(normalizedFeatureName)
        if not deleted:
            raise ApiException(
                f"Feature flag '{normalizedFeatureName}' was not found.",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.FEATURE_FLAG_NOT_FOUND,
            )
        self.featureFlagCacheByName.pop(normalizedFeatureName, None)

    def getFeatureFlagByName(self, featureName: str) -> FeatureFlagResponseDto:
        normalizedFeatureName = featureName.strip().upper()
        featureFlagEntity = self.findFeatureFlagEntityByName(normalizedFeatureName)
        if featureFlagEntity is None:
            raise ApiException(
                f"Feature flag '{normalizedFeatureName}' was not found.",
                status_code=HTTPStatus.NOT_FOUND.value,
                code=ErrorCode.FEATURE_FLAG_NOT_FOUND,
            )
        return self.toResponseDto(featureFlagEntity)

    def listAllFeatureFlags(self) -> FeatureFlagListResponseDto:
        featureFlagEntities = self.featureFlagRepository.findAllFeatureFlags()
        responseItems = [self.toResponseDto(featureFlagEntity) for featureFlagEntity in featureFlagEntities]
        return FeatureFlagListResponseDto(count=len(responseItems), feature_flags=responseItems)

    def evaluateFeatureFlag(
            self,
            evaluationRequest: FeatureFlagEvaluationRequestDto,
    ) -> FeatureFlagEvaluationResponseDto:
        evaluationContext = FeatureFlagEvaluationContext(
            latitude=evaluationRequest.latitude,
            longitude=evaluationRequest.longitude,
            userId=evaluationRequest.user_id,
            environmentName=evaluationRequest.environment_name or self.runtimeEnvironmentName,
            regionCode=evaluationRequest.region_code,
        )
        enabled, reason = self.evaluateFeatureFlagWithContext(
            evaluationRequest.feature_name,
            evaluationContext,
        )
        return FeatureFlagEvaluationResponseDto(
            feature_name=evaluationRequest.feature_name.strip().upper(),
            enabled=enabled,
            reason=reason,
        )

    def isFeatureEnabled(
            self,
            featureName: str,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> bool:
        enabled, _reason = self.evaluateFeatureFlagWithContext(featureName, evaluationContext)
        return enabled

    def isFeatureEnabledAtLocation(
            self,
            featureName: str,
            latitude: float,
            longitude: float,
    ) -> bool:
        evaluationContext = FeatureFlagEvaluationContext(
            latitude=latitude,
            longitude=longitude,
            environmentName=self.runtimeEnvironmentName,
        )
        return self.isFeatureEnabled(featureName, evaluationContext)

    def evaluateFeatureFlagWithContext(
            self,
            featureName: str,
            evaluationContext: FeatureFlagEvaluationContext,
    ) -> tuple[bool, str]:
        normalizedFeatureName = featureName.strip().upper()
        featureFlagEntity = self.findFeatureFlagEntityByName(normalizedFeatureName)
        if featureFlagEntity is None:
            return False, self.EVALUATION_REASON_FEATURE_NOT_FOUND

        if not featureFlagEntity.isActive():
            return False, self.EVALUATION_REASON_FEATURE_INACTIVE

        if not featureFlagEntity.globallyEnabled:
            return False, self.EVALUATION_REASON_GLOBALLY_DISABLED

        evaluationStrategy = self.evaluationStrategyFactory.resolveStrategy(
            featureFlagEntity.conditionType
        )
        conditionMatched = evaluationStrategy.evaluateFeatureFlag(
            featureFlagEntity,
            evaluationContext,
        )
        if conditionMatched:
            return True, self.EVALUATION_REASON_CONDITION_MATCHED

        if featureFlagEntity.defaultEnabled:
            return True, self.EVALUATION_REASON_DEFAULT_ENABLED

        return False, self.EVALUATION_REASON_CONDITION_NOT_MATCHED

    def findFeatureFlagEntityByName(self, featureName: str) -> Optional[FeatureFlagEntity]:
        normalizedFeatureName = featureName.strip().upper()
        cachedFeatureFlag = self.featureFlagCacheByName.get(normalizedFeatureName)
        if cachedFeatureFlag is not None:
            return cachedFeatureFlag

        loadedFeatureFlag = self.featureFlagRepository.findFeatureFlagByName(normalizedFeatureName)
        if loadedFeatureFlag is not None:
            self.featureFlagCacheByName[normalizedFeatureName] = loadedFeatureFlag
        return loadedFeatureFlag

    def toResponseDto(self, featureFlagEntity: FeatureFlagEntity) -> FeatureFlagResponseDto:
        return FeatureFlagResponseDto(
            feature_flag_id=featureFlagEntity.featureFlagId,
            feature_name=featureFlagEntity.featureName,
            display_name=featureFlagEntity.displayName,
            description=featureFlagEntity.description,
            globally_enabled=featureFlagEntity.globallyEnabled,
            default_enabled=featureFlagEntity.defaultEnabled,
            condition_type=featureFlagEntity.conditionType,
            condition_configuration=featureFlagEntity.conditionConfiguration,
            feature_flag_status=featureFlagEntity.featureFlagStatus,
            created_at=featureFlagEntity.createdAt.isoformat(),
            updated_at=featureFlagEntity.updatedAt.isoformat(),
        )
