from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class SourceKind(StrEnum):
    resume = "resume"
    job_description = "job_description"
    github = "github"
    portfolio = "portfolio"


class RequirementCategory(StrEnum):
    skill = "skill"
    mandatory_skill = "mandatory_skill"
    preferred_skill = "preferred_skill"
    nice_to_have_skill = "nice_to_have_skill"
    years_experience = "years_experience"
    responsibility = "responsibility"
    education = "education"
    certification = "certification"
    domain_knowledge = "domain_knowledge"
    tooling = "tooling"
    soft_skill = "soft_skill"
    keyword = "keyword"
    implied_requirement = "implied_requirement"
    seniority = "seniority"


class NormalizedTerm(BaseModel):
    original: str
    canonical: str
    synonyms: list[str] = Field(default_factory=list)


class ExtractedItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    location: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ContactInformation(BaseModel):
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class ResumeExtraction(BaseModel):
    source: str
    name: str | None = None
    contact_information: ContactInformation = Field(default_factory=ContactInformation)
    summary: str | None = None
    sections: dict[str, list[ExtractedItem]] = Field(default_factory=dict)
    items: list[ExtractedItem] = Field(default_factory=list)
    raw_text: str = Field(min_length=1)


class JobRequirementExtraction(BaseModel):
    text: str = Field(min_length=1)
    kind: str = "contextual"
    category: RequirementCategory = RequirementCategory.keyword
    source_location: str
    original_terms: list[str] = Field(default_factory=list)
    normalized_terms: list[str] = Field(default_factory=list)
    terms: list[NormalizedTerm] = Field(default_factory=list)
    years_experience: int | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)


class JobDescriptionExtraction(BaseModel):
    source: str
    title: str | None = None
    seniority_indicators: list[str] = Field(default_factory=list)
    years_of_experience: int | None = Field(default=None, ge=0)
    mandatory_skills: list[NormalizedTerm] = Field(default_factory=list)
    preferred_skills: list[NormalizedTerm] = Field(default_factory=list)
    nice_to_have_skills: list[NormalizedTerm] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)
    tooling: list[NormalizedTerm] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    keywords: list[NormalizedTerm] = Field(default_factory=list)
    implied_requirements: list[str] = Field(default_factory=list)
    raw_text: str = Field(min_length=1)
    requirements: list[JobRequirementExtraction] = Field(default_factory=list)


class ExternalContentExtraction(BaseModel):
    source: HttpUrl
    title: str | None = None
    text: str = Field(min_length=1)
    items: list[ExtractedItem] = Field(default_factory=list)
