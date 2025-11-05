# gettext-bin

Cross-platform build system for GNU gettext binaries using Docker containers.

## Overview

This project builds static binaries of GNU gettext for multiple platforms:
- **linux-amd64** - Linux x86_64
- **linux-aarch64** - Linux ARM64
- **windows-amd64** - Windows x86_64

All builds run inside Docker containers (`ghcr.io/actions-precompiled/buildenv:0.0.1`) ensuring reproducible, consistent builds across different host systems.

## Prerequisites

- **Docker** - For containerized builds
- **CMake 3.20+** - Build system
- **uv** - Python package manager (for helper scripts)
- **GnuPG** - For GPG signature verification
- **GitHub CLI (gh)** - For automated releases (optional)

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with mise
mise use -g uv
```

## Quick Start

### Build a Specific Version and Target

```bash
# Set environment variables
export GETTEXT_VERSION=0.22.5
export BUILD_TARGET=linux-amd64

# Configure and build
cmake -B build
cmake --build build

# Output: build/out/0.22.5-linux-amd64.tar.gz
```

### Build Multiple Targets

```bash
# Build for all platforms
./create_releases 0.22.5

# Build for specific platforms
TARGETS="linux-amd64 linux-aarch64" ./create_releases 0.22.5
```

## How It Works

1. **Download & Verify**: Downloads gettext source tarball and verifies GPG signature
2. **Docker Build**: Runs `docker-build.sh` inside buildenv container with `BUILD_TARGET` set
3. **Configure & Compile**: Script automatically selects toolchain and builds gettext
4. **Package**: Creates tarball with installed binaries

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  create_releases (bash)                                 │
│  ├─ Iterates over BUILD_TARGET (linux-amd64, ...)      │
│  └─ Calls CMake for each target                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  CMakeLists.txt                                         │
│  ├─ Downloads & verifies source (scripts/verify_gpg.py)│
│  ├─ Runs docker with BUILD_TARGET env var              │
│  └─ Mounts /src (ro) and /out (rw)                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  ghcr.io/actions-precompiled/buildenv:0.0.1             │
│  └─ Executes /src/docker-build.sh                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  docker-build.sh                                        │
│  ├─ Downloads tarball                                  │
│  ├─ Configures with appropriate --host based on TARGET │
│  ├─ Builds with make -j$(nproc)                        │
│  └─ Creates .tar.gz in /out                            │
└─────────────────────────────────────────────────────────┘
```

## Automated Releases

### create_releases Script

The `create_releases` script automates building and uploading to GitHub releases:

```bash
# Build specific versions
./create_releases 0.22.5 0.22.4

# Auto-detect missing versions
./create_releases

# Test build without creating releases
LOCAL_BUILD=1 ./create_releases 0.22.5

# Dry run
DRY_RUN=1 ./create_releases
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GETTEXT_VERSION` | Version to build | 0.22.5 |
| `BUILD_TARGET` | Target platform | linux-amd64 |
| `TARGETS` | Space-separated list of targets | `linux-amd64 linux-aarch64 windows-amd64` |
| `BUILDENV_VERSION` | Docker image version | 0.0.1 |
| `LOCAL_BUILD` | Skip GitHub release creation | (unset) |
| `DRY_RUN` | Show what would be built | (unset) |

## GitHub Actions Workflows

### PR Build Test (`.github/workflows/pr-build-test.yml`)

Runs on every pull request to validate builds:
- Builds linux-amd64 target only
- Uses `LOCAL_BUILD=1` to skip release creation
- Uploads artifacts for inspection

### Build Releases (`.github/workflows/build-releases.yml`)

Scheduled weekly (Saturdays 2:00 AM UTC) or manually triggered:
- Builds all missing versions for all targets
- Creates GitHub releases
- Uploads tarballs

Trigger manually:
```bash
gh workflow run build-releases.yml
```

## CMake Configuration

### Build Options

| CMake Variable | Description | Default |
|----------------|-------------|---------|
| `GETTEXT_VERSION` | Version to build | 0.22.5 |
| `BUILD_TARGET` | Target platform | linux-amd64 |
| `BUILDENV_IMAGE` | Docker image | `ghcr.io/actions-precompiled/buildenv` |
| `BUILDENV_VERSION` | Docker tag | 0.0.1 |
| `GETTEXT_MIRROR` | Download mirror | Berkeley OCF |

### Example: Custom Build Environment

```bash
cmake -B build \
  -DGETTEXT_VERSION=0.22.5 \
  -DBUILD_TARGET=linux-aarch64 \
  -DBUILDENV_VERSION=0.0.2
```

## Helper Scripts

### `scripts/list_versions.py`

Lists all available gettext versions from GNU mirror:

```bash
./scripts/list_versions.py
```

### `scripts/verify_gpg.py`

Downloads and verifies tarball GPG signature:

```bash
./scripts/verify_gpg.py 0.22.5 --output-dir downloads
```

Verifies against Bruno Haible's GPG keys:
- `B6301D9E1BBEAC08`
- `F5BE8B267C6A406D`
- `4F494A942E4616C2`

## Output Structure

```
target/
└── 0.22.5/
    ├── 0.22.5-linux-amd64.tar.gz
    ├── 0.22.5-linux-aarch64.tar.gz
    ├── 0.22.5-windows-amd64.tar.gz
    └── 0.22.5-src.tar.gz
```

Each tarball contains the complete gettext installation (bin, lib, include, share).

## Troubleshooting

### Docker not found

```bash
# Check Docker installation
docker version

# Install Docker
# https://docs.docker.com/engine/install/
```

### Container pull fails

```bash
# Pull manually
docker pull ghcr.io/actions-precompiled/buildenv:0.0.1

# Login to GHCR if needed (for private images)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### GPG verification fails

```bash
# Import keys manually
gpg --recv-keys B6301D9E1BBEAC08 F5BE8B267C6A406D 4F494A942E4616C2

# Or skip verification (not recommended)
# Edit scripts/verify_gpg.py to add --skip-verify flag
```

### Build fails inside container

```bash
# Run container interactively to debug
docker run -it --rm \
  -v $(pwd):/src:ro \
  -v $(pwd)/debug-out:/out \
  -e GETTEXT_VERSION=0.22.5 \
  -e BUILD_TARGET=linux-amd64 \
  ghcr.io/actions-precompiled/buildenv:0.0.1 \
  bash

# Inside container, run commands manually
cd /src
./docker-build.sh
```

## Development

### Local Testing

```bash
# Test single target build
LOCAL_BUILD=1 TARGETS="linux-amd64" ./create_releases 0.22.5

# Verify artifacts
ls -lh target/0.22.5/
tar -tzf target/0.22.5/0.22.5-linux-amd64.tar.gz | head
```

### Adding New Targets

1. Update `docker-build.sh` with new case in switch statement
2. Ensure buildenv container has required toolchain
3. Add target to `TARGETS` default in `create_releases`
4. Test build locally

## Migration from Dagger

This project was migrated from Dagger to a CMake + Docker approach for:

- ✅ **Pinned dependencies**: Buildenv version explicitly specified
- ✅ **Standard tooling**: CMake instead of custom Dagger SDK
- ✅ **Simplified CI**: No Dagger Engine required in CI
- ✅ **Easier debugging**: Can run Docker container manually
- ✅ **Build caching**: Docker layer caching works automatically

Old Dagger configuration preserved in `.dagger/` for reference.

## License

This project follows the same license as GNU gettext (GPL-3.0).

## Related Projects

- [actions-precompiled/buildenv](https://github.com/actions-precompiled/buildenv) - Docker build environment
- [actions-precompiled/tesseract-bin](https://github.com/actions-precompiled/tesseract-bin) - Similar project for Tesseract OCR
