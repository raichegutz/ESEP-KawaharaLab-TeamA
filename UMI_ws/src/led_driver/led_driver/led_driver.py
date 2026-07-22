import time
import threading

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool
from gpiozero import LED

from sensor_framework.msg import LedPulse


class LEDDriver(Node):

    def __init__(self):
        super().__init__("led_driver")
        self.declare_parameter("gpio_pin", 18)
        self.led = LED(self.get_parameter("gpio_pin").value)


        self.ready_sub = self.create_subscription(
            Bool,
            "/recorder_ready",
            self.ready_callback,
            10,
        )

        self.pulse_pub = self.create_publisher(
            LedPulse,
            "/led_pulse",
            10,
        )

        self.recording = False
        self.thread = None
        self.pulse_id = 0


    def ready_callback(self, msg):
        if msg.data and not self.recording:
            self.recording = True
            self.thread = threading.Thread(
                target=self.flash_loop,
                daemon=True,
            )
            self.thread.start()
        elif not msg.data:
            self.recording = False
            if self.thread is not None:
                self.thread.join(timeout=1.0)
                self.thread = None


    def flash_loop(self):
        period = 0.1      # 10 Hz
        pulse_width = 0.015   # 15 ms
        while rclpy.ok() and self.recording:
            cycle_start = time.perf_counter()
            start_stamp = self.get_clock().now()
            self.led.on()
            target = time.perf_counter() + pulse_width
            while time.perf_counter() < target:
                pass


            self.led.off()
            end_stamp = self.get_clock().now()
      
            msg = LedPulse()

            msg.start_stamp = start_stamp.to_msg()
            msg.end_stamp = end_stamp.to_msg()
            msg.pulse_id = self.pulse_id

            self.pulse_pub.publish(msg)

            self.pulse_id += 1

            remaining = period - (time.perf_counter() - cycle_start)

            if remaining > 0:
                time.sleep(remaining)

        self.led.off()
        self.get_logger().info("LED pulse thread stopped.")