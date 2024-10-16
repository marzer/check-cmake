ExternalProject_Add(
    some_lib
    SOURCE_DIR "some_lib/source"
    CMAKE_ARGS "-DCMAKE_BUILD_TYPE=Release"
)