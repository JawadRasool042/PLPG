"""Typed data structures for the advanced learning intelligence system."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class LearningProfile:
    user_id: Optional[str]
    primary_interest: str
    user_profile: str
    profile_confidence: float
    top_domains: List[Dict[str, Any]] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    signals: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LearningInsight:
    domain: str
    match_score: float
    match_percent: float
    why_matched: List[str] = field(default_factory=list)
    skills_gap: List[str] = field(default_factory=list)
    fastest_path: str = ""
    best_courses: List[str] = field(default_factory=list)
    best_projects: List[str] = field(default_factory=list)
    best_certifications: List[str] = field(default_factory=list)
    community_resources: List[str] = field(default_factory=list)
    career_paths: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RoadmapItem:
    level: str
    duration: str
    goals: List[str]
    projects: List[str]
    metrics: Dict[str, Any] = field(default_factory=dict)
    milestones: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
