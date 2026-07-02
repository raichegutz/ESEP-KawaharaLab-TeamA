# gopro_driver

ROS 2 Python driver for a GoPro HERO9 connected through Media Mod HDMI output
and an HDMI capture card.

## Hardware Path

```text
GoPro HERO9 Black
  -> HERO9 Media Mod micro HDMI out
  -> HDMI capture card
  -> PC USB 3.0
  -> /dev/videoX on Ubuntu
```

## Published Topics

```text
/gopro/image_raw  sensor_msgs/Image
```

## Ubuntu Test Commands

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

```bash
cd ~/UMI_ws
colcon build --packages-select gopro_driver
source install/setup.bash
ros2 launch gopro_driver gopro_launch.py video_device:=/dev/video0
```

In another terminal:

```bash
source ~/UMI_ws/install/setup.bash
ros2 topic hz /gopro/image_raw
```
