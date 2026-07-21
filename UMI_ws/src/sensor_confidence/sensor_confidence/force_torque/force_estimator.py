from sensor_confidence.common.rolling_buffer import RollingBuffer, Sample

import numpy as np

from .models import ForceWindow
from .force_features import ForceFeatureExtractor
from .force_confidence import ForceConfidenceEstimator


class ForceHealthEstimator:

    def __init__(self):
        #create rolling buffer of F/T data
        self.left_data_buffer = RollingBuffer(window_seconds=0.5)
        self.right_data_buffer = RollingBuffer(window_seconds=0.5)

        #initialize feature extractor and confidence estimator
        self.feature_extractor = ForceFeatureExtractor()
        self.confidence_estimator = ForceConfidenceEstimator()


    def update_left_buffer(self,msg):
        #create a Sample object with the current timestamp and the wrench data
        sample = Sample(stamp=msg.header.stamp, data=msg.wrench)

        #add wrench stamped to rolling buffer
        self.left_data_buffer.add_sample(sample)

    def update_right_buffer(self,msg):
        #create a Sample object with the current timestamp and the wrench data
        sample = Sample(stamp=msg.header.stamp, data=msg.wrench)

        #add wrench stamped to rolling buffer
        self.right_data_buffer.add_sample(sample)


    def compute_confidence(self):
        if len(self.left_data_buffer) < 2 or len(self.right_data_buffer) < 2:
            return None, None, None, None

        left_window = self.left_data_buffer.build_window(self.left_data_buffer)
        right_window = self.right_data_buffer.build_window(self.right_data_buffer)

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

    def apply_left_right_consistency(self, left_features, right_features, left_health, right_health):
        """
        Penalize only the less-confident force sensor if the two
        force sensors disagree substantially.
        """
        t= self.thresholds
        penalty = 0.0

        # ---------- Force Magnitude ----------
        mean_diff = abs(left_features.force_magnitude - right_features.force_magnitude)
        if mean_diff > t.left_right_force_magnitude_threshold:
            penalty += t.left_right_max_penalty

        # ---------- Torque Magnitude ----------
        mean_diff = abs(
            left_features.torque_magnitude -
            right_features.torque_magnitude
        )
        if mean_diff > t.left_right_torque_magnitude_threshold:
            penalty += t.left_right_max_penalty

        # ---------- RMS ----------
        for axis in ["fx","fy","fz","tx","ty","tz"]:
            left = getattr(left_features.rms, axis)
            right = getattr(right_features.rms, axis)
            if abs(left-right) > t.left_right_rms_threshold:
                penalty += t.left_right_max_penalty

        # ---------- Variance ----------
        for axis in ["fx","fy","fz","tx","ty","tz"]:
            left = getattr(left_features.variance, axis)
            right = getattr(right_features.variance, axis)
            if abs(left-right) > t.left_right_variance_threshold:
                penalty += t.left_right_max_penalty

        penalty = min(penalty, 0.20)

        if left_health.confidence < right_health.confidence:
            left_health.penalties.left_right_consistency = penalty
            left_health.total_penalty += penalty
            left_health.confidence = max(0.0, left_health.confidence - penalty)
        else:
            right_health.penalties.left_right_consistency = penalty
            right_health.total_penalty += penalty
            right_health.confidence = max(0.0, right_health.confidence - penalty)

    def build_window(self, buffer: RollingBuffer):

        timestamps = np.array([
            sample.stamp.sec +
            sample.stamp.nanosec*1e-9
            for sample in buffer
        ])

        fx = np.array([
            sample.data.force.x
            for sample in buffer
        ])

        fy = np.array([
            sample.data.force.y
            for sample in buffer
        ])

        fz = np.array([
            sample.data.force.z
            for sample in buffer
        ])

        tx = np.array([
            sample.data.torque.x
            for sample in buffer
        ])

        ty = np.array([
            sample.data.torque.y
            for sample in buffer
        ])

        tz = np.array([
            sample.data.torque.z
            for sample in buffer
        ])

        return ForceWindow(
            timestamps,
            fx,
            fy,
            fz,
            tx,
            ty,
            tz
        )