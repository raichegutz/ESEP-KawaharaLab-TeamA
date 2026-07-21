from numpy import np
import cv2
from .models import VisionFeatures
from sensor_confidence.sensor_confidence.common import utils


class VisionFeatureExtractor:
    def compute(self, window):
        mean = utils.mean(window.grayscale)
        variance = utils.variance(window.grayscale)
        blur = utils.blur_metric(window.grayscale)
        contrast = utils.standard_deviation(window.grayscale)
        dark_pixel_ratio = self.dark_pixel_ratio(window.grayscale)
        spatial_entropy = self.spatial_entropy(window.grayscale)
        jitter = utils.timestamp_jitter(window.timestamps)

        return VisionFeatures(
            mean=mean,
            variance=variance,
            blur=blur,
            contrast=contrast,
            dark_pixel_ratio=dark_pixel_ratio,
            spatial_entropy=spatial_entropy,
            jitter=jitter

        )
    
    
    def dark_pixel_ratio(self, frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the ratio of dark pixels in each frame.

        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one dark pixel ratio value per frame.
        """
        if self.reference_frame is None:
            raise ValueError("Reference frame not set.")

        dark_pixel_ratios = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            dark_pixels = np.sum(frame < 128)  # Assuming 8-bit grayscale
            total_pixels = frame.size
            dark_pixel_ratios[i] = dark_pixels / total_pixels if total_pixels > 0 else 0

        return dark_pixel_ratios
 

    def spatial_entropy(frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the Shannon entropy of every frame in a rolling window.
        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one entropy value per frame.
        """

        entropies = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            hist = cv2.calcHist(
                [frame],
                [0],
                None,
                [256],
                [0, 256]
            )
            probs = hist.ravel()
            probs /= (probs.sum() + 1e-12)
            probs = probs[probs > 0]
            entropies[i] = -np.sum(probs * np.log2(probs))

        return entropies
        
