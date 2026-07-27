#!/bin/bash
source /opt/ros/jazzy/setup.bash
source ~/UMI_ws/install/setup.bash

ros2 run gopro_driver gopro_node --ros-args -p video_device:=/dev/video24 &
ros2 run sensor_framework synchronized_publisher
#ros2 launch sensor_confidence sensor_confidence.launch.py


wait
