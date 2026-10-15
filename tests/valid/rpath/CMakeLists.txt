get_target_property(my_rpaths my_app INSTALL_RPATH)
list(APPEND my_rpaths "/opt/lib")
set_target_properties(my_app PROPERTIES INSTALL_RPATH "${my_rpaths}")
