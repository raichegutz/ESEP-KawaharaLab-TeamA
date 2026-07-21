from numpy import np
import cv2
from .models import TactileFeatures
from sensor_confidence.common import utils


class TactileFeatureExtractor:
    reference_frame = None
    
    def __init__(self):
        #find path to reference frame and initialize the image
        pass

    def compute(self, window, task):
        variance = utils.variance(window.grayscale)
        contrast = utils.standard_deviation(window.grayscale)
        spatial_entropy = self.spatial_entropy(window.grayscale)
        blur = utils.blur_metric(window.grayscale)
        jitter = utils.timestamp_jitter(window.timestamps)

        #run these health checks at the beginning of the grasping task, when the sensor is not in contact with any object
        if self.reference_frame is not None and task == "no_grasp":
            reference_SD = self.reference_SD(window.grayscale)
            reference_mean = self.reference_mean(window.grayscale)
        else:
            reference_SD = np.zeros(window.grayscale.shape[0], dtype=np.float32)
            reference_mean = np.zeros(window.grayscale.shape[0], dtype=np.float32)

        return TactileFeatures(
            variance=variance,
            contrast=contrast,
            reference_SD=reference_SD,
            reference_mean=reference_mean,
            blur=blur,
            spatial_entropy=spatial_entropy,
            jitter=jitter
        )
    
    
    def reference_SD(self,frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the Reference Standard Deviation (RSD)
        of each frame to the reference frame (new sensor, non-grasping).

        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one RSD value per frame.
        """
        if self.reference_frame is None:
            raise ValueError("Reference frame not set.")

        rsd_values = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            diff = frame.astype(np.float32) - self.reference_frame.astype(np.float32)
            rsd_values[i] = np.std(diff)

        return rsd_values

    def reference_mean(self, frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the Reference Mean (RM)
        of each frame to the reference frame (new sensor, non-grasping).

        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one RM value per frame.
        """
        if self.reference_frame is None:
            raise ValueError("Reference frame not set.")

        rm_values = np.zeros(frame_window.shape[0], dtype=np.float32)
        reference = self.reference_frame.astype(np.float32)

        for i, frame in enumerate(frame_window):
            diff = np.abs(frame.astype(np.float32) - reference)
            rm_values[i] = np.mean(diff)

        return rm_values
    

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
        
        