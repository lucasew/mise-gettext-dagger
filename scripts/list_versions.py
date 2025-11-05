#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.31.0",
#     "beautifulsoup4>=4.12.0",
# ]
# ///
"""
Script to fetch available gettext versions from GNU mirror
"""
import re
import sys
from typing import List
import requests
from bs4 import BeautifulSoup


def get_versions() -> List[str]:
    """Fetch all available gettext versions from GNU mirror with fallback"""
    regex = r"gettext-(?P<version>.*?)\.tar\.gz(?P<sig>\.sig)?"

    # List of mirrors to try
    mirrors = [
        "https://ftp.gnu.org/gnu/gettext/",
        "https://ftpmirror.gnu.org/gettext/",
        "https://mirrors.ocf.berkeley.edu/gnu/gettext/",
        "https://mirror.dogado.de/gnu/gettext/",
        "https://mirror.checkdomain.de/gnu/gettext/",
        "https://ftp.cc.uoc.gr/mirrors/gnu/gettext/",
    ]

    last_error = None
    for url in mirrors:
        try:
            print(f"Trying {url}...", file=sys.stderr)
            res = requests.get(url, timeout=30)
            res.raise_for_status()
            print(f"✓ Successfully fetched from {url}", file=sys.stderr)

            tree = BeautifulSoup(res.text, 'html.parser')
            versions = set()

            table = tree.find("table")
            if not table:
                print(f"WARNING: Could not find version table at {url}", file=sys.stderr)
                continue

            for item in table.find_all('a'):
                name = item.text
                match = re.match(regex, name)
                if match:
                    version = match.group('version')
                    if not match.group('sig'):  # Only add if it's the tarball, not signature
                        versions.add(version)

            if versions:
                return sorted(versions)
            else:
                print(f"WARNING: No versions found at {url}", file=sys.stderr)
                continue

        except requests.RequestException as e:
            print(f"✗ Failed to fetch from {url}: {e}", file=sys.stderr)
            last_error = e
            continue

    print(f"ERROR: Failed to fetch versions from all mirrors!", file=sys.stderr)
    if last_error:
        print(f"Last error: {last_error}", file=sys.stderr)
    sys.exit(1)


def main():
    versions = get_versions()
    for version in versions:
        print(version)
    return 0


if __name__ == '__main__':
    sys.exit(main())
