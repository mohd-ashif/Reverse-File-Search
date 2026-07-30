"""Generate the RS256 JWT signing keypair used by app.auth.jwt.

Usage:
    python scripts/generate_jwt_keys.py
    python scripts/generate_jwt_keys.py --force
"""

import argparse
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KEYS_DIR = Path(__file__).resolve().parent.parent / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "jwt_private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "jwt_public.pem"


def generate_keys(force: bool = False) -> None:
    if not force and (PRIVATE_KEY_PATH.exists() or PUBLIC_KEY_PATH.exists()):
        print(
            "Error: one or more key files already exist "
            f"({PRIVATE_KEY_PATH}, {PUBLIC_KEY_PATH}). Use --force to overwrite."
        )
        sys.exit(1)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_KEY_PATH.write_bytes(private_pem)
    PUBLIC_KEY_PATH.write_bytes(public_pem)

    print("Generated RS256 JWT keypair:")
    print(f"  Private key: {PRIVATE_KEY_PATH}")
    print(f"  Public key:  {PUBLIC_KEY_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="Overwrite existing key files if present")
    args = parser.parse_args()

    generate_keys(force=args.force)


if __name__ == "__main__":
    main()
