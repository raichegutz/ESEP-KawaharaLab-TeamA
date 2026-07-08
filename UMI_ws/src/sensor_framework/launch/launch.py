from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'num_episodes',
            default_value='1',
            description='Number of episodes to record',
        ),
        DeclareLaunchArgument(
            'episode_duration_sec',
            default_value='10.0',
            description='Duration of each episode in seconds',
        ),
        DeclareLaunchArgument(
            'data_root',
            default_value='./data',
            description='Root directory for recorded episodes',
        ),
        Node(
            package='sensor_framework',
            executable='sensor_recorder',
            name='three_topic_recorder',
            output='screen',
            parameters=[{
                'num_episodes': ParameterValue(
                    LaunchConfiguration('num_episodes'),
                    value_type=int,
                ),
                'episode_duration_sec': ParameterValue(
                    LaunchConfiguration('episode_duration_sec'),
                    value_type=float,
                ),
                'data_root': ParameterValue(
                    LaunchConfiguration('data_root'),
                    value_type=str,
                ),
            }],
        ),
    ])
