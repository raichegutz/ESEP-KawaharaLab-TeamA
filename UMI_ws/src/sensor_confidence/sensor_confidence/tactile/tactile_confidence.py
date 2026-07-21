from sensor_confidence.common import utils
from .models import TactilePenalties, TactileHealth, TactileThresholds
import numpy as np

class TactileConfidenceEstimator:

    def __init__(self):
        self.thresholds = TactileThresholds()

    def compute(self, features):
        self.tactile_health = TactileHealth()

        self.tactile_health.confidence = 1.0
        self.tactile_health.total_penalty = 0.0

        self.tactile_health.penalties = TactilePenalties(
            variance_penalty=self.variance_penalty(features.variance),
            blur_penalty=self.blur_penalty(features.blur),
            contrast_penalty=self.contrast_penalty(features.contrast),
            reference_sd_penalty=self.reference_SD_penalty(features.reference_SD),
            reference_mean_penalty=self.reference_mean_penalty(features.reference_mean),
            entropy_penalty=self.entropy_penalty(features.spatial_entropy),
            jitter_penalty=self.jitter_penalty(features.jitter)
        )

        for penalty in self.tactile_health.penalties.__dict__.values():
            self.tactile_health.confidence -= penalty
            self.tactile_health.total_penalty += penalty
        self.tactile_health.confidence = max(0.0, min(1.0, self.tactile_health.confidence))
        
        return self.tactile_health
    

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
        

    def reference_SD_penalty(self,reference_SD):
        t = self.thresholds
        mean_sd = np.mean(reference_SD)
        penalty = np.clip(
            mean_sd/t.reference_sd_threshold,
            0,
            1
        )

        return penalty*t.reference_sd_max_penalty
        
        
    
    def reference_mean_penalty(self,reference_mean):
        t = self.thresholds 
        mean_diff = np.mean(reference_mean)
        penalty = np.clip(
            mean_diff/t.reference_mean_threshold,
            0,
            1
        )

        return penalty*t.reference_mean_max_penalty
        

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
        
    
    def jitter_penalty(self,jitter):
        t = self.thresholds
        penalty = np.clip(
            jitter / t.jitter_threshold,
            0,
            1
        )

        return penalty * t.jitter_max_penalty

  