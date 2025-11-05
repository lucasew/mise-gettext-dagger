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
- **uv** - Python package manager (for helper scripts)
- **GnuPG** - For GPG signature verification (optional)
- **GitHub CLI (gh)** - For automated releases (optional)

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with mise
mise use -g uv
```

## Quick Start

### Build Specific Version

```bash
# Build all platforms
./create_releases 0.22.5

# Build specific platforms only
TARGETS="linux-amd64" ./create_releases 0.22.5

# Test build without creating GitHub release
LOCAL_BUILD=1 ./create_releases 0.22.5
```

### Auto-detect and Build Missing Versions

```bash
# Automatically builds versions that don't have releases yet
./create_releases
```

## How It Works

The `create_releases` script orchestrates everything:

```
create_releases
  ├─ Pulls ghcr.io/actions-precompiled/buildenv:0.0.1
  ├─ For each TARGET (linux-amd64, linux-aarch64, windows-amd64):
  │   ├─ Generates build script inline
  │   ├─ Runs docker with:
  │   │   ├─ GETTEXT_VERSION env var
  │   │   ├─ BUILD_TARGET env var
  │   │   └─ /out volume mount
  │   └─ Inside container:
  │       ├─ Downloads tarball from GNU mirror
  │       ├─ Configures with appropriate --host for cross-compilation
  │       ├─ Builds with make -j$(nproc)
  │       ├─ Installs to /tmp/install
  │       └─ Creates tarballs in /out
  └─ Uploads to GitHub releases (unless LOCAL_BUILD=1)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TARGETS` | Space-separated list of targets | `linux-amd64 linux-aarch64 windows-amd64` |
| `BUILDENV_VERSION` | Docker image version | `0.0.1` |
| `BUILDENV_IMAGE` | Docker image | `ghcr.io/actions-precompiled/buildenv` |
| `GETTEXT_MIRROR` | Download mirror | `https://mirrors.ocf.berkeley.edu/gnu/gettext` |
| `LOCAL_BUILD` | Skip GitHub release creation | (unset) |
| `DRY_RUN` | Show what would be built | (unset) |

## Helper Scripts

### `scripts/list_versions.py`

Lists all available gettext versions from GNU mirror:

```bash
./scripts/list_versions.py
```

Uses `uv` with inline script metadata (PEP 723) - dependencies auto-managed.

### `scripts/verify_gpg.py`

Downloads and verifies tarball GPG signature:

```bash
./scripts/verify_gpg.py 0.22.5 --output-dir downloads
```

**Features:**
- Auto-imports GPG keys from multiple keyservers
- Retries on failure (keys.openpgp.org, keyserver.ubuntu.com, pgp.mit.edu)
- Verifies against Bruno Haible's GPG keys:
  - `B6301D9E1BBEAC08`
  - `F5BE8B267C6A406D`
  - `4F494A942E4616C2`
- `--allow-insecure`: Continue with warnings if verification fails
- `--skip-verify`: Skip verification entirely

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

## GitHub Actions Workflows

### PR Build Test (`.github/workflows/pr-build-test.yml`)

Runs on every pull request to validate builds:
- Builds linux-amd64 target only (faster)
- Uses `LOCAL_BUILD=1` to skip release creation
- Uploads artifacts for inspection

### Build Releases (`.github/workflows/build-releases.yml`)

Scheduled weekly (Saturdays 2:00 AM UTC) or manually triggered:
- Builds all missing versions for all targets
- Creates GitHub releases automatically
- Uploads tarballs

Trigger manually:
```bash
gh workflow run build-releases.yml
```

## Examples

### Build Single Target

```bash
TARGETS="linux-amd64" ./create_releases 0.22.5
```

### Build Multiple Specific Versions

```bash
./create_releases 0.22.5 0.22.4 0.21.1
```

### Custom Mirror

```bash
GETTEXT_MIRROR="https://ftp.gnu.org/gnu/gettext" ./create_releases 0.22.5
```

### Dry Run

```bash
DRY_RUN=1 ./create_releases
# Shows: Versions to be built: 0.22.5, 0.22.4 ...
```

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

### GPG verification warnings

GPG verification tries to validate signatures but continues with warnings if it fails. This is intentional to avoid blocking builds due to keyserver reliability issues.

To enforce strict GPG verification, modify `create_releases` to not pass `--allow-insecure` flag.

### Build fails inside container

```bash
# Run container interactively to debug
docker run -it --rm \
  -v $(pwd)/target/0.22.5:/out \
  -e GETTEXT_VERSION=0.22.5 \
  -e BUILD_TARGET=linux-amd64 \
  ghcr.io/actions-precompiled/buildenv:0.0.1 \
  bash

# Inside container:
wget https://mirrors.ocf.berkeley.edu/gnu/gettext/gettext-0.22.5.tar.gz
tar -xzf gettext-0.22.5.tar.gz
cd gettext-0.22.5
./configure --prefix=/tmp/install --disable-shared --enable-static
make -j$(nproc)
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

1. Edit `create_releases` - add new case in `generate_build_script()`
2. Ensure buildenv container has required toolchain
3. Test locally with `LOCAL_BUILD=1`

Example for macOS ARM64:
```bash
darwin-arm64)
    export CC=aarch64-apple-darwin-gcc
    ./configure --prefix="${INSTALL_PREFIX}" \
        --host=aarch64-apple-darwin \
        --disable-shared --enable-static
    ;;
```

## Architecture

### Simple & Direct

```
create_releases (bash)
  └─ docker run (for each target)
      └─ bash -c "inline build script"
          ├─ wget tarball
          ├─ ./configure (with --host for cross-compilation)
          ├─ make && make install
          └─ tar -czf output
```

**No intermediate layers:**
- ❌ No CMake
- ❌ No Dagger
- ❌ No separate build script files
- ✅ Just bash + Docker + inline scripts

### Benefits

1. **Simple**: Single script does everything
2. **Transparent**: Build logic visible inline
3. **Portable**: Works anywhere with Docker
4. **Fast**: No CMake configure overhead
5. **Maintainable**: One file to understand

## Migration from Dagger + CMake

This project was initially built with Dagger, then migrated to CMake + Docker, and finally simplified to just bash + Docker.

**Evolution:**
1. **Dagger** (complex, Python SDK, Dagger Engine dependency)
2. **CMake + Docker** (still complex, multiple files)
3. **Bash + Docker** (current - simple, direct, one script) ✅

Old configurations preserved for reference:
- `.dagger/` - Original Dagger implementation (removed)
- Previous commits show CMake-based approach

## Related Projects

- [actions-precompiled/buildenv](https://github.com/actions-precompiled/buildenv) - Docker build environment with cross-compilation toolchains
- [actions-precompiled/tesseract-bin](https://github.com/actions-precompiled/tesseract-bin) - Similar approach for Tesseract OCR

## License

This project follows the same license as GNU gettext (GPL-3.0).
