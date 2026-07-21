
import numpy as np

from sensor_confidence.ToF.models import ToFFeatures, ToFWindow
from sensor_confidence.common.rolling_buffer import RollingBuffer, Sample


class ToFDataProcessor:

    def __init__(self):
        #create rolling buffer of ToF data
        self.data_buffer = RollingBuffer(window_seconds=0.5)


    def update_buffer(self,msg):
        #create a Sample object with the current timestamp and the wrench data
        sample = Sample(stamp=msg.header.stamp, data=msg.range)

        #add wrench stamped to rolling buffer
        self.data_buffer.add_sample(sample)
    
    def compute_features(self):
        if len(self.data_buffer) < 2:
            return None

        window = self.build_window(self.data_buffer)
        mean_distance = self.compute_mean_distance(window)

        return ToFFeatures(mean_distance=mean_distance)
    
    def build_window(self, buffer):
        
        timestamps = np.array([
            sample.stamp.sec +
            sample.stamp.nanosec*1e-9
            for sample in buffer
        ])

        distances = np.array([
            sample.data
            for sample in buffer
        ])

        return ToFWindow(timestamps=timestamps, distances=distances)
    
    def compute_mean_distance(self, window: ToFWindow) -> float:
        """
        Computes the mean distance from the ToF sensor data in the window.

        Args:
            window: ToFWindow object containing timestamps and distances.

        Returns:
            Mean distance as a float.
        """
        return float(np.mean(window.distances))