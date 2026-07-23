#!/bin/bash
source /opt/ros/jazzy/setup.bash
source ~/sensor_ws/install/setup.bash

echo "=== Preparing Real-Time Environment ==="

# 1. Force all CPU cores into performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 2. Verify the CPU frequency is locked at maximum
echo "Current CPU Frequencies:"
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq

echo "=== Launching Core-Pinned Sensor Nodes ==="

# 3. Launch your nodes into their isolated hardware lanes
chrt -f 85 taskset -c 1 ros2 launch ros2_gelsight_package gelsight_publisher.launch.py &
chrt -f 90 taskset -c 2 ros2 launch mms101_driver mms101_dual.launch.py &


# Wait for all
wait