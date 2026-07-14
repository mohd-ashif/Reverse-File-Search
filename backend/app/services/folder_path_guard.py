"""Classifies a folder path's indexing risk level and enforces the hard block
for High-risk paths.

- HIGH: drive/filesystem roots, OS system directories, the user's entire
  profile root, and sensitive profile children (AppData, OneDrive) that can
  hold credentials or an entire synced cloud library. Blocked outright.
- MEDIUM: broad-but-common personal folders (Desktop, Downloads, Documents,
  Pictures). Allowed, but flagged with a warning + recommendation.
- LOW: anything more specific. No warning.

Matching runs on both the raw user input and the resolved absolute path so
the check is OS-convention-independent and catches path-traversal tricks
(e.g. ``C:\\Users\\me\\..\\..\\Windows``) after resolution.
"""

import re
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high"]

RECOMMENDATION_HIGH = "Select a smaller, business-specific folder instead."
RECOMMENDATION_MEDIUM = "Consider selecting a more specific subfolder, e.g. Documents\\Reports."
RECOMMENDATION_LOW = "This folder looks safe to monitor."

TOO_BROAD_MESSAGE = (
    "This folder is too broad and may expose sensitive system or personal files. "
    "Please select a specific subfolder instead."
)


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    reason: str
    recommendation: str


# --- HIGH: hard-blocked -------------------------------------------------

_HIGH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"^[A-Za-z]:[\\/]?$"),
        "This is an entire drive, containing every file on the disk.",
    ),
    (
        re.compile(
            r"^[A-Za-z]:[\\/](Windows|Program Files( \(x86\))?|ProgramData)[\\/]?$",
            re.IGNORECASE,
        ),
        "This is a Windows system directory required for the computer to function.",
    ),
    (
        re.compile(r"^[A-Za-z]:[\\/]Users[\\/]?$", re.IGNORECASE),
        "This contains every user's profile on this computer.",
    ),
    (
        re.compile(r"^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/]?$", re.IGNORECASE),
        "This is an entire user profile, containing personal and system files.",
    ),
    (
        re.compile(
            r"^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/](AppData|OneDrive[^\\/]*)[\\/]?$",
            re.IGNORECASE,
        ),
        "This can contain sensitive application data, credentials, or an entire cloud-synced library.",
    ),
    (re.compile(r"^/$"), "This is the root of the filesystem, containing every file on the machine."),
    (
        re.compile(r"^/(root|etc|usr|System|Applications|private)/?$", re.IGNORECASE),
        "This is an operating system directory required for the computer to function.",
    ),
    (
        re.compile(r"^/(home|Users)/?$", re.IGNORECASE),
        "This contains every user's profile on this computer.",
    ),
    (
        re.compile(r"^/(home|Users)/[^/]+/?$", re.IGNORECASE),
        "This is an entire user profile, containing personal and system files.",
    ),
    (
        re.compile(r"^/(home|Users)/[^/]+/OneDrive[^/]*/?$", re.IGNORECASE),
        "This can contain an entire cloud-synced library.",
    ),
]

# --- MEDIUM: allowed, warned -------------------------------------------

_MEDIUM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/](Desktop|Downloads|Documents|Pictures)[\\/]?$",
        re.IGNORECASE,
    ),
    re.compile(r"^/(home|Users)/[^/]+/(Desktop|Downloads|Documents|Pictures)/?$", re.IGNORECASE),
]

_MEDIUM_REASON = "This is a broad personal folder that likely mixes personal and business files."

_LOW_REASON = "This looks like a specific, business-relevant folder."


def _match_high(candidate: str) -> str | None:
    candidate = candidate.strip()
    if not candidate:
        return "No folder path was provided."
    for pattern, reason in _HIGH_PATTERNS:
        if pattern.match(candidate):
            return reason
    return None


def _match_medium(candidate: str) -> bool:
    candidate = candidate.strip()
    return any(pattern.match(candidate) for pattern in _MEDIUM_PATTERNS)


def classify_folder_risk(raw_path: str, resolved_path: str | None = None) -> RiskAssessment:
    """Classifies risk using both the raw input and the resolved absolute
    path (when available), taking the higher of the two risk levels."""
    candidates = [raw_path] + ([resolved_path] if resolved_path is not None else [])

    for candidate in candidates:
        high_reason = _match_high(candidate)
        if high_reason is not None:
            return RiskAssessment(level="high", reason=high_reason, recommendation=RECOMMENDATION_HIGH)

    for candidate in candidates:
        if _match_medium(candidate):
            return RiskAssessment(level="medium", reason=_MEDIUM_REASON, recommendation=RECOMMENDATION_MEDIUM)

    return RiskAssessment(level="low", reason=_LOW_REASON, recommendation=RECOMMENDATION_LOW)


def is_folder_path_too_broad(raw_path: str, resolved_path: str | None = None) -> bool:
    """True only for High-risk paths — the ones that are hard-blocked."""
    return classify_folder_risk(raw_path, resolved_path).level == "high"
