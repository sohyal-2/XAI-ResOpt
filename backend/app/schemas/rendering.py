"""Schemas for deterministic resume document representation, layout configuration, and pre-rendering validation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeContactBlock(BaseModel):
    """Structured contact header block for ATS parsing."""
    name: str = Field(description="Full legal or professional name")
    email: str = Field(description="Primary email address")
    phone: str | None = Field(default=None, description="Contact phone number")
    location: str | None = Field(default=None, description="City, State, or Country")
    linkedin: str | None = Field(default=None, description="LinkedIn profile URL")
    github: str | None = Field(default=None, description="GitHub profile URL")
    portfolio: str | None = Field(default=None, description="Portfolio or website URL")


class ResumeItemBlock(BaseModel):
    """Individual entry in an experience, education, or project section."""
    title: str | None = Field(default=None, description="Job title, degree, or project name")
    organization: str | None = Field(default=None, description="Company, university, or institution")
    date_range: str | None = Field(default=None, description="Dates active e.g. 2020 - Present")
    location: str | None = Field(default=None, description="City/State location")
    bullets: list[str] = Field(default_factory=list, description="Specific impact bullet points")
    raw_text: str | None = Field(default=None, description="Paragraph or unstructured content")


class ResumeSectionBlock(BaseModel):
    """Normalized ATS section block with safe heading and ordered items."""
    section_key: str = Field(description="Standardized key e.g. summary, experience, skills, education, certifications")
    heading: str = Field(description="Display heading e.g. Professional Summary, Work Experience, Technical Skills")
    items: list[ResumeItemBlock] = Field(default_factory=list)


class ResumeRenderConfig(BaseModel):
    """Customizable rendering layout and typography settings for ATS-safe generation."""
    font_family: str = Field(default="Helvetica", description="Primary font family: Helvetica or Times")
    font_size_pt: int = Field(default=10, ge=9, le=12, description="Base body font size in points")
    heading_size_pt: int = Field(default=13, ge=12, le=16, description="Section heading font size in points")
    margins_inch: float = Field(default=0.6, ge=0.4, le=1.0, description="Page margins in inches")
    line_spacing: float = Field(default=1.2, ge=1.0, le=1.5, description="Paragraph line spacing multiplier")
    section_order: list[str] = Field(
        default=["summary", "experience", "skills", "education", "certifications", "projects"],
        description="Configurable section rendering order",
    )
    show_dividers: bool = Field(default=True, description="Render subtle ATS-safe horizontal divider lines")

    model_config = ConfigDict(extra="forbid")


class DeterministicResumeDocument(BaseModel):
    """Standardized, deterministic resume representation consumed by document renderers."""
    resume_version_id: UUID | None = None
    header: ResumeContactBlock
    sections: list[ResumeSectionBlock] = Field(default_factory=list)
    config: ResumeRenderConfig = Field(default_factory=ResumeRenderConfig)


class ResumeValidationResult(BaseModel):
    """Audit report from the pre-rendering validation layer."""
    is_valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks_passed: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
