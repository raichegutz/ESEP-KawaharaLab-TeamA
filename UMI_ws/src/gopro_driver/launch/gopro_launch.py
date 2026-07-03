from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video0',
            description='Video device path for the GoPro HDMI capture card.',
        ),
        DeclareLaunchArgument(
            'width',
            default_value='1280',
            description='Capture width in pixels.',
        ),
        DeclareLaunchArgument(
            'height',
            default_value='720',
            description='Capture height in pixels.',
        ),
        DeclareLaunchArgument(
            'fps',
            default_value='30.0',
            description='Capture frame rate.',
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='gopro_frame',
            description='Frame id written into image headers.',
        ),
        DeclareLaunchArgument(
            'pixel_format',
            default_value='MJPG',
            description='Requested V4L2 pixel format, for example MJPG or YUYV.',
        ),
        Node(
            package='gopro_driver',
            executable='gopro_node',
            name='gopro_node',
            output='screen',
            parameters=[{
                'video_device': ParameterValue(
                    LaunchConfiguration('video_device'),
                    value_type=str,
                ),
                'width': ParameterValue(
                    LaunchConfiguration('width'),
                    value_type=int,
                ),
                'height': ParameterValue(
                    LaunchConfiguration('height'),
                    value_type=int,
                ),
                'fps': ParameterValue(
                    LaunchConfiguration('fps'),
                    value_type=float,
                ),
                'frame_id': ParameterValue(
                    LaunchConfiguration('frame_id'),
                    value_type=str,
                ),
                'pixel_format': ParameterValue(
                    LaunchConfiguration('pixel_format'),
                    value_type=str,
                ),
            }],
        ),
    ])
