#this code will subscribe to the topics published from the other packages# time_series_recorder/collector_node.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

from .sensor_buffer import SensorDataBuffer
from .writer import JsonlWriter
from .converters import (
    array_msg_to_record,
    image_msg_to_metadata,
    image_msg_to_record,
)


class ThreeTopicRecorder(Node):
    def __init__(self):
        super().__init__("three_topic_recorder")

        self.buffer = SensorDataBuffer()
        self.writer = JsonlWriter("./data/recording.jsonl")

        # self.sub_image_left = self.create_subscription(
        #     Image,
        #     "/gelsight/left/image_raw",
        #     lambda msg: self.image_callback(msg, "gelsight_left"),
        #     10
        # )

        self.sub_image_right = self.create_subscription(
            Image,
            "/gelsight/right/image_raw",
            lambda msg: self.image_callback(msg, "gelsight_right"),
            10
        )

        # self.sub_force = self.create_subscription(
        #     Float32MultiArray,
        #     "/force_sensor",
        #     self.force_callback,
        #     10,
        # )

        # Flush data periodically instead of writing inside every callback.
        self.flush_timer = self.create_timer(1.5, self.flush)

    def image_callback(self, msg, topic_name: str):
        self.writer.write_metadata(image_msg_to_metadata(msg))
        record = image_msg_to_record(msg)
        self.buffer.append(topic_name, record)

    def flush(self):
        self.buffer.pop_all(self.writer)


def main(args=None):
    rclpy.init(args=args)
    node = ThreeTopicRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.flush()
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
