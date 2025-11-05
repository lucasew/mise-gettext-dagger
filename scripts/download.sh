#!/bin/bash
set -euo pipefail

# Download gettext tarball from multiple mirrors with fallback
# Usage: download.sh <version> <output_file> [primary_mirror]

VERSION="${1}"
OUTPUT_FILE="${2}"
PRIMARY_MIRROR="${3:-}"

# List of GNU mirrors to try (ftp.gnu.org last since it's often slow)
MIRRORS=(
    "${PRIMARY_MIRROR}"
    'https://mirrors.ocf.berkeley.edu/gnu/gettext'
    'https://mirror.dogado.de/gnu/gettext'
    'https://mirror.checkdomain.de/gnu/gettext'
    'https://ftp.cc.uoc.gr/mirrors/gnu/gettext'
    'https://ftpmirror.gnu.org/gettext'
    'https://ftp.gnu.org/gnu/gettext'
)

FILENAME="gettext-${VERSION}.tar.gz"
SUCCESS=0

for mirror in "${MIRRORS[@]}"; do
    # Skip empty mirror entries
    if [ -z "${mirror}" ]; then
        continue
    fi

    url="${mirror}/${FILENAME}"
    echo "Trying ${url}..."

    # Try downloading with curl (timeout 30s, 3 retries, 2s delay between retries)
    if curl --fail --location --silent --show-error \
            --max-time 30 --retry 3 --retry-delay 2 \
            --output "${OUTPUT_FILE}" "${url}"; then
        echo "✓ Successfully downloaded from ${mirror}"
        SUCCESS=1
        break
    else
        echo "✗ Failed to download from ${mirror}"
    fi
done

if [ ${SUCCESS} -eq 0 ]; then
    echo "ERROR: Failed to download from all mirrors!"
    exit 1
fi
