from dataclasses import dataclass
import numpy as np


@dataclass
class ForceWindow:
    timestamps: np.ndarray

    fx: np.ndarray
    fy: np.ndarray
    fz: np.ndarray

    tx: np.ndarray
    ty: np.ndarray
    tz: np.ndarray

#stores the values for force and torque channels for a given feature
@dataclass
class ForceScalarData:
    fx: float
    fy: float
    fz: float

    tx: float
    ty: float
    tz: float
@dataclass
class ForceArrayData:
    fx: np.ndarray
    fy: np.ndarray
    fz: np.ndarray

    tx: np.ndarray
    ty: np.ndarray
    tz: np.ndarray


@dataclass
class ForceFeatures:
    #Signal Quality Features
    #mean related features
    mean: ForceScalarData
    rms: ForceScalarData

    variance: ForceScalarData
    derivative: ForceScalarData


    #Communcication Health Features
    jitter: float
    frequency: float
    timeout: float
    force_magnitude: float
    torque_magnitude: float

    #fourier transform related features  
    high_freq_ratio: ForceScalarData
    frequency_entropy: ForceScalarData


    
@dataclass
class ForceHealth:
    confidence: float
    total_penalty: float
    penalties: ForcePenalties


@dataclass
class ForcePenalties:
    rms: float = 0.0
    variance: float = 0.0
    derivative: float = 0.0
    jitter: float = 0.0
    frequency: float = 0.0
    timeout: float = 0.0
    force_magnitude: float = 0.0
    torque_magnitude: float = 0.0
    high_freq_ratio: float = 0.0
    frequency_entropy: float = 0.0
    left_right_consistency: float = 0.0
    


@dataclass
class ForceThresholds:
    # -------------------------------------------------
    # Mean Brightness
    # -------------------------------------------------
    mean_min: float = 60.0
    mean_max: float = 190.0

    mean_max_penalty: float = 0.10

    mean_rate_threshold: float = 8.0
    mean_rate_max_penalty: float = 0.05


    # -------------------------------------------------
    # Image Variance
    # -------------------------------------------------
    variance_min: float = 500.0
    variance_max: float = 6000.0

    variance_max_penalty: float = 0.08

    variance_rate_threshold: float = 300.0
    variance_rate_max_penalty: float = 0.04


    # -------------------------------------------------
    # Blur (Variance of Laplacian)
    # Higher is better
    # -------------------------------------------------
    blur_threshold: float = 80.0

    blur_max_penalty: float = 0.15

    blur_rate_threshold: float = 15.0
    blur_rate_max_penalty: float = 0.05


    # -------------------------------------------------
    # Contrast (standard deviation)
    # Higher is generally better
    # -------------------------------------------------
    contrast_threshold: float = 30.0

    contrast_max_penalty: float = 0.08

    contrast_rate_threshold: float = 5.0
    contrast_rate_max_penalty: float = 0.03


    # -------------------------------------------------
    # Spatial Entropy
    # Higher indicates more information
    # -------------------------------------------------
    entropy_threshold: float = 5.5

    entropy_max_penalty: float = 0.10

    entropy_rate_threshold: float = 0.30
    entropy_rate_max_penalty: float = 0.05


    # -------------------------------------------------
    # Dark Pixel Ratio
    # Percentage of pixels below intensity threshold
    # -------------------------------------------------
    dark_pixel_ratio_threshold: float = 0.40

    dark_pixel_ratio_max_penalty: float = 0.12

    dark_pixel_ratio_rate_threshold: float = 0.08
    dark_pixel_ratio_rate_max_penalty: float = 0.04


    # -------------------------------------------------
    # Timestamp Jitter (seconds)
    # -------------------------------------------------
    jitter_threshold: float = 0.020

    jitter_max_penalty: float = 0.06

    # -------------------------------------------------
    # Left-Right Consistency
    # -------------------------------------------------
    left_right_force_magnitude_threshold = 10.0
    left_right_torque_magnitude_threshold = 2.0

    left_right_rms_threshold = 3.0
    left_right_variance_threshold = 5.0