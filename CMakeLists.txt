cmake_minimum_required(VERSION 3.20)
project(gettext-build NONE)

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
elseif(BUILD_TARGET_NAME STREQUAL "linux-aarch64")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=aarch64-linux-gnu
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
    set(CONFIGURE_ENV CC=aarch64-linux-gnu-gcc CXX=aarch64-linux-gnu-g++)
elseif(BUILD_TARGET_NAME STREQUAL "windows-amd64")
    set(CONFIGURE_ARGS
        --prefix=${INSTALL_DIR}
        --host=x86_64-w64-mingw32
        --target=x86_64-w64-mingw32
        --build=x86_64-linux-gnu
        --disable-shared
        --enable-static
    )
    set(CONFIGURE_ENV CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++)
else()
    message(FATAL_ERROR "Unknown BUILD_TARGET: ${BUILD_TARGET_NAME}. Supported: linux-amd64, linux-aarch64, windows-amd64")
endif()

# Build gettext using ExternalProject
ExternalProject_Add(gettext
    URL ${DOWNLOAD_URLS}
    DOWNLOAD_NO_PROGRESS FALSE
    TIMEOUT 30

    CONFIGURE_COMMAND ${CONFIGURE_ENV} <SOURCE_DIR>/configure ${CONFIGURE_ARGS}
    BUILD_COMMAND make -j$$(nproc)
    INSTALL_COMMAND make install

    BUILD_IN_SOURCE 0
    LOG_CONFIGURE TRUE
    LOG_BUILD TRUE
    LOG_INSTALL TRUE
)

# Create output tarballs
ExternalProject_Add_Step(gettext package
    COMMAND ${CMAKE_COMMAND} -E echo "Creating tarballs..."
    COMMAND ${CMAKE_COMMAND} -E make_directory ${OUTPUT_DIR}
    COMMAND ${CMAKE_COMMAND} -E tar czf ${OUTPUT_DIR}/${VERSION}-${BUILD_TARGET_NAME}.tar.gz .
    WORKING_DIRECTORY ${INSTALL_DIR}

    COMMAND ${CMAKE_COMMAND} -E echo "Creating source tarball..."
    COMMAND ${CMAKE_COMMAND} -E make_directory /tmp/${VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E tar xzf <DOWNLOADED_FILE> --strip-components=1
    WORKING_DIRECTORY /tmp/${VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E tar czf ${OUTPUT_DIR}/${VERSION}-src.tar.gz ${VERSION}-src
    WORKING_DIRECTORY /tmp

    DEPENDEES install
    COMMENT "Creating output tarballs"
)

# Alias for buildenv compatibility
add_custom_target(package-zip ALL DEPENDS gettext)
