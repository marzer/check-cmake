target_include_directories(
    my_lib 
    PRIVATE 
        "some/path"
    SYSTEM 
        "$<INSTALL_INTERFACE:include>)"
}
