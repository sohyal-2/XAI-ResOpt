from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.parsing.models import ExtractedItem


class IngestionResponse(BaseModel):
    id: UUID
    source: str
    item_count: int
    items: list[ExtractedItem]


class JobDescriptionResponse(BaseModel):
    id: UUID
    title: str
    source: str
    requirement_count: int
    seniority_indicators: list[str]
    keywords: list[dict]
    requirements: list[dict]
    years_of_experience: int | None = None
    mandatory_skills: list[dict] = Field(default_factory=list)
    preferred_skills: list[dict] = Field(default_factory=list)
    nice_to_have_skills: list[dict] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)
    tooling: list[dict] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    implied_requirements: list[str] = Field(default_factory=list)


class ExternalSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    uri: HttpUrl
    item_count: int = Field(ge=0)
