#!/usr/bin/env python3
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import Bool
from gpiozero import LED

from led_driver.msg import LedPulse


class LEDDriver(Node):

    def __init__(self):
        super().__init__("led_driver")
        self.declare_parameter("gpio_pin", 4)
        self.led = LED(self.get_parameter("gpio_pin").value)
        
        ready_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.ready_sub = self.create_subscription(
            Bool,
            "/recorder_ready",
            self.ready_callback,
            ready_qos,
        )

        self.pulse_pub = self.create_publisher(
            LedPulse,
            "/led_pulse",
            10,
        )
    
        self.recording = False
        self.thread = None
        self.stop_event = threading.Event()
        self.pulse_id = 0
    
    def ready_callback(self, msg):
        if msg.data:
            # Start recording pulses
            if not self.recording:

                self.get_logger().info(
                    "Recorder ready. Starting LED pulses."
                )

                self.recording = True

                self.stop_event.clear()

                self.thread = threading.Thread(
                    target=self.flash_loop,
                    daemon=True,
                )

                self.thread.start()


        else:
            # Stop recording pulses
            if self.recording:

                self.get_logger().info(
                    "Recorder stopped. Stopping LED pulses."
                )

                self.recording = False

                self.stop_event.set()

                # Do not block ROS executor
                if self.thread is not None:
                    self.thread = None
    
    
    def flash_loop(self):
        period = 0.1          # 10 Hz
        pulse_width = 0.015   # 15 ms

        while rclpy.ok() and not self.stop_event.is_set():

            cycle_start = time.perf_counter()


            # Timestamp immediately before LED activation
            start_stamp = self.get_clock().now()

            self.led.on()


            # Maintain pulse width without burning CPU
            time.sleep(pulse_width)


            self.led.off()

            # Timestamp immediately after LED off
            end_stamp = self.get_clock().now()


            msg = LedPulse()

            msg.start_stamp = start_stamp.to_msg()
            msg.end_stamp = end_stamp.to_msg()
            msg.pulse_id = self.pulse_id

            self.pulse_pub.publish(msg)


            self.pulse_id += 1


            # Maintain 10Hz frequency
            elapsed = time.perf_counter() - cycle_start

            remaining = period - elapsed

            if remaining > 0:
                time.sleep(remaining)


        self.led.off()

        self.get_logger().info(
            "LED pulse thread exited."
        )


def main(args=None):
    rclpy.init(args=args)
    node = LEDDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.recording = False
        node.stop_event.set()

        if node.thread is not None:
            node.thread.join(timeout=1.0)

        node.led.off()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

