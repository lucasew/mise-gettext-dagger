#!/bin/bash
set -euo pipefail

# This script runs inside the buildenv container
# Environment variables expected:
#   GETTEXT_VERSION - version to build (e.g., "0.22.5")
#   BUILD_TARGET - target platform (e.g., "linux-amd64", "linux-aarch64", "windows-amd64")

# Validate required environment variables
if [ -z "${GETTEXT_VERSION:-}" ]; then
    echo "ERROR: GETTEXT_VERSION environment variable is required"
    exit 1
fi

if [ -z "${BUILD_TARGET:-}" ]; then
    echo "ERROR: BUILD_TARGET environment variable is required"
    exit 1
fi

echo "============================================"
echo "Building gettext ${GETTEXT_VERSION} for ${BUILD_TARGET}"
echo "============================================"

# Configuration
MIRROR="${GETTEXT_MIRROR:-https://mirrors.ocf.berkeley.edu/gnu/gettext}"
TARBALL_URL="${MIRROR}/gettext-${GETTEXT_VERSION}.tar.gz"
BUILD_DIR="/tmp/build"
INSTALL_PREFIX="/tmp/install"
OUTPUT_DIR="/out"

# Create working directories
mkdir -p "${BUILD_DIR}"
mkdir -p "${INSTALL_PREFIX}"
mkdir -p "${OUTPUT_DIR}"

# Download tarball (with GPG verification already done by CMake)
echo "Downloading gettext ${GETTEXT_VERSION}..."
cd /tmp
wget -q "${TARBALL_URL}" -O "gettext-${GETTEXT_VERSION}.tar.gz"

# Extract source
echo "Extracting source..."
tar -xzf "gettext-${GETTEXT_VERSION}.tar.gz" -C "${BUILD_DIR}" --strip-components=1

# Configure based on target platform
cd "${BUILD_DIR}"
echo "Configuring for ${BUILD_TARGET}..."

case "${BUILD_TARGET}" in
    linux-amd64)
        CONFIGURE_OPTS=(
            --prefix="${INSTALL_PREFIX}"
            --disable-shared
            --enable-static
        )
        ;;
    linux-aarch64)
        CONFIGURE_OPTS=(
            --prefix="${INSTALL_PREFIX}"
            --host=aarch64-linux-gnu
            --build=x86_64-linux-gnu
            --disable-shared
            --enable-static
        )
        export CC=aarch64-linux-gnu-gcc
        export CXX=aarch64-linux-gnu-g++
        ;;
    windows-amd64)
        CONFIGURE_OPTS=(
            --prefix="${INSTALL_PREFIX}"
            --host=x86_64-w64-mingw32
            --target=x86_64-w64-mingw32
            --build=x86_64-linux-gnu
            --disable-shared
            --enable-static
        )
        export CC=x86_64-w64-mingw32-gcc
        export CXX=x86_64-w64-mingw32-g++
        ;;
    *)
        echo "ERROR: Unknown BUILD_TARGET: ${BUILD_TARGET}"
        echo "Supported targets: linux-amd64, linux-aarch64, windows-amd64"
        exit 1
        ;;
esac

./configure "${CONFIGURE_OPTS[@]}"

# Build
echo "Building gettext..."
make -j"$(nproc)"

# Install
echo "Installing to ${INSTALL_PREFIX}..."
make install

# Create tarball
echo "Creating output tarball..."
cd "${INSTALL_PREFIX}"
tar -czf "${OUTPUT_DIR}/${GETTEXT_VERSION}-${BUILD_TARGET}.tar.gz" .

# Also create source tarball (repackaged)
echo "Creating source tarball..."
cd /tmp
mkdir -p "${GETTEXT_VERSION}-src"
tar -xzf "gettext-${GETTEXT_VERSION}.tar.gz" -C "${GETTEXT_VERSION}-src" --strip-components=1
tar -czf "${OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz" "${GETTEXT_VERSION}-src"

# Summary
echo ""
echo "============================================"
echo "Build completed successfully!"
echo "============================================"
echo "Output files in ${OUTPUT_DIR}:"
ls -lh "${OUTPUT_DIR}"
echo ""
