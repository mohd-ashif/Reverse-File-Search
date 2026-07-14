"""Verifies a folder path is safely accessible before it can be monitored:
exists, is a directory, is readable, isn't locked by another process, and
isn't an unreachable network location. Raises a specific, descriptive
exception per failure mode so the API and frontend can surface the exact
cause instead of a generic failure.
"""

import os
from pathlib import Path

# Windows error codes surfaced via OSError.winerror (absent on other platforms).
_NETWORK_WINERRORS = {53, 67, 1231}  # network path/name not found, network unreachable
_LOCKED_WINERRORS = {32, 33}  # file in use by another process, lock violation


class FolderPathInvalidError(Exception):
    pass


class FolderPathMissingError(Exception):
    pass


class FolderPermissionDeniedError(Exception):
    pass


class FolderLockedError(Exception):
    pass


class FolderNetworkUnavailableError(Exception):
    pass


def _is_network_path(raw_path: str, resolved: Path) -> bool:
    return raw_path.strip().startswith("\\\\") or str(resolved.drive).startswith("\\\\")


def _raise_for_os_error(exc: OSError, raw_path: str, resolved: Path) -> None:
    winerror = getattr(exc, "winerror", None)

    if winerror in _NETWORK_WINERRORS or (_is_network_path(raw_path, resolved) and winerror is None):
        raise FolderNetworkUnavailableError(
            f"'{raw_path}' is a network location that is currently unreachable. "
            "Check the network connection and that the share is still shared."
        ) from exc
    if winerror in _LOCKED_WINERRORS:
        raise FolderLockedError(
            f"'{raw_path}' is locked by another process and cannot be accessed right now."
        ) from exc
    raise FolderPathInvalidError(f"'{raw_path}' could not be accessed: {exc.strerror or exc}.") from exc


def verify_folder_access(raw_path: str, resolved: Path) -> None:
    """Raises a descriptive exception if `resolved` cannot be safely
    monitored. `resolved` must be the expanded/resolved form of `raw_path`."""

    if not raw_path or not raw_path.strip():
        raise FolderPathInvalidError("No folder path was provided.")

    try:
        resolved.stat()
    except FileNotFoundError as exc:
        raise FolderPathMissingError(f"'{raw_path}' does not exist.") from exc
    except NotADirectoryError as exc:
        raise FolderPathInvalidError(
            f"'{raw_path}' is not a valid folder path — part of it is a file, not a folder."
        ) from exc
    except PermissionError as exc:
        raise FolderPermissionDeniedError(f"Permission denied: cannot access '{raw_path}'.") from exc
    except OSError as exc:
        _raise_for_os_error(exc, raw_path, resolved)

    if not resolved.is_dir():
        raise FolderPathInvalidError(f"'{raw_path}' is not a folder.")

    if not os.access(resolved, os.R_OK):
        raise FolderPermissionDeniedError(f"Permission denied: cannot read '{raw_path}'.")

    try:
        with os.scandir(resolved) as entries:
            next(entries, None)
    except PermissionError as exc:
        raise FolderPermissionDeniedError(
            f"Permission denied: cannot list the contents of '{raw_path}'."
        ) from exc
    except NotADirectoryError as exc:
        raise FolderPathInvalidError(f"'{raw_path}' is not a folder.") from exc
    except OSError as exc:
        _raise_for_os_error(exc, raw_path, resolved)
