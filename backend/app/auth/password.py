"""Password policy validation.

Rules (all violations are reported at once, not fail-fast):
- length >= 8
- at least one uppercase letter
- at least one lowercase letter
- at least one digit
- at least one special character
- not present in the bundled common-password blocklist
"""

import re
from pathlib import Path

_COMMON_PASSWORDS_PATH = Path(__file__).resolve().parent / "data" / "common_passwords.txt"

_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
_SPECIAL_CHARS_PATTERN = re.compile(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]")

MIN_LENGTH = 8


def _load_common_passwords() -> frozenset[str]:
    if not _COMMON_PASSWORDS_PATH.exists():
        return frozenset()

    entries: set[str] = set()
    with _COMMON_PASSWORDS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip().lower()
            if stripped:
                entries.add(stripped)
    return frozenset(entries)


COMMON_PASSWORDS: frozenset[str] = _load_common_passwords()


class PasswordPolicyError(Exception):
    """Raised when a password fails one or more policy rules."""

    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def validate_password_policy(password: str) -> None:
    violations: list[str] = []

    if len(password) < MIN_LENGTH:
        violations.append(f"Password must be at least {MIN_LENGTH} characters long.")
    if not re.search(r"[A-Z]", password):
        violations.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        violations.append("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        violations.append("Password must contain at least one digit.")
    if not _SPECIAL_CHARS_PATTERN.search(password):
        violations.append(f"Password must contain at least one special character ({_SPECIAL_CHARS}).")
    if password.lower() in COMMON_PASSWORDS:
        violations.append("Password is too common; please choose a less predictable password.")

    if violations:
        raise PasswordPolicyError(violations)
