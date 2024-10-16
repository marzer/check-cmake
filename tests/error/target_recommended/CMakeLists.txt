add_compile_options(my_app PRIVATE -Wall)
set_target_properties(my_app PROPERTIES CXX_STANDARD 17)
add_compile_definitions(my_app PRIVATE DEBUG=1)
include_directories(my_app PRIVATE "some/include/path")
link_directories(my_app PRIVATE "some/lib/path")

add_compile_options(${my_app} PRIVATE -Wall)
set_target_properties(${my_app} PROPERTIES CXX_STANDARD 17)
add_compile_definitions(${my_app} PRIVATE DEBUG=1)
include_directories(${my_app} PRIVATE "some/include/path")
link_directories(${my_app} PRIVATE "some/lib/path")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)