from __future__ import annotations

import enum
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class Platform(str, enum.Enum):
    IOS = "ios"
    WEB = "web"
    CROSS_PLATFORM = "cross_platform"
    UNKNOWN = "unknown"


class DeploymentTarget(str, enum.Enum):
    APP_STORE = "app_store"
    TESTFLIGHT = "testflight"
    WEB_HOSTING = "web_hosting"
    ENTERPRISE = "enterprise"


class AgeRating(str, enum.Enum):
    FOUR_PLUS = "4+"
    NINE_PLUS = "9+"
    TWELVE_PLUS = "12+"
    SEVENTEEN_PLUS = "17+"


class MonetizationModel(str, enum.Enum):
    FREE = "free"
    PAID = "paid"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    ADS = "ads"
    NONE = "none"


class LandingPageChoice(str, enum.Enum):
    HTML = "html"
    PROMPT = "prompt"
    NO = "no"


class SDKDetection(BaseModel):

    name: str
    import_line: str = ""
    file_path: str = ""
    category: str = ""
    data_collected: list[str] = Field(default_factory=list)
    privacy_description: str = ""


class DataCollectionPattern(BaseModel):

    pattern_type: str
    description: str = ""
    file_path: str = ""
    entitlement_key: str = ""


class AuthDetection(BaseModel):

    method: str
    file_path: str = ""


class ProjectUnderstanding(BaseModel):

    project_path: str = ""
    project_name: str = ""
    platform: Platform = Platform.UNKNOWN
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    sdks: list[SDKDetection] = Field(default_factory=list)
    data_collection: list[DataCollectionPattern] = Field(default_factory=list)
    auth_methods: list[AuthDetection] = Field(default_factory=list)
    has_in_app_purchases: bool = False
    bundle_id: str = ""
    min_ios_version: str = ""
    readme_content: str = ""

    color_theme: dict[str, str] = Field(default_factory=dict)

    app_purpose: str = ""
    target_audience: str = ""
    deployment_target: DeploymentTarget = DeploymentTarget.APP_STORE
    monetization: MonetizationModel = MonetizationModel.FREE
    age_rating: AgeRating = AgeRating.FOUR_PLUS
    landing_page: LandingPageChoice = LandingPageChoice.PROMPT
    developer_name: str = ""
    developer_email: str = ""
    developer_country: str = ""
    company_name: str = ""
    support_url: str = ""

    @property
    def sdk_names(self) -> list[str]:
        return [s.name for s in self.sdks]

    @property
    def all_data_types(self) -> list[str]:
        types: set[str] = set()
        for sdk in self.sdks:
            types.update(sdk.data_collected)
        for dc in self.data_collection:
            types.add(dc.pattern_type)
        return sorted(types)

    @property
    def display_name(self) -> str:
        return self.project_name or "Unnamed Project"


class GeneratedArtifact(BaseModel):

    artifact_type: str
    content: str = ""
    file_path: str = ""
    format: str = "markdown"
    model_used: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: str = ""
    extra_files: dict[str, str] = Field(default_factory=dict)

    system_prompt: str = ""
    user_prompt: str = ""

    @property
    def success(self) -> bool:
        return bool(self.content) and not self.error


class GenerationResult(BaseModel):

    artifacts: list[GeneratedArtifact] = Field(default_factory=list)
    output_dir: str = ""
    branch_name: str = ""
    total_time_seconds: float = 0.0

    @property
    def successful(self) -> list[GeneratedArtifact]:
        return [a for a in self.artifacts if a.success]

    @property
    def failed(self) -> list[GeneratedArtifact]:
        return [a for a in self.artifacts if not a.success]


class DevDexPipelineState(BaseModel):

    understanding: ProjectUnderstanding = Field(default_factory=ProjectUnderstanding)
    result: GenerationResult = Field(default_factory=GenerationResult)
    scan_complete: bool = False
    interview_complete: bool = False
    generation_complete: bool = False
