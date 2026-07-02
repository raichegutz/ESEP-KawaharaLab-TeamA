from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='sensor_framework',
            executable='sensor_recorder',
            name='three_topic_recorder',
            output='screen',
        ),
    ])
