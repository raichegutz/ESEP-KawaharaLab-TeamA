from dataclasses import dataclass
import numpy as np


@dataclass
class TactileWindow:
    timestamps: np.ndarray
    images: np.ndarray
    grayscale: np.ndarray | None = None

@dataclass
class TactileFeatures:
    variance: np.ndarray
    blur: np.ndarray
    contrast: np.ndarray
    reference_SD: np.ndarray
    reference_mean: np.ndarray
    spatial_entropy: np.ndarray
    jitter: float
    left_right_consistency: float

@dataclass
class TactileHealth:
    confidence: float
    total_penalty: float
    penalties: TactilePenalties


@dataclass
class TactilePenalties:
    variance: float = 0.0
    blur: float = 0.0
    contrast: float = 0.0
    reference_sd: float = 0.0
    reference_mean: float = 0.0
    entropy: float = 0.0
    jitter: float = 0.0
    left_right_consistency: float = 0.0


@dataclass
class TactileThresholds:

    # -------------------------------------------------
    # Image Variance
    # -------------------------------------------------
    variance_threshold: float = 500.0
    variance_max_penalty: float = 0.06

    variance_rate_threshold: float = 300.0
    variance_rate_max_penalty: float = 0.03


    # -------------------------------------------------
    # Blur (Variance of Laplacian)
    # -------------------------------------------------
    blur_threshold: float = 80.0
    blur_max_penalty: float = 0.08

    blur_rate_threshold: float = 15.0
    blur_rate_max_penalty: float = 0.03


    # -------------------------------------------------
    # Contrast (Pixel Standard Deviation)
    # -------------------------------------------------
    contrast_threshold: float = 25.0
    contrast_max_penalty: float = 0.05

    contrast_rate_threshold: float = 5.0
    contrast_rate_max_penalty: float = 0.02


    # -------------------------------------------------
    # Difference from Reference Image (Standard Deviation)
    # Most important indicator of GelSight health
    # -------------------------------------------------
    reference_sd_threshold: float = 35.0
    reference_sd_max_penalty: float = 0.18

    reference_sd_rate_threshold: float = 8.0
    reference_sd_rate_max_penalty: float = 0.07


    # -------------------------------------------------
    # Difference from Reference Image (Mean)
    # -------------------------------------------------
    reference_mean_threshold: float = 30.0
    reference_mean_max_penalty: float = 0.15

    reference_mean_rate_threshold: float = 6.0
    reference_mean_rate_max_penalty: float = 0.05


    # -------------------------------------------------
    # Spatial Entropy
    # -------------------------------------------------
    entropy_threshold: float = 5.0
    entropy_max_penalty: float = 0.08

    entropy_rate_threshold: float = 0.30
    entropy_rate_max_penalty: float = 0.03


    # -------------------------------------------------
    # Timestamp Jitter
    # -------------------------------------------------
    jitter_threshold: float = 0.020
    jitter_max_penalty: float = 0.07

    # -------------------------------------------------
    # Left-Right Consistency
    # -------------------------------------------------
    left_right_reference_sd_threshold = 15.0
    left_right_reference_mean_threshold = 15.0

    left_right_contrast_threshold = 20.0
    left_right_variance_threshold = 20.0

    left_right_entropy_threshold = 0.75

    left_right_max_penalty = 0.20