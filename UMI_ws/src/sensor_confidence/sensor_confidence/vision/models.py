from dataclasses import dataclass
import numpy as np


@dataclass
class VisionWindow:
    timestamps: np.ndarray
    images: np.ndarray
    grayscale: np.ndarray | None = None

@dataclass
class VisionFeatures:
    mean: np.ndarray
    variance: np.ndarray
    blur: np.ndarray
    contrast: np.ndarray
    spatial_entropy: np.ndarray
    dark_pixel_ratio: np.ndarray
    jitter: float

@dataclass
class VisionPenalties:
    mean: float = 0.0
    variance: float = 0.0
    blur: float = 0.0
    contrast: float = 0.0
    entropy: float = 0.0
    dark_pixel_ratio: float = 0.0
    jitter: float = 0.0
    
@dataclass
class VisionHealth:
    confidence: float
    total_penalty: float
    penalties: VisionPenalties


@dataclass
class VisionThresholds:
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