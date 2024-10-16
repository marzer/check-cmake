target_include_directories(
    ${project_lib}
    SYSTEM
    INTERFACE
        "${CMAKE_CURRENT_SOURCE_DIR}"

    PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}"
)