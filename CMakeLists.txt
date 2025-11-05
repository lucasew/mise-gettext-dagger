cmake_minimum_required(VERSION 3.20)
project(gettext-build NONE)

# Required environment variables
if(NOT DEFINED ENV{GETTEXT_VERSION})
    message(FATAL_ERROR "GETTEXT_VERSION environment variable is required")
endif()

if(NOT DEFINED ENV{BUILD_TARGET})
    message(FATAL_ERROR "BUILD_TARGET environment variable is required")
endif()

set(VERSION $ENV{GETTEXT_VERSION})
set(TARGET $ENV{BUILD_TARGET})
set(MIRROR "$ENV{GETTEXT_MIRROR}")
if(NOT MIRROR)
    set(MIRROR "https://mirrors.ocf.berkeley.edu/gnu/gettext")
endif()

message(STATUS "Building gettext ${VERSION} for ${TARGET}")

# Paths
set(BUILD_DIR "/tmp/build")
set(INSTALL_DIR "/tmp/install")
set(OUTPUT_DIR "/out")

# Download and extract with multi-mirror fallback
add_custom_target(download ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Downloading gettext-${VERSION}.tar.gz..."
    COMMAND bash -c [=[
        set -euo pipefail

        # List of GNU mirrors to try (ftp.gnu.org last since it's often slow)
        MIRRORS=(
            ']=]${MIRROR}[=['
            'https://mirrors.ocf.berkeley.edu/gnu/gettext'
            'https://mirror.dogado.de/gnu/gettext'
            'https://mirror.checkdomain.de/gnu/gettext'
            'https://ftp.cc.uoc.gr/mirrors/gnu/gettext'
            'https://ftpmirror.gnu.org/gettext'
            'https://ftp.gnu.org/gnu/gettext'
        )

        FILENAME='gettext-]=]${VERSION}[=[.tar.gz'
        SUCCESS=0

        for mirror in "${MIRRORS[@]}"; do
            url="${mirror}/${FILENAME}"
            echo "Trying ${url}..."

            # Try downloading with wget (timeout 30s, 3 retries)
            if wget --timeout=30 --tries=3 -q -O /tmp/gettext.tar.gz "${url}"; then
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
    ]=]
    COMMAND ${CMAKE_COMMAND} -E make_directory ${BUILD_DIR}
    COMMAND tar -xzf /tmp/gettext.tar.gz -C ${BUILD_DIR} --strip-components=1
    COMMENT "Downloading and extracting gettext ${VERSION}"
)

# Configure based on target
if(TARGET STREQUAL "linux-amd64")
    set(CONFIGURE_ARGS --prefix=${INSTALL_DIR} --disable-shared --enable-static)
elseif(TARGET STREQUAL "linux-aarch64")
    set(ENV{CC} "aarch64-linux-gnu-gcc")
    set(ENV{CXX} "aarch64-linux-gnu-g++")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=aarch64-linux-gnu
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
elseif(TARGET STREQUAL "windows-amd64")
    set(ENV{CC} "x86_64-w64-mingw32-gcc")
    set(ENV{CXX} "x86_64-w64-mingw32-g++")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=x86_64-w64-mingw32
        --target=x86_64-w64-mingw32
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
else()
    message(FATAL_ERROR "Unknown BUILD_TARGET: ${TARGET}. Supported: linux-amd64, linux-aarch64, windows-amd64")
endif()

# Build and install
add_custom_target(build ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Configuring for ${TARGET}..."
    COMMAND cd ${BUILD_DIR} && ./configure ${CONFIGURE_ARGS}
    COMMAND ${CMAKE_COMMAND} -E echo "Building..."
    COMMAND cd ${BUILD_DIR} && make -j$$(nproc)
    COMMAND ${CMAKE_COMMAND} -E echo "Installing..."
    COMMAND cd ${BUILD_DIR} && make install
    DEPENDS download
    COMMENT "Building gettext ${VERSION} for ${TARGET}"
)

# Create output tarballs
add_custom_target(package ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Creating tarball..."
    COMMAND ${CMAKE_COMMAND} -E make_directory ${OUTPUT_DIR}
    COMMAND cd ${INSTALL_DIR} && tar -czf ${OUTPUT_DIR}/${VERSION}-${TARGET}.tar.gz .
    COMMAND ${CMAKE_COMMAND} -E echo "Creating source tarball..."
    COMMAND mkdir -p /tmp/${VERSION}-src
    COMMAND tar -xzf /tmp/gettext.tar.gz -C /tmp/${VERSION}-src --strip-components=1
    COMMAND cd /tmp && tar -czf ${OUTPUT_DIR}/${VERSION}-src.tar.gz ${VERSION}-src
    DEPENDS build
    COMMENT "Creating output tarballs"
)

# Alias for buildenv compatibility (some versions expect this target)
add_custom_target(package-zip DEPENDS package)
