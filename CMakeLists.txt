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
set(BUILD_TARGET_NAME $ENV{BUILD_TARGET})
set(MIRROR "$ENV{GETTEXT_MIRROR}")
if(NOT MIRROR)
    set(MIRROR "https://mirrors.ocf.berkeley.edu/gnu/gettext")
endif()

message(STATUS "Building gettext ${VERSION} for ${BUILD_TARGET_NAME}")

# Paths
set(BUILD_DIR "/tmp/build")
set(INSTALL_DIR "/tmp/install")
set(OUTPUT_DIR "/out")

# Create download script
set(DOWNLOAD_SCRIPT "${CMAKE_BINARY_DIR}/download.sh")
file(WRITE ${DOWNLOAD_SCRIPT} "#!/bin/bash\n")
file(APPEND ${DOWNLOAD_SCRIPT} "set -euo pipefail\n\n")
file(APPEND ${DOWNLOAD_SCRIPT} "# List of GNU mirrors to try (ftp.gnu.org last since it's often slow)\n")
file(APPEND ${DOWNLOAD_SCRIPT} "MIRRORS=(\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    '${MIRROR}'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://mirrors.ocf.berkeley.edu/gnu/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://mirror.dogado.de/gnu/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://mirror.checkdomain.de/gnu/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://ftp.cc.uoc.gr/mirrors/gnu/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://ftpmirror.gnu.org/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    'https://ftp.gnu.org/gnu/gettext'\n")
file(APPEND ${DOWNLOAD_SCRIPT} ")\n\n")
file(APPEND ${DOWNLOAD_SCRIPT} "FILENAME='gettext-${VERSION}.tar.gz'\n")
file(APPEND ${DOWNLOAD_SCRIPT} "SUCCESS=0\n\n")
file(APPEND ${DOWNLOAD_SCRIPT} "for mirror in \"\${MIRRORS[@]}\"; do\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    url=\"\${mirror}/\${FILENAME}\"\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    echo \"Trying \${url}...\"\n\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    if wget --timeout=30 --tries=3 -q -O /tmp/gettext.tar.gz \"\${url}\"; then\n")
file(APPEND ${DOWNLOAD_SCRIPT} "        echo \"✓ Successfully downloaded from \${mirror}\"\n")
file(APPEND ${DOWNLOAD_SCRIPT} "        SUCCESS=1\n")
file(APPEND ${DOWNLOAD_SCRIPT} "        break\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    else\n")
file(APPEND ${DOWNLOAD_SCRIPT} "        echo \"✗ Failed to download from \${mirror}\"\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    fi\n")
file(APPEND ${DOWNLOAD_SCRIPT} "done\n\n")
file(APPEND ${DOWNLOAD_SCRIPT} "if [ \${SUCCESS} -eq 0 ]; then\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    echo \"ERROR: Failed to download from all mirrors!\"\n")
file(APPEND ${DOWNLOAD_SCRIPT} "    exit 1\n")
file(APPEND ${DOWNLOAD_SCRIPT} "fi\n")

# Download and extract with multi-mirror fallback
add_custom_target(download ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Downloading gettext-${VERSION}.tar.gz..."
    COMMAND bash ${DOWNLOAD_SCRIPT}
    COMMAND ${CMAKE_COMMAND} -E make_directory ${BUILD_DIR}
    COMMAND tar -xzf /tmp/gettext.tar.gz -C ${BUILD_DIR} --strip-components=1
    COMMENT "Downloading and extracting gettext ${VERSION}"
)

# Configure based on target
if(BUILD_TARGET_NAME STREQUAL "linux-amd64")
    set(CONFIGURE_ARGS --prefix=${INSTALL_DIR} --disable-shared --enable-static)
elseif(BUILD_TARGET_NAME STREQUAL "linux-aarch64")
    set(ENV{CC} "aarch64-linux-gnu-gcc")
    set(ENV{CXX} "aarch64-linux-gnu-g++")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=aarch64-linux-gnu
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
elseif(BUILD_TARGET_NAME STREQUAL "windows-amd64")
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
    message(FATAL_ERROR "Unknown BUILD_TARGET: ${BUILD_TARGET_NAME}. Supported: linux-amd64, linux-aarch64, windows-amd64")
endif()

# Build and install
add_custom_target(build ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Configuring for ${BUILD_TARGET_NAME}..."
    COMMAND bash -c "cd ${BUILD_DIR} && ./configure ${CONFIGURE_ARGS}"
    COMMAND ${CMAKE_COMMAND} -E echo "Building..."
    COMMAND bash -c "cd ${BUILD_DIR} && make -j$$(nproc)"
    COMMAND ${CMAKE_COMMAND} -E echo "Installing..."
    COMMAND bash -c "cd ${BUILD_DIR} && make install"
    DEPENDS download
    COMMENT "Building gettext ${VERSION} for ${BUILD_TARGET_NAME}"
)

# Create output tarballs
add_custom_target(package ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Creating tarball..."
    COMMAND ${CMAKE_COMMAND} -E make_directory ${OUTPUT_DIR}
    COMMAND bash -c "cd ${INSTALL_DIR} && tar -czf ${OUTPUT_DIR}/${VERSION}-${BUILD_TARGET_NAME}.tar.gz ."
    COMMAND ${CMAKE_COMMAND} -E echo "Creating source tarball..."
    COMMAND bash -c "mkdir -p /tmp/${VERSION}-src"
    COMMAND bash -c "tar -xzf /tmp/gettext.tar.gz -C /tmp/${VERSION}-src --strip-components=1"
    COMMAND bash -c "cd /tmp && tar -czf ${OUTPUT_DIR}/${VERSION}-src.tar.gz ${VERSION}-src"
    DEPENDS build
    COMMENT "Creating output tarballs"
)

# Alias for buildenv compatibility (some versions expect this target)
add_custom_target(package-zip DEPENDS package)
