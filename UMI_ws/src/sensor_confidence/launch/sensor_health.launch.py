from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    sensor_health_node = Node(
        package="sensor_confidence",
        executable="sensor_health_node",
        name="sensor_health_node",
        output="screen"
    )

    return LaunchDescription([
        sensor_health_node
    ])