"""Argon2id hashing round-trip and password-policy rule coverage."""

import pytest

from app.auth.password import PasswordPolicyError, validate_password_policy
from app.auth.security import hash_password, verify_password


def test_hash_password_round_trip() -> None:
    plaintext = "CorrectHorse!9"
    hashed = hash_password(plaintext)

    assert hashed != plaintext
    assert verify_password(plaintext, hashed) is True
    assert verify_password("WrongHorse!9", hashed) is False


def test_hash_password_is_argon2id() -> None:
    hashed = hash_password("SomePassword!1")
    assert hashed.startswith("$argon2id$")


def test_policy_fails_only_on_length() -> None:
    # Has upper/lower/digit/special, but only 7 chars.
    password = "Ab1!xyz"
    assert len(password) < 8

    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("at least 8 characters" in v for v in violations)
    assert not any("uppercase" in v for v in violations)
    assert not any("lowercase" in v for v in violations)
    assert not any("digit" in v for v in violations)
    assert not any("special character" in v for v in violations)
    assert not any("too common" in v for v in violations)


def test_policy_fails_only_on_missing_uppercase() -> None:
    password = "lowercase123!@#$"
    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("uppercase" in v for v in violations)
    assert len(violations) == 1


def test_policy_fails_only_on_missing_lowercase() -> None:
    password = "UPPERCASE123!@#$"
    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("lowercase" in v for v in violations)
    assert len(violations) == 1


def test_policy_fails_only_on_missing_digit() -> None:
    # 20 chars, upper+lower+special, no digit.
    password = "NoDigitsHereAtAll!!!"
    assert len(password) == 20
    assert not any(ch.isdigit() for ch in password)

    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("digit" in v for v in violations)
    assert len(violations) == 1


def test_policy_fails_only_on_missing_special_char() -> None:
    password = "NoSpecialChars123"
    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("special character" in v for v in violations)
    assert len(violations) == 1


def test_policy_rejects_common_password() -> None:
    # "password" is on the bundled blocklist (case-insensitive match).
    password = "password"
    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert any("too common" in v for v in violations)


def test_policy_reports_multiple_violations_at_once() -> None:
    password = "short"
    with pytest.raises(PasswordPolicyError) as excinfo:
        validate_password_policy(password)

    violations = excinfo.value.violations
    assert len(violations) > 1


def test_policy_passes_for_compliant_password() -> None:
    # Not on the common-password list, satisfies every character-class rule.
    validate_password_policy("Xk9!zqTrWv2#")
