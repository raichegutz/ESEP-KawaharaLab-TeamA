from dataclass import dataclass
from typing import Any
from rclpy.time import Time
from collections import deque



@dataclass
class Sample:
    stamp: Time
    data: Any
    #maybe add this later (can help compute latency)
    #arrival_time: Time | None = None 

'''Creates a rolling buffer that stores samples within a specified time window. 
The buffer automatically removes old samples that fall outside the window.
Is compatible with any ROS2 message type that is read from all sensors.'''
class RollingBuffer:
    #initalizes a deque of samples and sets the window size in seconds
    def __init__(self, window_seconds: float =0.5):
        self.window_seconds = window_seconds
        self.samples: deque[Sample] = deque()
    
    
    def add_sample(self, sample: Sample):
        self.samples.append(sample)
        self.remove_old_samples()

    def remove_old_samples(self):
        if not self.samples:
            return
        now = self.latest_sample().stamp #gets latest sample timestamp
        #iterates through samples and removes any that are older than the window size
        while self.samples:
            age = (now - self.samples[0].stamp).nanoseconds / 1e9
            if age <= self.window_seconds:
                break
            self.samples.popleft()

    def clear(self):
        self.samples.clear()


    #helper functions
    def __len__(self):
        return len(self.samples)
    
    def is_empty(self):
        return len(self.samples) == 0
    
    def latest_sample(self):
        if self.samples:
            return self.samples[-1]
        return None
    


    def get_window(self):
        return list(self.samples)



