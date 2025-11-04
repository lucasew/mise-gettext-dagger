# gettext-bin

CMake-based build system for cross-compiling GNU gettext for multiple platforms.

## Overview

This project builds static binaries of GNU gettext for:
- Linux x86_64 (amd64)
- Linux ARM64 (aarch64)
- Windows x86_64 (optional)

## Prerequisites

### Required
- CMake 3.20 or higher
- GCC/G++ (for native builds)
- GNU Make
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer (replaces pip)
- GnuPG (for signature verification)

### For Cross-Compilation
- `gcc-aarch64-linux-gnu` and `g++-aarch64-linux-gnu` (for ARM64)
- `mingw-w64` (for Windows)

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
├── CMakeLists.txt              # Main CMake configuration
├── cmake/
│   ├── toolchain-linux-aarch64.cmake   # ARM64 cross-compilation
│   └── toolchain-windows-amd64.cmake   # Windows cross-compilation
├── scripts/
│   ├── list_versions.py        # Fetch available gettext versions
│   └── verify_gpg.py           # Download and verify GPG signatures
├── create_releases             # Automated release build script
└── README.md                   # This file
```

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

### Cross-compilation toolchain not found

Install the required cross-compilation tools:
```bash
# Debian/Ubuntu
sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu mingw-w64

# Fedora/RHEL
sudo dnf install gcc-aarch64-linux-gnu gcc-c++-aarch64-linux-gnu mingw64-gcc
```

### GPG key import fails

Import keys manually:
```bash
gpg --recv-keys B6301D9E1BBEAC08 F5BE8B267C6A406D 4F494A942E4616C2
```

## Migration from Dagger

This project was migrated from Dagger to CMake for:
- Better reproducibility
- Simpler dependencies (no Docker required)
- Faster local builds
- Standard build system tooling

The old Dagger configuration is preserved in `.dagger/` for reference.
