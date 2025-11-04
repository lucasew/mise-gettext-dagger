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
    """Fetch all available gettext versions from GNU mirror"""
    regex = r"gettext-(?P<version>.*?)\.tar\.gz(?P<sig>\.sig)?"
    url = "https://ftp.gnu.org/gnu/gettext/"

    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch versions from {url}: {e}", file=sys.stderr)
        sys.exit(1)

    tree = BeautifulSoup(res.text, 'html.parser')
    versions = set()

    table = tree.find("table")
    if not table:
        print("ERROR: Could not find version table", file=sys.stderr)
        sys.exit(1)

    for item in table.find_all('a'):
        name = item.text
        match = re.match(regex, name)
        if match:
            version = match.group('version')
            if not match.group('sig'):  # Only add if it's the tarball, not signature
                versions.add(version)

    return sorted(versions)


def main():
    versions = get_versions()
    for version in versions:
        print(version)
    return 0


if __name__ == '__main__':
    sys.exit(main())
