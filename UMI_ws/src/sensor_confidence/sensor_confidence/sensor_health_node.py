import rclpy
from rclpy.node import Node
from geometry_msgs.msg import WrenchStamped
from sensor_msgs.msg import Image, Range
from std_msgs.msg import Float32
import sys
import termios
import tty
import threading

from sensor_confidence.force_torque.force_estimator import ForceHealthEstimator
from sensor_confidence.vision.vision_estimator import VisionHealthEstimator
from sensor_confidence.tactile.tactile_estimator import TactileHealthEstimator
from sensor_confidence.ToF.ToF_features import ToFDataProcessor
from sensor_confidence.fusion.sensor_fusion import SensorFusion
from sensor_confidence.common.task_phase import TaskPhase

class SensorHealthNode(Node):
    def __init__(self):
        super().__init__('sensor_health_node')

        #declare as subscribers to sensor topics
        #subscribe to left and right F/T sensors
        self.left_force_subscriber = self.create_subscription(
            WrenchStamped,
            '/force_sensor/force/left',
            self.left_force_callback,
            10
        )
        self.right_force_subscriber = self.create_subscription(
            WrenchStamped,
            '/force_sensor/force/right',
            self.right_force_callback,
            10
        )

        self.vision_subscriber = self.create_subscription(
            Image,
            '/gopro/image_raw',
            self.vision_callback,
            10
        )
        self.ToF_subscriber = self.create_subscription(
            Range,
            '/tof/data',
            self.ToF_callback,
            10
        )
        self.left_tactile_subscriber = self.create_subscription(
            Image,
            '/gelsight/image_raw/left',
            self.left_tactile_callback,
            10
        )

        self.right_tactile_subscriber = self.create_subscription(
            Image,
            '/gelsight/image_raw/right',
            self.right_tactile_callback,
            10
        )
        

        #declare as publishers to confidence topics
        self.force_confidence_publisher = self.create_publisher(
            Float32,
            '/sensor_confidence/force',
            10
        )

        self.vision_confidence_publisher = self.create_publisher(
            Float32,    
            '/sensor_confidence/vision',
            10
        )

        self.tactile_confidence_publisher = self.create_publisher(
            Float32,
            '/sensor_confidence/tactile',
            10
        )

        #initalize estimators for each sensor type
        self.force_estimator = ForceHealthEstimator()
        self.vision_estimator = VisionHealthEstimator()
        self.tactile_estimator = TactileHealthEstimator()
        self.ToF_data_processor = ToFDataProcessor()

        #intialize sensor fuser
        self.sensor_fuser = SensorFusion(self.get_logger())

      
        #initialize keyboard listener to change task phase
        self._state_lock = threading.Lock()
        self.task_phase = TaskPhase.IDLE

        # Save terminal settings to restore them on shutdown
        self.settings = termios.tcgetattr(sys.stdin)

        # Start a native background thread to listen to the terminal stdin
        self.input_thread = threading.Thread(target=self.keyboard_loop)
        self.input_thread.daemon = True 
        self.input_thread.start()

        #publish confidence values at a fixed rate
        self.publish_rate_hz = 10.0
        self.timer = self.create_timer(1.0 / self.publish_rate_hz, self.publish_confidence)

    
    def get_key(self):
        """Reads a single keypress from the terminal window."""
        tty.setraw(sys.stdin.fileno())
        # Select waits for characters without blocking the CPU
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key
    

    def keyboard_loop(self):
        self.get_logger().info("Press 0-4 to change task phases.")
        while rclpy.ok():
            key = self.get_key()
            new_phase = None
            
            if key == "0": new_phase = TaskPhase.IDLE
            elif key == "1": new_phase = TaskPhase.APPROACH
            elif key == "2": new_phase = TaskPhase.GRASP
            elif key == "3": new_phase = TaskPhase.LIFT
            elif key == "4": new_phase = TaskPhase.RELEASE
            elif key == '\x03': # Ctrl+C code
                break
            else:
                continue

            if new_phase is not None:
                with self._state_lock:
                    self.task_phase = new_phase
                self.get_logger().info(f"Task phase changed to {new_phase.name}")




    def left_force_callback(self, msg):
        #update rolling buffer for left force sensor
        self.force_estimator.update_left_buffer(msg)


    def right_force_callback(self, msg):
        #update rolling buffer for right force sensor
        self.force_estimator.update_right_buffer(msg)


    def vision_callback(self, msg):
        #update rolling buffer for vision sensor
        self.vision_estimator.update_buffer(msg)

    def ToF_callback(self, msg):
        #update rolling buffer for ToF sensor
        self.ToF_data_processor.update_buffer(msg)

    def left_tactile_callback(self, msg):
        #update rolling buffer for tactile sensor
        self.tactile_estimator.update_left_buffer(msg)

    def right_tactile_callback(self, msg):
        #update rolling buffer for tactile sensor
        self.tactile_estimator.update_right_buffer(msg)





    def publish_confidence(self):
        #compute confidence values for each sensor type
        #returns a class containing local sensor confidence values and penalties
        force_result = self.force_estimator.compute_confidence()
        vision_result = self.vision_estimator.compute_confidence()
        tactile_result = self.tactile_estimator.compute_confidence()
        ToF_features = self.ToF_data_processor.compute_features()

        #handle cases where any of the sensor confidence computations return None
        if vision_result is None:
            self.get_logger().warn("Waiting for vision data...", throttle_duration_sec=5.0)
            return
        if force_result is None:
            self.get_logger().warn("Waiting for force data...", throttle_duration_sec=5.0)
            return
        if tactile_result is None:
            self.get_logger().warn("Waiting for tactile data...", throttle_duration_sec=5.0)
            return
        
        #unpack results from each sensor confidence computation
        (
            left_force_health,
            right_force_health,
            left_force_features,
            right_force_features,
        ) = force_result
        
        (
            vision_health,
            vision_features,
        ) = vision_result

        (
            left_tactile_health,
            right_tactile_health,
            left_tactile_features,
            right_tactile_features,
        ) = tactile_result

        #fuse sensor health parameters to calculate final confidence 
        #perform intersensor cross modality fusion
        force_result = self.sensor_fuser.fuse_confidences(
            left_force_health,
            right_force_health,
            left_force_features,
            right_force_features,
            vision_health,
            vision_features,
            left_tactile_health,
            right_tactile_health,
            left_tactile_features,
            right_tactile_features,
            self.task_phase,
            ToF_features
        )

        if force_result is None:
            self.get_logger().warn("Waiting for sufficient data to fuse...",
                                   throttle_duration_sec=5.0)
            return
        
        force_left_confidence, force_right_confidence, vision_confidence, tactile_left_confidence, tactile_right_confidence = force_result

        #publish confidence values
        self.force_confidence_publisher.publish(Float32(data=force_left_confidence))
        self.force_confidence_publisher.publish(Float32(data=force_right_confidence))
        self.vision_confidence_publisher.publish(Float32(data=vision_confidence))
        self.tactile_confidence_publisher.publish(Float32(data=tactile_left_confidence))
        self.tactile_confidence_publisher.publish(Float32(data=tactile_right_confidence))






def main(args=None):
    rclpy.init(args=args)
    node = SensorHealthNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
