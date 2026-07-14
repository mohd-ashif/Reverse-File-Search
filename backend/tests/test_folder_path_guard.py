import pytest

from app.services.folder_path_guard import (
    RECOMMENDATION_HIGH,
    RECOMMENDATION_LOW,
    RECOMMENDATION_MEDIUM,
    classify_folder_risk,
    is_folder_path_too_broad,
)

HIGH_RISK_PATHS = [
    # Drive / filesystem roots
    "C:\\",
    "D:\\",
    "E:\\",
    "C:/",
    "/",
    # Windows system directories
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\Users",
    # Windows user profile root
    "C:\\Users\\ADMIN",
    "C:\\Users\\Ashif",
    # Windows sensitive home children that remain hard-blocked
    "C:\\Users\\ADMIN\\AppData",
    "C:\\Users\\ADMIN\\OneDrive",
    "C:\\Users\\ADMIN\\OneDrive - Bizpole",
    # Linux
    "/home",
    "/root",
    "/etc",
    "/usr",
    "/home/ashif",
    # macOS
    "/System",
    "/Applications",
    "/private",
    "/Users",
    "/Users/ashif",
]

MEDIUM_RISK_PATHS = [
    "C:\\Users\\ADMIN\\Desktop",
    "C:\\Users\\ADMIN\\Downloads",
    "C:\\Users\\ADMIN\\Documents",
    "C:\\Users\\ADMIN\\Pictures",
    "/Users/ashif/Desktop",
    "/Users/ashif/Downloads",
    "/home/ashif/Documents",
    "/home/ashif/Pictures",
]

LOW_RISK_PATHS = [
    "C:\\Users\\ADMIN\\Documents\\Reports",
    "D:\\MT\\calendar-reminder",
    "D:\\Projects",
    "C:\\Invoices",
    "C:\\Users\\ADMIN\\Documents\\CompanyData",
    "/home/ashif/Projects",
    "/Users/ashif/Documents/Archives",
    "C:\\Uploads",
]


@pytest.mark.parametrize("path", HIGH_RISK_PATHS)
def test_high_risk_paths_are_classified_and_blocked(path: str) -> None:
    assessment = classify_folder_risk(path)
    assert assessment.level == "high"
    assert assessment.recommendation == RECOMMENDATION_HIGH
    assert assessment.reason
    assert is_folder_path_too_broad(path) is True


@pytest.mark.parametrize("path", MEDIUM_RISK_PATHS)
def test_medium_risk_paths_are_classified_but_allowed(path: str) -> None:
    assessment = classify_folder_risk(path)
    assert assessment.level == "medium"
    assert assessment.recommendation == RECOMMENDATION_MEDIUM
    assert assessment.reason
    assert is_folder_path_too_broad(path) is False


@pytest.mark.parametrize("path", LOW_RISK_PATHS)
def test_low_risk_paths_are_classified_and_allowed(path: str) -> None:
    assessment = classify_folder_risk(path)
    assert assessment.level == "low"
    assert assessment.recommendation == RECOMMENDATION_LOW
    assert is_folder_path_too_broad(path) is False


def test_empty_path_is_high_risk() -> None:
    assessment = classify_folder_risk("")
    assert assessment.level == "high"
    assert is_folder_path_too_broad("") is True
    assert is_folder_path_too_broad("   ") is True


def test_traversal_is_caught_via_resolved_path() -> None:
    assessment = classify_folder_risk("C:\\Users\\ADMIN\\Documents\\..\\..\\Windows", "C:\\Windows")
    assert assessment.level == "high"
    assert is_folder_path_too_broad("C:\\Users\\ADMIN\\Documents\\..\\..\\Windows", "C:\\Windows") is True


def test_resolved_path_alone_does_not_over_block_legit_subfolder() -> None:
    assessment = classify_folder_risk("D:\\MT\\calendar-reminder", "D:\\MT\\calendar-reminder")
    assert assessment.level == "low"
