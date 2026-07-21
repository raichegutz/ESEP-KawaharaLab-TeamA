from sensor_confidence.common.rolling_buffer import RollingBuffer, Sample

import cv2
import numpy as np

from .models import TactileWindow, TactileThresholds
from .tactile_features import TactileFeatureExtractor
from .tactile_confidence import TactileConfidenceEstimator


class TactileHealthEstimator:
    def __init__(self):
        #create rolling buffer of frames
        self.left_frame_buffer = RollingBuffer(window_seconds=0.5)
        self.right_frame_buffer = RollingBuffer(window_seconds=0.5)

        self.feature_extractor = TactileFeatureExtractor()
        self.confidence_estimator = TactileConfidenceEstimator()

        self.thresholds = TactileThresholds()
  
    def update_left_buffer(self, msg):
        #convert ROS2 Image message to OpenCV image
        cv_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8"
        )
        #create a Sample object with the current timestamp and the image data
        sample = Sample(stamp=msg.header.stamp, data=cv_image)

        #add sample to rolling buffer
        self.left_frame_buffer.add_sample(sample)

    def update_right_buffer(self, msg):
        #convert ROS2 Image message to OpenCV image
        cv_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8"
        )
        #create a Sample object with the current timestamp and the image data
        sample = Sample(stamp=msg.header.stamp, data=cv_image)

        #add sample to rolling buffer
        self.right_frame_buffer.add_sample(sample)

    def compute_confidence(self):
        if len(self.left_data_buffer) < 2 or len(self.right_data_buffer) < 2:
            return None, None, None, None

        left_window = self.left_frame_buffer.build_window(self.left_frame_buffer)
        right_window = self.right_frame_buffer.build_window(self.right_frame_buffer)

        left_features = self.feature_extractor.compute(left_window)
        right_features = self.feature_extractor.compute(right_window)

        left_health = self.confidence_estimator.compute(left_features)
        right_health = self.confidence_estimator.compute(right_features)

        self.apply_left_right_consistency(
            left_features,
            right_features,
            left_health,
            right_health
        )

        return left_health, right_health, left_features, right_features
    
    
    def build_window(self, frame_buffer):
        timestamps = np.array([
            sample.stamp.sec +
            sample.stamp.nanosec*1e-9
            for sample in frame_buffer
        ])

        images = np.stack([
            sample.data
            for sample in frame_buffer],
            axis=0
        )
       
        grayscale = np.stack([
            cv2.cvtColor(sample.data, cv2.COLOR_BGR2GRAY)
            for sample in frame_buffer],
            axis=0
        )

        return TactileWindow(
            timestamps,
            images,
            grayscale
        )

    def apply_left_right_consistency(self,left_features,right_features,left_health,right_health):
        """
        Penalize only the less-confident GelSight if the two
        tactile sensors disagree.
        """
        t = self.thresholds
        penalty = 0.0

        comparisons = [
            (left_features.reference_SD,
            right_features.reference_SD,
            t.left_right_reference_sd_threshold,
            t.left_right_max_penalty),

            (left_features.reference_mean,
            right_features.reference_mean,
            t.left_right_reference_mean_threshold,
            t.left_right_max_penalty),

            (left_features.contrast,
            right_features.contrast,
            t.left_right_contrast_threshold,
            t.left_right_max_penalty),

            (left_features.variance,
            right_features.variance,
            t.left_right_variance_threshold,
            t.left_right_max_penalty),

            (left_features.spatial_entropy,
            right_features.spatial_entropy,
            t.left_right_entropy_threshold,
            t.left_right_max_penalty)
        ]

        for left, right, threshold, weight in comparisons:
            # Difference in average feature
            mean_difference = abs(
                np.mean(left) -
                np.mean(right)
            )

            # Average point-wise disagreement
            window_difference = np.mean(
                np.abs(left-right)
            )

            if mean_difference > threshold:
                penalty += weight
            if window_difference > threshold:
                penalty += weight

        penalty = min(penalty, 0.20)

        if left_health.confidence < right_health.confidence:
            left_health.penalties.left_right_consistency = penalty
            left_health.total_penalty += penalty
            left_health.confidence = max(0.0, left_health.confidence - penalty)
        else:
            right_health.penalties.left_right_consistency = penalty
            right_health.total_penalty += penalty
            right_health.confidence = max(0.0, right_health.confidence - penalty)
   
