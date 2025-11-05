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

# List of GNU mirrors to try
MIRRORS = [
    "https://ftp.gnu.org/gnu/gettext",
    "https://ftpmirror.gnu.org/gettext",
    "https://mirrors.ocf.berkeley.edu/gnu/gettext",
    "https://mirror.dogado.de/gnu/gettext",
    "https://mirror.checkdomain.de/gnu/gettext",
    "https://ftp.cc.uoc.gr/mirrors/gnu/gettext",
]


def download_file_with_retry(filename: str, output_path: Path, mirrors: list) -> bool:
    """Download a file with retry across multiple mirrors"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error = None
    for mirror in mirrors:
        url = f"{mirror}/{filename}"
        try:
            print(f"Trying {url}...")
            res = requests.get(url, timeout=60, stream=True)
            res.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✓ Downloaded from {mirror}")
            return True
        except requests.RequestException as e:
            print(f"✗ Failed to download from {mirror}: {e}", file=sys.stderr)
            last_error = e
            continue

    print(f"ERROR: Failed to download {filename} from all mirrors!", file=sys.stderr)
    if last_error:
        print(f"Last error: {last_error}", file=sys.stderr)
    return False


def import_gpg_keys(keys: list) -> bool:
    """Import GPG keys from keyserver with retry logic"""
    keyservers = [
        "hkps://keys.openpgp.org",
        "hkps://keyserver.ubuntu.com",
        "hkps://pgp.mit.edu",
    ]

    print(f"Importing GPG keys: {', '.join(keys)}")

    for keyserver in keyservers:
        try:
            print(f"  Trying keyserver: {keyserver}")
            result = subprocess.run(
                ["gpg", "--keyserver", keyserver, "--recv-keys", *keys],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            print("✓ GPG keys imported successfully")
            return True
        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout from {keyserver}")
            continue
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed with {keyserver}: {e.stderr.strip()}")
            continue
        except FileNotFoundError:
            print("ERROR: gpg command not found. Please install GnuPG.", file=sys.stderr)
            return False

    print("ERROR: Failed to import GPG keys from all keyservers", file=sys.stderr)
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
        help="Additional mirror URL to try first"
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
        help="Skip GPG verification entirely (not recommended)"
    )
    parser.add_argument(
        "--allow-insecure",
        action="store_true",
        help="Continue even if GPG verification fails (show warning only)"
    )

    args = parser.parse_args()

    # Build mirror list (custom mirror first if provided, then defaults)
    mirrors = []
    if args.mirror:
        mirrors.append(args.mirror)
    mirrors.extend(MIRRORS)

    # Output paths
    tarball_path = args.output_dir / f"gettext-{args.version}.tar.gz"
    sig_path = args.output_dir / f"gettext-{args.version}.tar.gz.sig"

    # Download tarball with retry
    tarball_filename = f"gettext-{args.version}.tar.gz"
    if not download_file_with_retry(tarball_filename, tarball_path, mirrors):
        return 1

    if args.skip_verify:
        print("=" * 60)
        print("WARNING: Skipping GPG verification (--skip-verify)")
        print("=" * 60)
        return 0

    # Download signature with retry
    sig_filename = f"gettext-{args.version}.tar.gz.sig"
    if not download_file_with_retry(sig_filename, sig_path, mirrors):
        if args.allow_insecure:
            print("=" * 60)
            print("WARNING: Could not download signature, continuing anyway")
            print("=" * 60)
            return 0
        return 1

    # Import GPG keys
    if not import_gpg_keys(VALID_KEYS):
        if args.allow_insecure:
            print("=" * 60)
            print("WARNING: Could not import GPG keys, continuing anyway")
            print("=" * 60)
            return 0
        return 1

    # Verify signature
    if not verify_signature(tarball_path, sig_path):
        if args.allow_insecure:
            print("=" * 60)
            print("WARNING: GPG signature verification FAILED!")
            print("WARNING: Continuing build anyway (--allow-insecure)")
            print("WARNING: This tarball could be tampered with!")
            print("=" * 60)
            return 0
        return 1

    print(f"\n✓ Successfully downloaded and verified gettext {args.version}")
    print(f"  Tarball: {tarball_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
