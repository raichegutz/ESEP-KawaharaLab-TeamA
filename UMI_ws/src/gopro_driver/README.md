# gopro_driver

ROS 2 Python driver for a GoPro HERO9 connected through Media Mod HDMI output
and an HDMI capture card.

It also contains a GoPro control node that uses the official OpenGoPro Python
SDK to start and stop recording on the GoPro itself. Those recordings are saved
on the GoPro SD card and keep the original GPMF/IMU metadata.

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

## Recording Control Node

Install the official OpenGoPro Python SDK in the same Python environment used by
ROS 2:

```bash
python3 -m pip install open-gopro
```

Start the control node:

```bash
cd ~/UMI_ws
colcon build --packages-select gopro_driver
source install/setup.bash
ros2 launch gopro_driver gopro_control_launch.py connection:=wired
```

For wireless control, use:

```bash
ros2 launch gopro_driver gopro_control_launch.py connection:=wireless
```

Available services:

```text
/gopro/start_record  std_srvs/Trigger
/gopro/stop_record   std_srvs/Trigger
/gopro/get_state     std_srvs/Trigger
```

Start recording on the GoPro SD card:

```bash
ros2 service call /gopro/start_record std_srvs/srv/Trigger
```

Stop recording:

```bash
ros2 service call /gopro/stop_record std_srvs/srv/Trigger
```

Record events are published as JSON strings:

```text
/gopro/record_event  std_msgs/String
```

Example:

```bash
ros2 topic echo /gopro/record_event
```

The MP4 file with GPMF/IMU data is saved by the GoPro, not by ROS 2:

```text
GoPro SD card: DCIM/100GOPRO/GX*.MP4
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

If the image appears green, striped, or the frame rate is much lower than
expected, inspect supported V4L2 modes:

```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

Then try a lower-bandwidth mode:

```bash
ros2 launch gopro_driver gopro_launch.py video_device:=/dev/video0 width:=640 height:=480 fps:=30.0 pixel_format:=MJPG
```

Or try the uncompressed format if the camera does not support MJPG:

```bash
ros2 launch gopro_driver gopro_launch.py video_device:=/dev/video0 width:=640 height:=480 fps:=30.0 pixel_format:=YUYV
```
