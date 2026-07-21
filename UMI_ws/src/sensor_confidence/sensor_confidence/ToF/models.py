from dataclasses import dataclass
import numpy as np

@dataclass
class ToFWindow:
    timestamps: np.ndarray
    distances: np.ndarray

@dataclass
class ToFFeatures:
    mean_distance: float
    min_distance: float
    variance: float