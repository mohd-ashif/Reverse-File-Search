from pathlib import Path

# Extensions that are almost always private key/credential material.
SENSITIVE_EXTENSIONS = frozenset({".pem", ".key", ".pfx", ".kdbx"})

# Exact filenames (case-insensitive) known to hold secrets regardless of extension.
SENSITIVE_FILENAMES = frozenset({
    "wallet.dat",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    "credentials.json",
    "passwords.txt",
})

# Filename prefixes matched case-insensitively, covering .env, .env.local, .env.production, etc.
SENSITIVE_NAME_PREFIXES = (".env",)


def is_sensitive_file(path: str | Path) -> bool:
    """True if `path` looks like it holds secrets (keys, credentials, env files)
    and should be excluded from indexing by default."""
    name = Path(path).name.lower()

    if name.startswith(SENSITIVE_NAME_PREFIXES):
        return True
    if name in SENSITIVE_FILENAMES:
        return True
    return Path(path).suffix.lower() in SENSITIVE_EXTENSIONS
