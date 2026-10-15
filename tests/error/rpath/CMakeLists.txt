target_link_options(my_app PRIVATE -Wl,-rpath=/opt/lib)

set_target_properties(my_app PROPERTIES LINK_FLAGS "-Wl,-rpath=/opt/lib")
