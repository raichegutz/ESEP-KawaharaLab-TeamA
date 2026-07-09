from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'connection',
            default_value='wired',
            description="GoPro SDK connection type: 'wired' or 'wireless'.",
        ),
        DeclareLaunchArgument(
            'identifier',
            default_value='',
            description='Optional GoPro identifier/name for SDK discovery.',
        ),
        DeclareLaunchArgument(
            'command_transport',
            default_value='auto',
            description="Command transport: 'auto', 'http', or 'ble'.",
        ),
        DeclareLaunchArgument(
            'connect_on_startup',
            default_value='true',
            description='Connect to the GoPro when the node starts.',
        ),
        DeclareLaunchArgument(
            'service_timeout_sec',
            default_value='15.0',
            description='Timeout for SDK commands triggered by ROS services.',
        ),
        Node(
            package='gopro_driver',
            executable='gopro_control_node',
            name='gopro_control_node',
            output='screen',
            parameters=[{
                'connection': ParameterValue(
                    LaunchConfiguration('connection'),
                    value_type=str,
                ),
                'identifier': ParameterValue(
                    LaunchConfiguration('identifier'),
                    value_type=str,
                ),
                'command_transport': ParameterValue(
                    LaunchConfiguration('command_transport'),
                    value_type=str,
                ),
                'connect_on_startup': ParameterValue(
                    LaunchConfiguration('connect_on_startup'),
                    value_type=bool,
                ),
                'service_timeout_sec': ParameterValue(
                    LaunchConfiguration('service_timeout_sec'),
                    value_type=float,
                ),
            }],
        ),
    ])
