import numpy as np
from scipy.signal import medfilt
import cv2


class Utils:
    #Compututing metrics accross arrays of arrays (e.g. rolling window of frames)
    def mean(frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the mean of every frame in a rolling window.
        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one mean value per frame.
        """
        means = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            means[i] = np.mean(frame.astype(np.float32))

        return means

    def variance(frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the variance of every frame in a rolling window.
        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one variance value per frame.
        """
        var = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            var[i] = np.var(frame.astype(np.float32))

        return var

    def standard_deviation(frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the standard deviation of every frame in a rolling window.
        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one standard deviation value per frame.
        """
        
        sd = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            sd[i] = np.std(frame.astype(np.float32))

        return sd
    
    def rms(self, data):
        return np.sqrt(np.mean(np.square(data)))

    
    def derivative(data: np.ndarray, timestamps: np.ndarray | None = None) -> np.ndarray:
        """
        Computes the first derivative. If timestamps are provided, returns dx/dt.
        Otherwise returns frame-to-frame difference.
        """

        data = np.asarray(data, dtype=np.float32)
        derivative = np.zeros_like(data)
        if len(data) < 2:
            return derivative
        if timestamps is None:
            derivative[1:] = np.diff(data)
        else:
            timestamps = np.asarray(
                timestamps,
                dtype=np.float64
            )
            dt = np.diff(timestamps)
            dt[dt == 0] = 1e-6
            derivative[1:] = np.diff(data) / dt
        return derivative




    def moving_average(self, data):
        pass

    def linear_regression_slope(self, x, y):
        slope, intercept = np.polyfit(x, y, 1)
        return slope

    def median_filter(self, data, window_size):
        return medfilt(data, kernel_size=window_size)
    


    #image processing metrics
    def blur(frame_window: np.ndarray) -> np.ndarray:
        """
        Computes the blur metric for every frame in a rolling window.
        Args:
            frame_window:
                NumPy array of shape (N, H, W)
        Returns:
            NumPy array of shape (N,)
            containing one blur value per frame.
        """
        blur_values = np.zeros(frame_window.shape[0], dtype=np.float32)
        for i, frame in enumerate(frame_window):
            blur_values[i] = cv2.Laplacian(frame, cv2.CV_64F).var()

        return blur_values
    


    #penalty calculation functions 
    def u_shaped_penalty(
        feature: np.ndarray,
        low_threshold: float,
        high_threshold: float,
        max_value: float = 255.0,
    ) -> np.ndarray:
        """
        Computes a U-shaped penalty for each value in a feature array.

        Penalty is:
            0          if low_threshold <= value <= high_threshold
            increases  as the value moves below low_threshold
            increases  as the value moves above high_threshold

        Returns:
            NumPy array of penalties in [0, 1].
        """

        penalty = np.zeros_like(feature, dtype=np.float32)

        low_mask = feature < low_threshold
        high_mask = feature > high_threshold

        penalty[low_mask] = (
            (low_threshold - feature[low_mask]) /
            low_threshold
        )

        penalty[high_mask] = (
            (feature[high_mask] - high_threshold) /
            (max_value - high_threshold)
        )

        return np.clip(penalty, 0.0, 1.0)
    
    def high_penalty(
        feature: np.ndarray,
        threshold: float,
        max_value: float = 255.0,
    ) -> np.ndarray:
        """
        Computes a high penalty for each value in a feature array.

        Penalty is:
            0          if value <= threshold
            increases  as the value moves above threshold

        Returns:
            NumPy array of penalties in [0, 1].
        """

        penalty = np.zeros_like(feature, dtype=np.float32)

        high_mask = feature > threshold

        penalty[high_mask] = (
            (feature[high_mask] - threshold) /
            (max_value - threshold)
        )

        return np.clip(penalty, 0.0, 1.0)
    
    def low_penalty(
            feature: np.ndarray,
            threshold: float,
            max_value: float = 255.0,
        ) -> np.ndarray:
            """
            Computes a low penalty for each value in a feature array.

            Penalty is:
                0          if value >= threshold
                increases  as the value moves below threshold

            Returns:
                NumPy array of penalties in [0, 1].
            """

            penalty = np.zeros_like(feature, dtype=np.float32)

            low_mask = feature < threshold

            penalty[low_mask] = (
                (threshold - feature[low_mask]) /
                threshold
            )

            return np.clip(penalty, 0.0, 1.0)
    
  