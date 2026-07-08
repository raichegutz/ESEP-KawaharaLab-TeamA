"""Record GelSight and force/torque data as a sequence of episodes."""

import json
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from sensor_msgs.msg import Image

from .converters import image_msg_to_metadata, image_msg_to_record
from .sensor_buffer import SensorDataBuffer
from .writer import ForceSensorWriter, GelsightWriter


class ThreeTopicRecorder(Node):
    """Record a configured number of fixed-duration sensor episodes."""

    def __init__(self):
        super().__init__("three_topic_recorder")

        self.declare_parameter("num_episodes", 1)
        self.declare_parameter("episode_duration_sec", 10.0)
        self.declare_parameter("data_root", "./data")

        self.num_episodes = int(self.get_parameter("num_episodes").value)
        self.episode_duration_sec = float(
            self.get_parameter("episode_duration_sec").value
        )
        self.data_root = Path(
            str(self.get_parameter("data_root").value)
        ).expanduser().resolve()

        if self.num_episodes < 1:
            raise ValueError("num_episodes must be at least 1")
        if self.episode_duration_sec <= 0:
            raise ValueError("episode_duration_sec must be positive")

        self.gelsight_buffer = SensorDataBuffer()
        self.force_buffer = SensorDataBuffer()
        self.gelsight_writer = None
        self.force_writer = None
        self.current_episode = 0
        self.recording_complete = False
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")

        self.sub_image_left = self.create_subscription(
            Image,
            "/gelsight/left/image_raw",
            lambda msg: self.image_callback(msg, "gelsight_left"),
            10,
        )
        self.sub_image_right = self.create_subscription(
            Image,
            "/gelsight/right/image_raw",
            lambda msg: self.image_callback(msg, "gelsight_right"),
            10,
        )
        self.sub_force_left = self.create_subscription(
            WrenchStamped,
            "/force_torque/left",
            lambda msg: self.force_callback(msg, "mms101_left"),
            10,
        )
        self.sub_force_right = self.create_subscription(
            WrenchStamped,
            "/force_torque/right",
            lambda msg: self.force_callback(msg, "mms101_right"),
            10,
        )

        # Buffered writes avoid doing filesystem I/O for every sensor message.
        self.flush_timer = self.create_timer(1.5, self.flush)
        self.episode_timer = self.create_timer(
            self.episode_duration_sec, self.finish_episode
        )
        self.start_episode()

    def episode_path(self, episode_number):
        """Return a path that cannot collide with a previous recorder run."""
        name = f"episode_{self.run_id}_{episode_number:06d}"
        return self.data_root / "episodes" / name

    def start_episode(self):
        """Create fresh buffers and writers for the next episode."""
        self.current_episode += 1
        path = self.episode_path(self.current_episode)
        path.mkdir(parents=True, exist_ok=False)

        self.gelsight_buffer = SensorDataBuffer()
        self.force_buffer = SensorDataBuffer()
        self.gelsight_writer = GelsightWriter(path)
        self.force_writer = ForceSensorWriter(path)

        started_at = datetime.now(timezone.utc).isoformat()
        episode_info = {
            "episode_number": self.current_episode,
            "num_episodes": self.num_episodes,
            "duration_sec": self.episode_duration_sec,
            "started_at": started_at,
            "status": "recording",
        }
        self._write_episode_info(path, episode_info)
        self.get_logger().info(
            f"Recording episode {self.current_episode}/{self.num_episodes} "
            f"in {path}"
        )

    def image_callback(self, msg, topic_name):
        if self.recording_complete:
            return
        self.gelsight_writer.write_metadata(image_msg_to_metadata(msg))
        self.gelsight_buffer.append(topic_name, image_msg_to_record(msg))

    def force_callback(self, msg, topic_name):
        if self.recording_complete:
            return
        record = {
            "stamp": (
                msg.header.stamp.sec * 1_000_000_000
                + msg.header.stamp.nanosec
            ),
            "fx": msg.wrench.force.x,
            "fy": msg.wrench.force.y,
            "fz": msg.wrench.force.z,
            "tx": msg.wrench.torque.x,
            "ty": msg.wrench.torque.y,
            "tz": msg.wrench.torque.z,
        }
        self.force_buffer.append(topic_name, record)

    def flush(self):
        """Write all currently buffered messages to the active episode."""
        if self.gelsight_writer is None or self.force_writer is None:
            return
        self.gelsight_buffer.pop_all(self.gelsight_writer)
        self.force_buffer.pop_all(self.force_writer)

    def finish_episode(self):
        """Finalize the active episode and start another when requested."""
        self.flush()
        path = self.episode_path(self.current_episode)
        info_path = path / "episode_info.json"
        with info_path.open(encoding="utf-8") as info_file:
            episode_info = json.load(info_file)
        episode_info["finished_at"] = datetime.now(timezone.utc).isoformat()
        episode_info["status"] = "complete"
        self._write_episode_info(path, episode_info)

        self.get_logger().info(
            f"Completed episode {self.current_episode}/{self.num_episodes}"
        )
        if self.current_episode >= self.num_episodes:
            self.recording_complete = True
            self.episode_timer.cancel()
            self.flush_timer.cancel()
            return

        self.start_episode()

    @staticmethod
    def _write_episode_info(path, episode_info):
        info_path = path / "episode_info.json"
        with info_path.open("w", encoding="utf-8") as info_file:
            json.dump(episode_info, info_file, indent=2)
            info_file.write("\n")


def main(args=None):
    rclpy.init(args=args)
    node = ThreeTopicRecorder()
    try:
        while rclpy.ok() and not node.recording_complete:
            rclpy.spin_once(node)
    except KeyboardInterrupt:
        node.get_logger().info("Recording interrupted")
    finally:
        try:
            node.flush()
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
