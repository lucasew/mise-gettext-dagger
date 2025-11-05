cmake_minimum_required(VERSION 3.20)
project(gettext-build NONE)

# Set policy for download timestamp
if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

include(ExternalProject)

# Required environment variables
if(NOT DEFINED ENV{GETTEXT_VERSION})
    message(FATAL_ERROR "GETTEXT_VERSION environment variable is required")
endif()

if(NOT DEFINED ENV{BUILD_TARGET})
    message(FATAL_ERROR "BUILD_TARGET environment variable is required")
endif()

set(VERSION $ENV{GETTEXT_VERSION})
set(BUILD_TARGET_NAME $ENV{BUILD_TARGET})
set(CUSTOM_MIRROR "$ENV{GETTEXT_MIRROR}")

message(STATUS "Building gettext ${VERSION} for ${BUILD_TARGET_NAME}")

# Paths
set(INSTALL_DIR "/tmp/install")
set(OUTPUT_DIR "/out")

# Read mirror list from file and prepare URLs
file(STRINGS "${CMAKE_SOURCE_DIR}/mirrors.txt" MIRROR_LIST)
set(DOWNLOAD_URLS)

# Add custom mirror first if provided
if(CUSTOM_MIRROR)
    list(APPEND DOWNLOAD_URLS "${CUSTOM_MIRROR}/gettext-${VERSION}.tar.gz")
endif()

# Add mirrors from file
foreach(MIRROR_URL IN LISTS MIRROR_LIST)
    string(STRIP "${MIRROR_URL}" MIRROR_URL)
    if(NOT MIRROR_URL OR MIRROR_URL MATCHES "^#")
        continue()
    endif()
    list(APPEND DOWNLOAD_URLS "${MIRROR_URL}/gettext-${VERSION}.tar.gz")
endforeach()

# Configure based on target
if(BUILD_TARGET_NAME STREQUAL "linux-amd64")
    set(CONFIGURE_ARGS --prefix=${INSTALL_DIR} --disable-shared --enable-static)
    set(CONFIGURE_ENV "")
elseif(BUILD_TARGET_NAME STREQUAL "windows-amd64")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=x86_64-w64-mingw32
        --target=x86_64-w64-mingw32
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
    set(CONFIGURE_ENV CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ CFLAGS=-Dlocale_t=_locale_t)
else()
    message(FATAL_ERROR "Unknown BUILD_TARGET: ${BUILD_TARGET_NAME}. Supported: linux-amd64, windows-amd64")
endif()

# Build gettext using ExternalProject
ExternalProject_Add(gettext
    URL ${DOWNLOAD_URLS}
    DOWNLOAD_NO_PROGRESS FALSE
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    TIMEOUT 30

    # Prevent autotools regeneration by touching generated files
    PATCH_COMMAND find <SOURCE_DIR> -name "aclocal.m4" -exec touch {} $<SEMICOLON>
          COMMAND find <SOURCE_DIR> -name "Makefile.in" -exec touch {} $<SEMICOLON>
          COMMAND find <SOURCE_DIR> -name "configure" -exec touch {} $<SEMICOLON>

    CONFIGURE_COMMAND ${CONFIGURE_ENV} <SOURCE_DIR>/configure ${CONFIGURE_ARGS}
    BUILD_COMMAND make -j
    INSTALL_COMMAND make install

    BUILD_IN_SOURCE 0
    USES_TERMINAL_CONFIGURE 1
    USES_TERMINAL_BUILD 1
    USES_TERMINAL_INSTALL 1
)

# Staging directory
set(STAGING_DIR "${CMAKE_BINARY_DIR}/staging/gettext-${VERSION}-${BUILD_TARGET_NAME}")

# Stage files from install directory
add_custom_target(stage-all
    COMMAND ${CMAKE_COMMAND} -E echo "Staging files to ${STAGING_DIR}..."
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${STAGING_DIR}
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${INSTALL_DIR} ${STAGING_DIR}
    DEPENDS gettext
    COMMENT "Staging installed files"
)

# Create binary package (zip only)
add_custom_target(package-zip ALL
    DEPENDS stage-all
    COMMAND ${CMAKE_COMMAND} -E echo "Creating gettext-${VERSION}-${BUILD_TARGET_NAME}.zip..."
    COMMAND ${CMAKE_COMMAND} -E tar cfv
            ${OUTPUT_DIR}/gettext-${VERSION}-${BUILD_TARGET_NAME}.zip
            --format=zip
            ${STAGING_DIR}
    WORKING_DIRECTORY ${STAGING_DIR}/..
    COMMENT "Packing ${STAGING_DIR} into zip"
)
