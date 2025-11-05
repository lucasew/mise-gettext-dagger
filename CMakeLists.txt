cmake_minimum_required(VERSION 3.20)
project(gettext-bin NONE)

# Configuration - accept from environment or CMake variable
if(DEFINED ENV{GETTEXT_VERSION})
    set(GETTEXT_VERSION $ENV{GETTEXT_VERSION})
elseif(NOT DEFINED GETTEXT_VERSION)
    set(GETTEXT_VERSION "0.22.5")
endif()

if(DEFINED ENV{BUILD_TARGET})
    set(BUILD_TARGET $ENV{BUILD_TARGET})
elseif(NOT DEFINED BUILD_TARGET)
    set(BUILD_TARGET "linux-amd64")
endif()

set(BUILDENV_IMAGE "ghcr.io/actions-precompiled/buildenv" CACHE STRING "Docker build environment image")
set(BUILDENV_VERSION "0.0.1" CACHE STRING "Docker build environment version")
set(GETTEXT_MIRROR "https://mirrors.ocf.berkeley.edu/gnu/gettext" CACHE STRING "Mirror URL")

# Derived variables
set(BUILDENV_FULL_IMAGE "${BUILDENV_IMAGE}:${BUILDENV_VERSION}")
set(SCRIPTS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/scripts")
set(DOWNLOADS_DIR "${CMAKE_BINARY_DIR}/downloads")
set(OUTPUT_DIR "${CMAKE_BINARY_DIR}/out")
set(SOURCE_TARBALL "${DOWNLOADS_DIR}/gettext-${GETTEXT_VERSION}.tar.gz")
set(SOURCE_VERIFIED_STAMP "${DOWNLOADS_DIR}/gettext-${GETTEXT_VERSION}.verified")

message(STATUS "Gettext version: ${GETTEXT_VERSION}")
message(STATUS "Build target: ${BUILD_TARGET}")
message(STATUS "Build environment: ${BUILDENV_FULL_IMAGE}")

# Create output directories
file(MAKE_DIRECTORY "${OUTPUT_DIR}")
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
        --allow-insecure
    COMMAND ${CMAKE_COMMAND} -E touch ${SOURCE_VERIFIED_STAMP}
    COMMENT "Downloading and verifying gettext-${GETTEXT_VERSION}.tar.gz (GPG verification optional)"
    VERBATIM
)

add_custom_target(verify-source
    DEPENDS ${SOURCE_VERIFIED_STAMP}
)

# Main build target using Docker container with buildenv
add_custom_command(
    OUTPUT ${OUTPUT_DIR}/.build-complete
    COMMAND ${CMAKE_COMMAND} -E echo "Building gettext ${GETTEXT_VERSION} for ${BUILD_TARGET}..."
    COMMAND ${CMAKE_COMMAND} -E make_directory ${OUTPUT_DIR}
    COMMAND ${DOCKER_EXECUTABLE} run --rm
        -v ${CMAKE_CURRENT_SOURCE_DIR}:/src:ro
        -v ${OUTPUT_DIR}:/out
        -e GETTEXT_VERSION=${GETTEXT_VERSION}
        -e BUILD_TARGET=${BUILD_TARGET}
        -w /src
        ${BUILDENV_FULL_IMAGE}
        /src/docker-build.sh
    COMMAND ${CMAKE_COMMAND} -E touch ${OUTPUT_DIR}/.build-complete
    DEPENDS ${SOURCE_VERIFIED_STAMP}
    COMMENT "Building gettext ${GETTEXT_VERSION} for ${BUILD_TARGET} using ${BUILDENV_FULL_IMAGE}"
    VERBATIM
)

add_custom_target(build-gettext ALL
    DEPENDS ${OUTPUT_DIR}/.build-complete
)

# Version list target
add_custom_target(version-list
    COMMAND ${SCRIPTS_DIR}/list_versions.py
    COMMENT "Fetching available gettext versions"
    VERBATIM
)

# Install/export target
install(DIRECTORY ${OUTPUT_DIR}/
    DESTINATION .
    PATTERN "*"
)
