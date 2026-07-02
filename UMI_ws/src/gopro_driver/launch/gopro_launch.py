from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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
        Node(
            package='gopro_driver',
            executable='gopro_node',
            name='gopro_node',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('video_device'),
                'width': LaunchConfiguration('width'),
                'height': LaunchConfiguration('height'),
                'fps': LaunchConfiguration('fps'),
                'frame_id': LaunchConfiguration('frame_id'),
            }],
        ),
    ])
