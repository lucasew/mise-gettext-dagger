#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Script to download and verify GPG signatures for gettext tarballs
"""
import argparse
import subprocess
import sys
from pathlib import Path
import requests


# Valid GPG keys for Bruno Haible (gettext maintainer)
VALID_KEYS = [
    "B6301D9E1BBEAC08",
    "F5BE8B267C6A406D",
    "4F494A942E4616C2"
]


def download_file(url: str, output_path: Path) -> bool:
    """Download a file from URL to output_path"""
    try:
        print(f"Downloading {url}...")
        res = requests.get(url, timeout=60, stream=True)
        res.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded to {output_path}")
        return True
    except requests.RequestException as e:
        print(f"ERROR: Failed to download {url}: {e}", file=sys.stderr)
        return False


def import_gpg_keys(keys: list) -> bool:
    """Import GPG keys from keyserver"""
    try:
        print(f"Importing GPG keys: {', '.join(keys)}")
        result = subprocess.run(
            ["gpg", "--recv-keys", *keys],
            capture_output=True,
            text=True,
            check=True
        )
        print("GPG keys imported successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to import GPG keys: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("ERROR: gpg command not found. Please install GnuPG.", file=sys.stderr)
        return False


def verify_signature(tarball: Path, signature: Path) -> bool:
    """Verify GPG signature of tarball"""
    try:
        print(f"Verifying signature for {tarball}...")
        result = subprocess.run(
            ["gpg", "--verify", str(signature), str(tarball)],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ Signature verification successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Signature verification failed: {e.stderr}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download and verify gettext tarball with GPG signature"
    )
    parser.add_argument("version", help="Gettext version to download")
    parser.add_argument(
        "--mirror",
        default="https://mirrors.ocf.berkeley.edu/gnu/gettext",
        help="Mirror URL (default: Berkeley OCF)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloads"),
        help="Output directory for downloads"
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip GPG verification (not recommended)"
    )

    args = parser.parse_args()

    # Construct URLs
    tarball_url = f"{args.mirror}/gettext-{args.version}.tar.gz"
    sig_url = f"{args.mirror}/gettext-{args.version}.tar.gz.sig"

    # Output paths
    tarball_path = args.output_dir / f"gettext-{args.version}.tar.gz"
    sig_path = args.output_dir / f"gettext-{args.version}.tar.gz.sig"

    # Download tarball
    if not download_file(tarball_url, tarball_path):
        return 1

    if args.skip_verify:
        print("WARNING: Skipping GPG verification")
        return 0

    # Download signature
    if not download_file(sig_url, sig_path):
        return 1

    # Import GPG keys
    if not import_gpg_keys(VALID_KEYS):
        return 1

    # Verify signature
    if not verify_signature(tarball_path, sig_path):
        return 1

    print(f"\n✓ Successfully downloaded and verified gettext {args.version}")
    print(f"  Tarball: {tarball_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
