# gettext-bin

CMake-based build system for cross-compiling GNU gettext for multiple platforms using Docker containers.

## Overview

This project builds static binaries of GNU gettext for:
- Linux x86_64 (amd64)
- Linux ARM64 (aarch64)
- Windows x86_64 (optional)

All builds are performed inside Docker containers using a pre-configured build environment, ensuring reproducible builds across different host systems.

## Prerequisites

### Required
- CMake 3.20 or higher
- Docker (for containerized builds)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- GnuPG (for GPG signature verification)

### Build Container

The build uses a pre-configured Docker image: `ghcr.io/actions-precompiled/buildenv:0.0.1`

This container includes all necessary cross-compilation toolchains:
- Native GCC/G++ for x86_64
- `gcc-aarch64-linux-gnu` for ARM64 cross-compilation
- `mingw-w64` for Windows cross-compilation

### Python Dependencies

The scripts use `uv` with inline script metadata (PEP 723), so dependencies are automatically managed when you run the scripts. No manual installation required!

Install `uv`:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with mise (recommended)
mise use -g uv

# Or with pip
pip install uv
```

## Quick Start

### Build a Specific Version

```bash
# Configure
cmake -B build -DGETTEXT_VERSION=0.22.5

# Build
cmake --build build -j$(nproc)

# Output will be in: build/target/0.22.5/
```

### Build for Specific Platforms

```bash
cmake -B build \
  -DGETTEXT_VERSION=0.22.5 \
  -DBUILD_PLATFORMS="linux-amd64;linux-aarch64"

cmake --build build
```

### List Available Versions

```bash
./scripts/list_versions.py
```

### Download and Verify Source

```bash
./scripts/verify_gpg.py 0.22.5 --output-dir downloads
```

## Automated Release Build

The `create_releases` script automates building and uploading releases to GitHub:

```bash
# Build specific versions
./create_releases 0.22.5 0.22.4

# Build all missing versions (compares with GitHub releases)
./create_releases

# Dry run (show what would be built)
DRY_RUN=1 ./create_releases
```

### Environment Variables

- `BUILD_DIR`: Build directory (default: `build`)
- `PLATFORMS`: Space-separated list of platforms (default: `linux-amd64 linux-aarch64`)
- `DRY_RUN`: If set, only show what would be built without building

## Project Structure

```
.
├── CMakeLists.txt              # Main CMake configuration (Docker-based builds)
├── scripts/
│   ├── list_versions.py        # Fetch available gettext versions (uv script)
│   └── verify_gpg.py           # Download and verify GPG signatures (uv script)
├── create_releases             # Automated release build script
└── README.md                   # This file
```

## How It Works

1. **GPG Verification**: Downloads gettext source tarball and verifies GPG signature
2. **Docker Pull**: Pulls the build environment image (`ghcr.io/actions-precompiled/buildenv`)
3. **Containerized Build**: Runs `./configure && make && make install` inside Docker for each platform
4. **Tarball Creation**: Packages the installed files into platform-specific tarballs

## GPG Verification

All downloads are verified against Bruno Haible's GPG keys:
- B6301D9E1BBEAC08
- F5BE8B267C6A406D
- 4F494A942E4616C2

To skip verification (not recommended):
```bash
./scripts/verify_gpg.py 0.22.5 --skip-verify
```

## CMake Options

| Option | Description | Default |
|--------|-------------|---------|
| `GETTEXT_VERSION` | Version to build | 0.22.5 |
| `BUILD_PLATFORMS` | Semicolon-separated list of platforms | `linux-amd64;linux-aarch64` |
| `GETTEXT_MIRROR` | Download mirror URL | Berkeley OCF mirror |
| `BUILDENV_IMAGE` | Docker build environment image | `ghcr.io/actions-precompiled/buildenv` |
| `BUILDENV_VERSION` | Docker image version/tag | `0.0.1` |

### Example: Pin a Different Container Version

```bash
cmake -B build \
  -DGETTEXT_VERSION=0.22.5 \
  -DBUILDENV_VERSION=0.0.2
```

## Output Format

Built artifacts are packaged as tarballs:
```
build/target/{version}/
├── {version}-linux-amd64.tar.gz
├── {version}-linux-aarch64.tar.gz
└── {version}-src.tar.gz
```

Each tarball contains the complete gettext installation (bin, lib, include, share).

## Troubleshooting

### Docker daemon not running

Make sure Docker is installed and running:
```bash
# Check Docker status
docker version

# Start Docker (Linux)
sudo systemctl start docker

# Or use Docker Desktop (macOS/Windows)
```

### Container pull fails

Check your network connection and Docker Hub/GHCR access:
```bash
# Manually pull the image
docker pull ghcr.io/actions-precompiled/buildenv:0.0.1

# Login to GHCR if needed (for private images)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### GPG key import fails

Import keys manually:
```bash
gpg --recv-keys B6301D9E1BBEAC08 F5BE8B267C6A406D 4F494A942E4616C2
```

## Migration from Dagger

This project was migrated from Dagger to CMake with Docker for:
- ✓ Better reproducibility with pinned container versions
- ✓ Standard build system tooling (CMake)
- ✓ Explicit dependency management (Docker image)
- ✓ Simpler CI/CD integration
- ✓ Faster local builds with caching

The old Dagger configuration is preserved in `.dagger/` for reference.

## Build Environment Container

The Docker build environment (`ghcr.io/actions-precompiled/buildenv`) contains:
- Debian Stable base
- GCC/G++ native toolchain
- Cross-compilation toolchains for ARM64 and Windows
- Build essentials (make, autotools, etc.)

To use a custom build environment, override the `BUILDENV_IMAGE` and `BUILDENV_VERSION` CMake variables.
