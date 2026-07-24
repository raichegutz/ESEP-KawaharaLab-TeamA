cmake_minimum_required(VERSION 3.8)
project(led_driver)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(rosidl_default_runtime REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/LedPulse.msg"
  DEPENDENCIES builtin_interfaces
)


install(PROGRAMS
  led_driver/led_driver_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME led_driver
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
