cmake_minimum_required(VERSION 3.20)
project(gettext-bin NONE)

# Configuration
set(GETTEXT_VERSION "0.22.5" CACHE STRING "Gettext version to build")
set(BUILD_PLATFORMS "linux-amd64;linux-aarch64" CACHE STRING "Platforms to build for")
set(GETTEXT_MIRROR "https://mirrors.ocf.berkeley.edu/gnu/gettext" CACHE STRING "Mirror URL")
set(BUILDENV_IMAGE "ghcr.io/actions-precompiled/buildenv" CACHE STRING "Docker build environment image")
set(BUILDENV_VERSION "0.0.1" CACHE STRING "Docker build environment version")

# Derived variables
set(BUILDENV_FULL_IMAGE "${BUILDENV_IMAGE}:${BUILDENV_VERSION}")
set(SCRIPTS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/scripts")
set(DOWNLOADS_DIR "${CMAKE_BINARY_DIR}/downloads")
set(BUILD_OUTPUT_DIR "${CMAKE_BINARY_DIR}/target/${GETTEXT_VERSION}")
set(SOURCE_TARBALL "${DOWNLOADS_DIR}/gettext-${GETTEXT_VERSION}.tar.gz")
set(SOURCE_VERIFIED_STAMP "${DOWNLOADS_DIR}/gettext-${GETTEXT_VERSION}.verified")

# Create output directories
file(MAKE_DIRECTORY "${BUILD_OUTPUT_DIR}")
file(MAKE_DIRECTORY "${DOWNLOADS_DIR}")

# Find required tools
find_program(DOCKER_EXECUTABLE docker REQUIRED)

# Target to download and verify source tarball with GPG
add_custom_command(
    OUTPUT ${SOURCE_VERIFIED_STAMP}
    COMMAND ${CMAKE_COMMAND} -E echo "Downloading and verifying gettext ${GETTEXT_VERSION}..."
    COMMAND ${SCRIPTS_DIR}/verify_gpg.py
        ${GETTEXT_VERSION}
        --mirror ${GETTEXT_MIRROR}
        --output-dir ${DOWNLOADS_DIR}
    COMMAND ${CMAKE_COMMAND} -E touch ${SOURCE_VERIFIED_STAMP}
    COMMENT "Downloading and verifying gettext-${GETTEXT_VERSION}.tar.gz"
    VERBATIM
)

add_custom_target(verify-source
    DEPENDS ${SOURCE_VERIFIED_STAMP}
)

# Function to add a gettext build target for a specific platform using Docker
function(add_gettext_platform PLATFORM_NAME)
    set(PLATFORM_DIR "${CMAKE_BINARY_DIR}/build-${PLATFORM_NAME}")
    set(INSTALL_DIR "${PLATFORM_DIR}/install")
    set(SRC_DIR "${PLATFORM_DIR}/src")
    set(BUILD_DIR_IN_CONTAINER "/build")
    set(TARBALL_OUTPUT "${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-${PLATFORM_NAME}.tar.gz")

    # Determine configure options based on platform
    if(PLATFORM_NAME STREQUAL "linux-amd64")
        set(CONFIGURE_OPTS
            "--prefix=/install"
            "--disable-shared"
            "--enable-static"
        )
        set(BUILD_ENV "")
    elseif(PLATFORM_NAME STREQUAL "linux-aarch64")
        set(CONFIGURE_OPTS
            "--prefix=/install"
            "--host=aarch64-linux-gnu"
            "--build=x86_64-linux-gnu"
            "--disable-shared"
            "--enable-static"
        )
        set(BUILD_ENV "CC=aarch64-linux-gnu-gcc CXX=aarch64-linux-gnu-g++")
    elseif(PLATFORM_NAME STREQUAL "windows-amd64")
        set(CONFIGURE_OPTS
            "--prefix=/install"
            "--host=x86_64-w64-mingw32"
            "--target=x86_64-w64-mingw32"
            "--build=x86_64-linux-gnu"
            "--disable-shared"
            "--enable-static"
        )
        set(BUILD_ENV "CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++")
    endif()

    # Convert list to space-separated string for shell command
    string(REPLACE ";" " " CONFIGURE_OPTS_STR "${CONFIGURE_OPTS}")

    # Build script to run inside container
    set(BUILD_SCRIPT "${PLATFORM_DIR}/build.sh")
    file(WRITE ${BUILD_SCRIPT} "#!/bin/bash\n")
    file(APPEND ${BUILD_SCRIPT} "set -euo pipefail\n\n")
    file(APPEND ${BUILD_SCRIPT} "echo 'Extracting source...'\n")
    file(APPEND ${BUILD_SCRIPT} "cd /build\n")
    file(APPEND ${BUILD_SCRIPT} "tar -xzf /tarball/gettext-${GETTEXT_VERSION}.tar.gz --strip-components=1\n\n")
    file(APPEND ${BUILD_SCRIPT} "echo 'Configuring gettext for ${PLATFORM_NAME}...'\n")
    file(APPEND ${BUILD_SCRIPT} "${BUILD_ENV} ./configure ${CONFIGURE_OPTS_STR}\n\n")
    file(APPEND ${BUILD_SCRIPT} "echo 'Building gettext...'\n")
    file(APPEND ${BUILD_SCRIPT} "make -j\$(nproc)\n\n")
    file(APPEND ${BUILD_SCRIPT} "echo 'Installing gettext...'\n")
    file(APPEND ${BUILD_SCRIPT} "make install\n")

    # Create build directory
    file(MAKE_DIRECTORY "${PLATFORM_DIR}")

    # Docker build command
    add_custom_command(
        OUTPUT ${INSTALL_DIR}/.build-complete
        COMMAND ${CMAKE_COMMAND} -E echo "Pulling Docker image ${BUILDENV_FULL_IMAGE}..."
        COMMAND ${DOCKER_EXECUTABLE} pull ${BUILDENV_FULL_IMAGE}
        COMMAND ${CMAKE_COMMAND} -E echo "Building gettext ${GETTEXT_VERSION} for ${PLATFORM_NAME} in Docker..."
        COMMAND ${CMAKE_COMMAND} -E make_directory ${INSTALL_DIR}
        COMMAND chmod +x ${BUILD_SCRIPT}
        COMMAND ${DOCKER_EXECUTABLE} run --rm
            -v ${SOURCE_TARBALL}:/tarball/gettext-${GETTEXT_VERSION}.tar.gz:ro
            -v ${BUILD_SCRIPT}:/build.sh:ro
            -v ${INSTALL_DIR}:/install
            -w ${BUILD_DIR_IN_CONTAINER}
            ${BUILDENV_FULL_IMAGE}
            /build.sh
        COMMAND ${CMAKE_COMMAND} -E touch ${INSTALL_DIR}/.build-complete
        DEPENDS ${SOURCE_VERIFIED_STAMP}
        COMMENT "Building gettext for ${PLATFORM_NAME} using Docker"
        VERBATIM
    )

    # Create tarball of the installed files
    add_custom_command(
        OUTPUT ${TARBALL_OUTPUT}
        COMMAND ${CMAKE_COMMAND} -E echo "Creating tarball for ${PLATFORM_NAME}..."
        COMMAND ${CMAKE_COMMAND} -E chdir ${PLATFORM_DIR}
            ${CMAKE_COMMAND} -E tar czf ${TARBALL_OUTPUT} --format=gnutar install/
        DEPENDS ${INSTALL_DIR}/.build-complete
        COMMENT "Creating ${GETTEXT_VERSION}-${PLATFORM_NAME}.tar.gz"
        VERBATIM
    )

    add_custom_target(build-${PLATFORM_NAME}
        DEPENDS ${TARBALL_OUTPUT}
    )

    add_custom_target(tarball-${PLATFORM_NAME}
        DEPENDS ${TARBALL_OUTPUT}
    )
endfunction()

# Add build targets for each platform
foreach(PLATFORM ${BUILD_PLATFORMS})
    add_gettext_platform(${PLATFORM})
endforeach()

# Add source tarball target (just repackage the verified source)
add_custom_command(
    OUTPUT ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz
    COMMAND ${CMAKE_COMMAND} -E echo "Creating source tarball..."
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/src-repack
    COMMAND ${CMAKE_COMMAND} -E chdir ${CMAKE_BINARY_DIR}/src-repack
        tar -xzf ${SOURCE_TARBALL}
    COMMAND ${CMAKE_COMMAND} -E chdir ${CMAKE_BINARY_DIR}/src-repack
        ${CMAKE_COMMAND} -E rename gettext-${GETTEXT_VERSION} ${GETTEXT_VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E chdir ${CMAKE_BINARY_DIR}/src-repack
        ${CMAKE_COMMAND} -E tar czf ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz --format=gnutar ${GETTEXT_VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${CMAKE_BINARY_DIR}/src-repack
    DEPENDS ${SOURCE_VERIFIED_STAMP}
    COMMENT "Creating source tarball"
    VERBATIM
)

add_custom_target(tarball-src
    DEPENDS ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz
)

# Add convenience target to build everything
add_custom_target(build-all ALL)
foreach(PLATFORM ${BUILD_PLATFORMS})
    add_dependencies(build-all build-${PLATFORM})
endforeach()
add_dependencies(build-all tarball-src)

# Version list target
add_custom_target(version-list
    COMMAND ${SCRIPTS_DIR}/list_versions.py
    COMMENT "Fetching available gettext versions"
    VERBATIM
)

# Install/export target
install(DIRECTORY ${BUILD_OUTPUT_DIR}/
    DESTINATION .
    PATTERN "*"
)
