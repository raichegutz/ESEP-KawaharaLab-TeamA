cmake_minimum_required(VERSION 3.8)
project(led_driver)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/LedPulse.msg"
  DEPENDENCIES builtin_interfaces
)

ament_python_install_package(led_driver)

install(
  PROGRAMS
    led_driver/led_driver.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()