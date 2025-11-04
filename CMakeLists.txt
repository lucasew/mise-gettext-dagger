cmake_minimum_required(VERSION 3.20)
project(gettext-bin NONE)

# Configuration
set(GETTEXT_VERSION "0.22.5" CACHE STRING "Gettext version to build")
set(BUILD_PLATFORMS "linux-amd64;linux-aarch64" CACHE STRING "Platforms to build for")
set(GETTEXT_MIRROR "https://mirrors.ocf.berkeley.edu/gnu/gettext" CACHE STRING "Mirror URL")

# Python scripts directory
set(SCRIPTS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/scripts")

# Output directory
set(BUILD_OUTPUT_DIR "${CMAKE_BINARY_DIR}/target/${GETTEXT_VERSION}")

include(ExternalProject)

# Create output directories
file(MAKE_DIRECTORY "${BUILD_OUTPUT_DIR}")

# Function to add a gettext build target for a specific platform
function(add_gettext_platform PLATFORM_NAME)
    set(PLATFORM_DIR "${CMAKE_BINARY_DIR}/build-${PLATFORM_NAME}")
    set(INSTALL_DIR "${CMAKE_BINARY_DIR}/install-${PLATFORM_NAME}")
    set(TARBALL_OUTPUT "${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-${PLATFORM_NAME}.tar.gz")

    # Determine configure options based on platform
    if(PLATFORM_NAME STREQUAL "linux-amd64")
        set(CONFIGURE_OPTS
            --prefix=${INSTALL_DIR}
            --disable-shared
            --enable-static
            CC=gcc
            CXX=g++
        )
    elseif(PLATFORM_NAME STREQUAL "linux-aarch64")
        set(CONFIGURE_OPTS
            --prefix=${INSTALL_DIR}
            --host=aarch64-linux-gnu
            --build=x86_64-linux-gnu
            --disable-shared
            --enable-static
            CC=aarch64-linux-gnu-gcc
            CXX=aarch64-linux-gnu-g++
        )
    elseif(PLATFORM_NAME STREQUAL "windows-amd64")
        set(CONFIGURE_OPTS
            --prefix=${INSTALL_DIR}
            --host=x86_64-w64-mingw32
            --target=x86_64-w64-mingw32
            --build=x86_64-linux-gnu
            --disable-shared
            --enable-static
            CC=x86_64-w64-mingw32-gcc
            CXX=x86_64-w64-mingw32-g++
        )
    endif()

    ExternalProject_Add(gettext-${PLATFORM_NAME}
        URL ${GETTEXT_MIRROR}/gettext-${GETTEXT_VERSION}.tar.gz
        DOWNLOAD_DIR ${CMAKE_BINARY_DIR}/downloads
        SOURCE_DIR ${PLATFORM_DIR}/src
        BINARY_DIR ${PLATFORM_DIR}/build
        CONFIGURE_COMMAND ${PLATFORM_DIR}/src/configure ${CONFIGURE_OPTS}
        BUILD_COMMAND make -j$$(nproc)
        INSTALL_COMMAND make install
        LOG_DOWNLOAD ON
        LOG_CONFIGURE ON
        LOG_BUILD ON
        LOG_INSTALL ON
    )

    # Create tarball of the installed files
    add_custom_command(
        OUTPUT ${TARBALL_OUTPUT}
        COMMAND ${CMAKE_COMMAND} -E tar czf ${TARBALL_OUTPUT} .
        WORKING_DIRECTORY ${INSTALL_DIR}
        DEPENDS gettext-${PLATFORM_NAME}
        COMMENT "Creating tarball for ${PLATFORM_NAME}"
    )

    add_custom_target(tarball-${PLATFORM_NAME} ALL
        DEPENDS ${TARBALL_OUTPUT}
    )
endfunction()

# Add build targets for each platform
foreach(PLATFORM ${BUILD_PLATFORMS})
    add_gettext_platform(${PLATFORM})
endforeach()

# Add source tarball target
add_custom_command(
    OUTPUT ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz
    COMMAND ${CMAKE_COMMAND} -E echo "Downloading source tarball..."
    COMMAND wget -q -O /tmp/gettext-${GETTEXT_VERSION}.tar.gz
        ${GETTEXT_MIRROR}/gettext-${GETTEXT_VERSION}.tar.gz
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/gettext-${GETTEXT_VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E tar xzf /tmp/gettext-${GETTEXT_VERSION}.tar.gz
        --directory ${CMAKE_BINARY_DIR}/gettext-${GETTEXT_VERSION}-src
    COMMAND ${CMAKE_COMMAND} -E tar czf ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz
        -C ${CMAKE_BINARY_DIR} gettext-${GETTEXT_VERSION}-src
    COMMENT "Creating source tarball"
)

add_custom_target(tarball-src ALL
    DEPENDS ${BUILD_OUTPUT_DIR}/${GETTEXT_VERSION}-src.tar.gz
)

# Add convenience target to build everything
add_custom_target(build-all
    DEPENDS ${BUILD_PLATFORMS}
)

# Version list target
add_custom_target(version-list
    COMMAND ${CMAKE_COMMAND} -E env
        ${Python3_EXECUTABLE} ${SCRIPTS_DIR}/list_versions.py
    COMMENT "Fetching available gettext versions"
)

# Install/export target
install(DIRECTORY ${BUILD_OUTPUT_DIR}/
    DESTINATION .
    PATTERN "*"
)
