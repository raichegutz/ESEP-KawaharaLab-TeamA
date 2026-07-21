from sensor_confidence.sensor_confidence.common import utils
from .models import VisionPenalties, VisionHealth, VisionThresholds
import numpy as np

class VisionConfidenceEstimator:

    def __init__(self):
        self.thresholds = VisionThresholds()

    def compute(self, features):
        vision_health = VisionHealth()

        vision_health.confidence = 1.0
        vision_health.total_penalty = 0.0

        vision_health.penalties = VisionPenalties(
            mean_penalty=self.mean_penalty(features.mean),
            variance_penalty=self.variance_penalty(features.variance),
            blur_penalty=self.blur_penalty(features.blur),
            contrast_penalty=self.contrast_penalty(features.contrast),
            entropy_penalty=self.entropy_penalty(features.spatial_entropy),
            dark_pixel_ratio_penalty=self.dark_pixel_ratio_penalty(features.dark_pixel_ratio),
            jitter_penalty=self.jitter_penalty(features.jitter)
        )

        for penalty in vision_health.penalties.__dict__.values():
            vision_health.confidence -= penalty
            vision_health.total_penalty += penalty
        vision_health.confidence = max(0.0, min(1.0, vision_health.confidence))
        
        return vision_health



    def mean_penalty(self, mean):
        t = self.thresholds

        #find the instantaneous penalty for each frame in the window based on the mean value
        frame_penalties = utils.u_shaped_penalty(
            mean,
            t.mean_min,
            t.mean_max
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.mean_max_penalty
    
    
        #find the average penalty across all frames in the window
        #calculate the rate of change of the mean over time (derivative)
        mean_derivative = np.abs(utils.derivative(mean))
        derivative_penalty = np.clip(
            np.mean(mean_derivative) / t.mean_rate_threshold,
            0,
            1
        ) * t.mean_rate_max_penalty

        return instantaneous_penalty + derivative_penalty

    def variance_penalty(self, variance):
        t = self.thresholds
        
        #variance per frame
        frame_penalties = utils.low_penalty(
            variance,
            t.variance_min,
            t.variance_max
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.variance_max_penalty

        #rate of change of variance over time (derivative)
        variance_derivative = np.abs(utils.derivative(variance))
        derivative_penalty = np.clip(
            np.mean(variance_derivative) / t.variance_rate_threshold,
            0,
            1
        ) * t.variance_rate_max_penalty

        return instantaneous_penalty + derivative_penalty



    def blur_penalty(self, blur):
        t = self.thresholds

        #blur per frame
        frame_penalties = utils.low_penalty(
            blur,
            t.blur_threshold
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.blur_max_penalty

        #rate of change of blur over time (derivative)
        blur_derivative = np.abs(utils.derivative(blur))
        derivative_penalty = np.clip(
            np.mean(blur_derivative) / t.blur_rate_threshold,
            0,
            1
        ) * t.blur_rate_max_penalty

        return instantaneous_penalty + derivative_penalty


    def contrast_penalty(self, contrast):
        t = self.thresholds
        
        #contrast per frame
        frame_penalties = utils.low_penalty(
            contrast,
            t.contrast_min,
            t.contrast_max
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.contrast_max_penalty

        #rate of change of contrast over time (derivative)
        contrast_derivative = np.abs(utils.derivative(contrast))
        derivative_penalty = np.clip(
            np.mean(contrast_derivative) / t.contrast_rate_threshold,
            0,
            1
        ) * t.contrast_rate_max_penalty

        return instantaneous_penalty + derivative_penalty
        
        

    def entropy_penalty(self,spatial_entropy):
        t = self.thresholds
        
        #entropy per frame
        frame_penalties = utils.low_penalty(
            spatial_entropy,
            t.entropy_threshold
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.entropy_max_penalty

        #rate of change of entropy over time (derivative)
        entropy_derivative = np.abs(utils.derivative(spatial_entropy))
        derivative_penalty = np.clip(
            np.mean(entropy_derivative) / t.entropy_rate_threshold,
            0,
            1
        ) * t.entropy_rate_max_penalty

        return instantaneous_penalty + derivative_penalty
    
    def dark_pixel_ratio_penalty(self,dark_pixel_ratio):
        t = self.thresholds
        
        #dark pixel ratio per frame
        frame_penalties = utils.high_penalty(
            dark_pixel_ratio,
            t.dark_pixel_ratio_threshold
        )
        instantaneous_penalty = np.mean(frame_penalties) * t.dark_pixel_ratio_max_penalty

        #rate of change of dark pixel ratio over time (derivative)
        dark_pixel_ratio_derivative = np.abs(utils.derivative(dark_pixel_ratio))
        derivative_penalty = np.clip(
            np.mean(dark_pixel_ratio_derivative) / t.dark_pixel_ratio_rate_threshold,
            0,
            1
        ) * t.dark_pixel_ratio_rate_max_penalty

        return instantaneous_penalty + derivative_penalty

    def jitter_penalty(self,jitter):
        t = self.thresholds
        penalty = np.clip(
            jitter /
            t.jitter_threshold,
            0,
            1
        )

        return penalty * t.jitter_max_penalty