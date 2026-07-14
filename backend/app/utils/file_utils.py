import hashlib
from pathlib import Path


def compute_checksum(file_path: str | Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
