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

# Read mirror list from file
file(STRINGS "${CMAKE_SOURCE_DIR}/mirrors.txt" MIRROR_LIST)

# Add custom mirror to the beginning if provided
if(MIRROR)
    list(INSERT MIRROR_LIST 0 "${MIRROR}")
endif()

# Try downloading from each mirror
set(DOWNLOAD_SUCCESS FALSE)
set(TARBALL_PATH "/tmp/gettext-${VERSION}.tar.gz")

foreach(MIRROR_URL IN LISTS MIRROR_LIST)
    # Skip empty lines and comments
    string(STRIP "${MIRROR_URL}" MIRROR_URL)
    if(NOT MIRROR_URL OR MIRROR_URL MATCHES "^#")
        continue()
    endif()

    set(DOWNLOAD_URL "${MIRROR_URL}/gettext-${VERSION}.tar.gz")
    message(STATUS "Trying ${DOWNLOAD_URL}...")

    file(DOWNLOAD "${DOWNLOAD_URL}" "${TARBALL_PATH}"
        TIMEOUT 30
        STATUS DOWNLOAD_STATUS
        SHOW_PROGRESS
    )

    list(GET DOWNLOAD_STATUS 0 STATUS_CODE)
    list(GET DOWNLOAD_STATUS 1 STATUS_MESSAGE)

    if(STATUS_CODE EQUAL 0)
        message(STATUS "✓ Successfully downloaded from ${MIRROR_URL}")
        set(DOWNLOAD_SUCCESS TRUE)
        break()
    else()
        message(STATUS "✗ Failed: ${STATUS_MESSAGE}")
    endif()
endforeach()

if(NOT DOWNLOAD_SUCCESS)
    message(FATAL_ERROR "Failed to download gettext-${VERSION}.tar.gz from all mirrors!")
endif()

# Extract tarball
add_custom_target(download ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${BUILD_DIR}
    COMMAND tar -xzf ${TARBALL_PATH} -C ${BUILD_DIR} --strip-components=1
    COMMENT "Extracting gettext ${VERSION}"
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
# Convert CONFIGURE_ARGS list to string for bash
list(JOIN CONFIGURE_ARGS " " CONFIGURE_ARGS_STR)

# Create configure script
set(CONFIGURE_SCRIPT "${CMAKE_BINARY_DIR}/configure.sh")
file(WRITE ${CONFIGURE_SCRIPT} "#!/bin/bash\nset -euo pipefail\n")
file(APPEND ${CONFIGURE_SCRIPT} "cd ${BUILD_DIR}\n")
file(APPEND ${CONFIGURE_SCRIPT} "./configure ${CONFIGURE_ARGS_STR}\n")

# Create build script
set(BUILD_SCRIPT "${CMAKE_BINARY_DIR}/build.sh")
file(WRITE ${BUILD_SCRIPT} "#!/bin/bash\nset -euo pipefail\n")
file(APPEND ${BUILD_SCRIPT} "cd ${BUILD_DIR}\n")
file(APPEND ${BUILD_SCRIPT} "make -j$(nproc)\n")

# Create install script
set(INSTALL_SCRIPT "${CMAKE_BINARY_DIR}/install.sh")
file(WRITE ${INSTALL_SCRIPT} "#!/bin/bash\nset -euo pipefail\n")
file(APPEND ${INSTALL_SCRIPT} "cd ${BUILD_DIR}\n")
file(APPEND ${INSTALL_SCRIPT} "make install\n")

add_custom_target(build ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Configuring for ${BUILD_TARGET_NAME}..."
    COMMAND bash ${CONFIGURE_SCRIPT}
    COMMAND ${CMAKE_COMMAND} -E echo "Building..."
    COMMAND bash ${BUILD_SCRIPT}
    COMMAND ${CMAKE_COMMAND} -E echo "Installing..."
    COMMAND bash ${INSTALL_SCRIPT}
    DEPENDS download
    COMMENT "Building gettext ${VERSION} for ${BUILD_TARGET_NAME}"
)

# Create packaging script
set(PACKAGE_SCRIPT "${CMAKE_BINARY_DIR}/package.sh")
file(WRITE ${PACKAGE_SCRIPT} "#!/bin/bash\nset -euo pipefail\n")
file(APPEND ${PACKAGE_SCRIPT} "mkdir -p ${OUTPUT_DIR}\n")
file(APPEND ${PACKAGE_SCRIPT} "cd ${INSTALL_DIR}\n")
file(APPEND ${PACKAGE_SCRIPT} "tar -czf ${OUTPUT_DIR}/${VERSION}-${BUILD_TARGET_NAME}.tar.gz .\n")
file(APPEND ${PACKAGE_SCRIPT} "mkdir -p /tmp/${VERSION}-src\n")
file(APPEND ${PACKAGE_SCRIPT} "tar -xzf ${TARBALL_PATH} -C /tmp/${VERSION}-src --strip-components=1\n")
file(APPEND ${PACKAGE_SCRIPT} "cd /tmp\n")
file(APPEND ${PACKAGE_SCRIPT} "tar -czf ${OUTPUT_DIR}/${VERSION}-src.tar.gz ${VERSION}-src\n")

# Create output tarballs
add_custom_target(package ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Creating tarballs..."
    COMMAND bash ${PACKAGE_SCRIPT}
    DEPENDS build
    COMMENT "Creating output tarballs"
)

# Alias for buildenv compatibility (some versions expect this target)
add_custom_target(package-zip DEPENDS package)
