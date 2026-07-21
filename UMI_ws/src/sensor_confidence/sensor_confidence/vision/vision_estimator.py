from sensor_confidence.sensor_confidence.common.utils import Utils
from sensor_confidence.sensor_confidence.common.rolling_buffer import RollingBuffer, Sample

import cv2
import numpy as np
from collections import deque
import numpy as np

from .models import VisionWindow,VisionHealth
from .vision_features import VisionFeatureExtractor
from .vision_confidence import VisionConfidenceEstimator


class VisionHealthEstimator:
    def __init__(self):
        #create rolling buffer of frames
        self.frame_buffer = RollingBuffer(window_seconds=0.5)

        self.feature_extractor = VisionFeatureExtractor()
        self.confidence_estimator = VisionConfidenceEstimator()
  
    def update_buffer(self, msg):
        #convert ROS2 Image message to OpenCV image
        cv_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8"
        )
        #create a Sample object with the current timestamp and the image data
        sample = Sample(stamp=msg.header.stamp, data=cv_image)

        #add sample to rolling buffer
        self.frame_buffer.add_sample(sample)

    def compute_confidence(self):
        if len(self.data_buffer) < 2:
            return None, None

        window = self.build_window()
        features = self.feature_extractor.compute(window)
        vision_health = VisionHealth(self.confidence_estimator.compute(features))
        #computes confidence based on features extracted from the vision data in the rolling buffer
        #returns a VisionHealth object containing the confidence value and any penalties applied to be fused later
        return vision_health, features

    def build_window(self):
        timestamps = np.array([
            sample.stamp.sec +
            sample.stamp.nanosec*1e-9
            for sample in self.frame_buffer
        ])

        images = np.stack([
            sample.data
            for sample in self.frame_buffer],
            axis=0
        )
       
        grayscale = np.stack([
            cv2.cvtColor(sample.data, cv2.COLOR_BGR2GRAY)
            for sample in self.frame_buffer],
            axis=0
        )

        return VisionWindow(
            timestamps,
            images,
            grayscale
        )


   
