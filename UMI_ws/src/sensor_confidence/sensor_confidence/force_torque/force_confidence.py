from sensor_confidence.common import utils
from .models import ForcePenalties, ForceHealth, ForceThresholds
import numpy as np

class ForceConfidenceEstimator:

    def __init__(self):
        self.thresholds = ForceThresholds()

    def compute(self, features):
        force_health = ForceHealth()

        force_health.confidence = 1.0
        force_health.total_penalty = 0.0

        force_health.penalties = ForcePenalties(
            mean_penalty=self.mean_penalty(features.mean),
            rms_penalty=self.rms_penalty(features.rms),
            variance_penalty=self.variance_penalty(features.variance),
            derivative_penalty=self.derivative_penalty(features.derivative),
            jitter_penalty=self.jitter_penalty(features.jitter),
            frequency_penalty=self.frequency_penalty(features.frequency),
            timeout_penalty=self.timeout_penalty(features.timeout),
            force_magnitude_penalty=self.force_magnitude_penalty(features.force_magnitude),
            torque_magnitude_penalty=self.torque_magnitude_penalty(features.torque_magnitude),
            high_freq_ratio_penalty=self.high_freq_ratio_penalty(features.high_freq_ratio),
            frequency_entropy_penalty=self.frequency_entropy_penalty(features.frequency_entropy)
        )

        for penalty in force_health.penalties.__dict__.values():
            force_health.confidence -= penalty
            force_health.total_penalty += penalty
        force_health.confidence = max(0.0, min(1.0, force_health.confidence))
        
        return force_health


    def mean_penalty(self, mean):
        t = self.thresholds
        values = np.abs([
            mean.fx,
            mean.fy,
            mean.fz,
            mean.tx,
            mean.ty,
            mean.tz
        ])

        frame_penalties = utils.high_penalty(
            values,
            t.mean_threshold
        )

        return np.mean(frame_penalties) * t.mean_max_penalty
    
    def rms_penalty(self, rms):
        t = self.thresholds
        values = np.array([
            rms.fx,
            rms.fy,
            rms.fz,
            rms.tx,
            rms.ty,
            rms.tz
        ])

        frame_penalties = utils.u_shaped_penalty(
            values,
            t.rms_min,
            t.rms_max
        )

        return np.mean(frame_penalties) * t.rms_max_penalty


    def variance_penalty(self, variance):
        t = self.thresholds
        
        values = np.array([
            variance.fx,
            variance.fy,
            variance.fz,
            variance.tx,
            variance.ty,
            variance.tz
        ])

        frame_penalties = utils.u_shaped_penalty(
            values,
            t.variance_min,
            t.variance_max
        )

        return np.mean(frame_penalties) * t.variance_max_penalty



    def derivative_penalty(self, derivative):
        t = self.thresholds

        mean_derivatives = np.array([
            np.mean(np.abs(derivative.fx)),
            np.mean(np.abs(derivative.fy)),
            np.mean(np.abs(derivative.fz)),
            np.mean(np.abs(derivative.tx)),
            np.mean(np.abs(derivative.ty)),
            np.mean(np.abs(derivative.tz))
        ])

        frame_penalties = utils.high_penalty(
            mean_derivatives,
            t.derivative_threshold
        )

        return np.mean(frame_penalties) * t.derivative_max_penalty

    def jitter_penalty(self,jitter):
        t = self.thresholds
        penalty = np.clip(
            jitter /
            t.jitter_threshold,
            0,
            1
        )

        return penalty * t.jitter_max_penalty
    
        
    def frequency_penalty(self, frequency):
        t = self.thresholds

        penalty = np.clip(
            (t.frequency_threshold - frequency)
            / t.frequency_threshold,
            0,
            1
        )

        return penalty * t.frequency_max_penalty    
    
    def timeout_penalty(self, timeout):
        t = self.thresholds

        penalty = np.clip(
            timeout / t.timeout_threshold,
            0,
            1
        )

        return penalty * t.timeout_max_penalty
    
    def force_magnitude_penalty(self, force_magnitude):
        t = self.thresholds

        penalty = np.clip(
            force_magnitude / t.force_magnitude_threshold,
            0,
            1
        )

        return penalty * t.force_magnitude_max_penalty
    
    def torque_magnitude_penalty(self, torque_magnitude):
        t = self.thresholds

        penalty = np.clip(
            torque_magnitude / t.torque_magnitude_threshold,
            0,
            1
        )

        return penalty * t.torque_magnitude_max_penalty
    
    def high_freq_ratio_penalty(self, high_freq_ratio):
        t = self.thresholds

        values = np.array([
            high_freq_ratio.fx,
            high_freq_ratio.fy,
            high_freq_ratio.fz,
            high_freq_ratio.tx,
            high_freq_ratio.ty,
            high_freq_ratio.tz
        ])

        frame_penalties = utils.high_penalty(
            values,
            t.high_freq_ratio_threshold
        )

        return np.mean(frame_penalties) * t.high_freq_ratio_max_penalty

    def entropy_penalty(self,frequency_entropy):
        t = self.thresholds
        
        values = np.array([
            frequency_entropy.fx,
            frequency_entropy.fy,
            frequency_entropy.fz,
            frequency_entropy.tx,
            frequency_entropy.ty,
            frequency_entropy.tz
        ])

        frame_penalties = utils.high_penalty(
            values,
            t.frequency_entropy_threshold
        )

        return np.mean(frame_penalties) * t.frequency_entropy_max_penalty
    
   

    

